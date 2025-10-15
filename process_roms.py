#!/usr/bin/env python3

import re
from pathlib import Path

# Process files in reverse order (mon12 down to mon1)
for i in range(12, 0, -1):
    filename = f"mon{i}.s"
    filepath = Path(filename)

    if not filepath.exists():
        continue

    with open(filepath, 'r') as f:
        lines = [line.rstrip() for line in f.readlines()]

    # Get first two non-empty lines
    non_empty = [line for line in lines if line.strip()]
    if len(non_empty) < 2:
        continue

    first_line = non_empty[0]
    second_line = non_empty[1]

    # Print from "uv" onward in first line
    if "uv" in first_line:
        uv_pos = first_line.index("uv")
        print(first_line[uv_pos:])

    # Parse second line: /* 47CF30 80186B10 00000000 */
    match = re.search(r'/\*\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)\s+\*/', second_line)
    if match:
        rom_addr = match.group(1)
        vram_addr = match.group(2)
        word = match.group(3)
        basename = f"mon{i}"
        print(f"uv run tools/model_header.py pokemonsnap.z64 {vram_addr} {rom_addr} {basename}_hd")
    else:
        print(second_line)

    print()  # Blank line between files
