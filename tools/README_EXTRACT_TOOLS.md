# Model Extraction Tools

This directory contains two Python scripts for extracting and analyzing model data from Pokemon Snap ROM files.

## 1. find_unkec64arg3.py

Scans binary files in the `assets/` directory to find potential `UnkEC64Arg3` model data structures.

### Usage

```bash
python3 tools/find_unkec64arg3.py
```

### Output

The script will output a table showing:
- File name (relative to `assets/`)
- Offset within the file (hexadecimal)
- Number of entries in the list

Example output:
```
File                                               Offset     Count
--------------------------------------------------------------------------------
13C780.bin                                         0x002D38    5
valley/7C6770.bin                                  0x036020    5
volcano/moltres/model.bin                          0x000888    22
```

## 2. extract_model.py

Extracts complete model data from a ROM file and generates:
1. model.c tail section (includes and data structures)
2. splat.yaml configuration
3. Symbol definitions for symbol_addrs.txt

### Usage

```bash
uv run tools/extract_model.py <rom_file> <vram_addr> <rom_addr> <name>
```

**Parameters:**
- `rom_file`: Path to the Pokemon Snap ROM (e.g., `pokemonsnap.z64`)
- `vram_addr`: Virtual RAM address where the UnkEC64Arg3 model array starts
- `rom_addr`: ROM file offset where the UnkEC64Arg3 model array starts
- `name`: Name of the model (e.g., `moltres`, `dugtrio`)

**Example:**
```bash
uv run tools/extract_model.py pokemonsnap.z64 0x8032A688 0x77B888 moltres
```

### Finding the Addresses

1. Use `find_unkec64arg3.py` to locate potential model data
2. For a binary at offset `0x77B888`, calculate the VRAM address using:
   ```bash
   uv run python3 -m mapfile_parser sym_info --vrom 0x77B888
   ```
   This will show you the virtual RAM address for that offset

### Output

The script generates three sections:

#### 1. MODEL.C TAIL

Includes statements for all model assets and the data structure definitions:

```c
#include "assets/volcano/moltres/model.vtx.inc.c"
#include "assets/volcano/moltres/first.gfx.inc.c"
#include "assets/volcano/moltres/part1_pre_near.gfx.inc.c"
...

DObjPayloadTypeI moltres_gfxdata[] = {
    { NULL, moltres_first },
    { moltres_part1_pre, moltres_part1_draw },
    ...
};

UnkEC64Arg3 moltres_model[] = {
    { 0, NULL, { 0.0, 0.0, 0.0 }, ... },
    ...
};
```

#### 2. SPLAT CONFIG

Configuration to add to `splat.yaml` for asset extraction:

```yaml
    - start: 0x775AC0
      type: .data
      dir: moltres
      name: moltres/model
      linker_section_order: .rodata
      subsegments:
      - [0x775AC0, vtx, model]
      - [0x777E10, gfx, first]
      - [0x777E50, gfx, part0_draw_near]
      ...
```

#### 3. SYMBOL DEFINITIONS

Symbol names and addresses for `tools/symbol_addrs.txt`:

```
moltres_vtx = 0x803248C0; // segment:volcano_code size:0x2350
moltres_first = 0x80326C10; // segment:volcano_code
moltres_part1_pre_near = 0x80326EA0; // segment:volcano_code
...
```

## Features

### Automatic Structure Detection

The script automatically detects:
- **DObjPayloadTypeI**: Two Gfx pointers (8 bytes)
  - Used when models have separate "pre" and "draw" display lists
  - Example: `{ moltres_part1_pre, moltres_part1_draw }`

- **DObjPayloadTypeC**: Integer + Gfx pointer (8 bytes)
  - Used for indexed display lists
  - Example: `{ 5, moltres_part1_draw }`

- **DObjPayloadTypeJ**: Integer + two Gfx pointers (12 bytes)
  - Used for more complex rendering setups
  - Example: `{ 0, moltres_unk1, moltres_unk2 }`

- **Direct Display Lists**: Pointers directly to Gfx arrays (no intermediate structure)

### Special Cases

- **"first" and "last"**: The script automatically detects the first and last display lists in a model and names them appropriately
- **Hierarchical structures**: Handles parent-child relationships in the UnkEC64Arg3 array (non-sequential indices)
- **LOD variants**: Generates near/far/base variants for each display list (typical N64 pattern)

## Notes

- The vertex data offset is estimated (usually ~0x2800 bytes before gfxdata)
- Display list sizes in the splat config are estimated (+0xE0 and +0x1C0 offsets)
- You may need to manually adjust these values based on the actual data
- For models with Type J structures, display lists may be named "unk1" and "unk2" - rename as needed

## Workflow

1. Run `find_unkec64arg3.py` to scan for model data
2. Identify a model you want to extract
3. Use `mapfile_parser` to get the VRAM address
4. Run `extract_model.py` with the ROM and addresses
5. Copy the output to appropriate files:
   - Add MODEL.C TAIL to your model.c file
   - Add SPLAT CONFIG to splat.yaml
   - Add SYMBOL DEFINITIONS to symbol_addrs.txt
6. Run splat to extract the assets
7. Build and verify the model matches

## Example: Extracting Moltres

```bash
# 1. Find the model data
python3 tools/find_unkec64arg3.py | grep moltres

# 2. Get VRAM address (if model is at ROM 0x77B888)
uv run python3 -m mapfile_parser sym_info --vrom 0x77B888

# 3. Extract the model
uv run tools/extract_model.py pokemonsnap.z64 0x8032A688 0x77B888 moltres > moltres_extract.txt

# 4. Review and integrate the output
cat moltres_extract.txt
```

