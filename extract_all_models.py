#!/usr/bin/env python3

import yaml
import subprocess
import sys
import re
from pathlib import Path

def parse_extract_output(output):
    """Parse the stdout from extract_model.py into sections."""
    sections = {
        'c': '',
        'yaml': '',
        'txt': ''
    }

    # Split by section headers
    model_c_match = re.search(r'MODEL\.C TAIL:\n=+\n(.*?)(?=\n=+\n|\Z)', output, re.DOTALL)
    if model_c_match:
        sections['c'] = model_c_match.group(1).strip()

    splat_config_match = re.search(r'SPLAT CONFIG:\n=+\n(.*?)(?=\n=+\n|\Z)', output, re.DOTALL)
    if splat_config_match:
        # Remove leading indentation from each line
        yaml_lines = splat_config_match.group(1).strip().split('\n')
        dedented_lines = [line[4:] if line.startswith('    ') else line for line in yaml_lines]
        sections['yaml'] = '\n'.join(dedented_lines)

    symbols_match = re.search(r'SYMBOL DEFINITIONS:\n=+\n(.*?)(?=\n=+\n|\Z)', output, re.DOTALL)
    if symbols_match:
        sections['txt'] = symbols_match.group(1).strip()

    return sections

# Read mons.yaml
with open('mons.yaml', 'r') as f:
    data = yaml.safe_load(f)

all_txt_content = []
all_yaml_content = []

for mon in data['mons']:
    name = mon['name']
    segment = mon['segment']
    dir_name = mon['dir']
    model = mon['model']
    materials = mon.get('materials')

    # Format addresses
    vram_str = f"0x{model['vram']:08X}" if isinstance(model['vram'], int) else hex(int(model['vram'], 16))
    rom_str = f"0x{model['rom']:08X}" if isinstance(model['rom'], int) else hex(int(model['rom'], 16))

    # Run extract_model.py
    extract_cmd = [
        'uv', 'run', 'tools/extract_model.py',
        '--variant', 'hd',
        '--segment', segment,
        './pokemonsnap.z64',
        dir_name,
        vram_str,
        rom_str,
        name,
        model['type']
    ]

    print(f"Processing {name}...", file=sys.stderr)
    result = subprocess.run(extract_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running extract_model.py for {name}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        continue

    # Parse the output sections
    sections = parse_extract_output(result.stdout)

    model_c_content = sections['c']
    model_yaml_content = sections['yaml']
    model_txt_content = sections['txt']

    # Collect txt for combined output
    if model_txt_content:
        all_txt_content.append(f"# {name}\n{model_txt_content}")

    # Parse and fix YAML root start address
    if model_yaml_content:
        import yaml as yaml_lib
        try:
            yaml_data = yaml_lib.safe_load(model_yaml_content)
            if yaml_data and isinstance(yaml_data, list) and len(yaml_data) > 0:
                # Get the rom offset from input (use top-level start field)
                rom_offset = mon['start']
                if isinstance(rom_offset, str):
                    rom_offset = int(rom_offset, 16)

                yaml_data[0]['start'] = f"0x{rom_offset:X}"

                # Manually format the YAML for better readability
                formatted_yaml = f"    - start: {yaml_data[0]['start']}\n"
                formatted_yaml += f"      type: {yaml_data[0]['type']}\n"
                formatted_yaml += f"      dir: {yaml_data[0]['dir']}\n"
                formatted_yaml += f"      name: {name}/model_hd\n"
                if 'linker_section_order' in yaml_data[0]:
                    formatted_yaml += f"      linker_section_order: {yaml_data[0]['linker_section_order']}\n"
                formatted_yaml += "      subsegments:\n"

                for subseg in yaml_data[0]['subsegments']:
                    if isinstance(subseg, list) and len(subseg) >= 3:
                        addr = subseg[0]
                        if isinstance(addr, int):
                            addr = f"0x{addr:X}"
                        formatted_yaml += f"      - [{addr}, {subseg[1]}, {subseg[2]}]\n"

                all_yaml_content.append(formatted_yaml)
            else:
                all_yaml_content.append(model_yaml_content)
        except Exception as e:
            print(f"Warning: Failed to parse/fix YAML for {name}: {e}", file=sys.stderr)
            all_yaml_content.append(model_yaml_content)

    # Run model_header.py if materials exist
    header_output = ""
    if materials:
        vram = materials['vram']
        rom = materials['rom']
        vram_str = f"0x{vram:08X}" if isinstance(vram, int) else hex(int(vram, 16))
        rom_str = f"0x{rom:08X}" if isinstance(rom, int) else hex(int(rom, 16))

        header_cmd = [
            'uv', 'run', 'tools/model_header.py',
            'pokemonsnap.z64',
            vram_str,
            rom_str,
            f"{name}_hd"
        ]
        header_result = subprocess.run(header_cmd, capture_output=True, text=True)
        if header_result.returncode == 0:
            # Extract only the C code after the "GENERATED C CODE:" header
            match = re.search(r'GENERATED C CODE:\n=+\n(.*)', header_result.stdout, re.DOTALL)
            if match:
                header_output = match.group(1).strip()
            else:
                header_output = header_result.stdout
        else:
            print(f"Warning: model_header.py failed for {name}", file=sys.stderr)

    # Combine into single C file
    c_content = '#include "common.h"\n\n'
    if header_output:
        c_content += header_output
        if not header_output.endswith('\n'):
            c_content += '\n'
    if model_c_content:
        c_content += model_c_content

    # Write C file
    c_file_path = Path(f"src/{dir_name}/{name}/model_hd.c")
    c_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(c_file_path, 'w') as f:
        f.write(c_content)
    print(f"Wrote {c_file_path}", file=sys.stderr)

# Output combined txt to stdout
print("# Combined TXT Output")
print("# " + "="*70)
for txt in all_txt_content:
    print(txt)
    print()

print("\n# Combined YAML Output")
print("# " + "="*70)

# First output auto items for all mons
for mon in data['mons']:
    name = mon['name']
    dir_name = mon['dir']
    print(f"    - [auto, c, {name}/model_hd]")

print()

# Then output the detailed subsegment data
for yaml_content in all_yaml_content:
    print(yaml_content)
