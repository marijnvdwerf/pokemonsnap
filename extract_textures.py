#!/usr/bin/env python3
import argparse
import re
from pathlib import Path


def extract_textures(area: str):
    """Extract texture extern declarations from an area's model files."""
    assets_dir = Path("assets") / area

    if not assets_dir.exists():
        print(f"Error: Directory {assets_dir} does not exist")
        return

    for mondir in sorted(assets_dir.iterdir()):
        if not mondir.is_dir():
            continue

        monname = mondir.name
        print(f"// {monname} textures")

        # Find all hd_*.gfx.inc.c files
        gfx_files = list(mondir.glob("hd_*.gfx.inc.c"))

        textures = set()

        for gfx_file in gfx_files:
            try:
                with open(gfx_file, 'r') as f:
                    for line in f:
                        if 'gsDPSetTextureImage' in line:
                            # Extract the 4th argument from the macro
                            # Format: gsDPSetTextureImage(arg1, arg2, arg3, arg4)
                            match = re.search(r'gsDPSetTextureImage\([^,]+,\s*[^,]+,\s*[^,]+,\s*([^),\s]+)', line)
                            if match:
                                texture = match.group(1)
                                textures.add(texture)
            except FileNotFoundError:
                continue

        # Output sorted unique texture declarations
        for texture in sorted(textures):
            # If it starts with D_ and has 8 hex chars, rename it
            if texture.startswith('D_'):
                # Extract the 8-character hex address after D_
                match = re.match(r'D_([0-9A-Fa-f]+)', texture)
                if match:
                    hex_addr = match.group(1)
                    texture = f"{monname}_tex_{hex_addr}"
            print(f"extern u8 {texture}[];")

        print()


def main():
    parser = argparse.ArgumentParser(
        description="Extract texture extern declarations from model files",
        epilog="Example: %(prog)s valley"
    )
    parser.add_argument("area", help="Area name (e.g., valley, beach, tunnel)")

    args = parser.parse_args()
    extract_textures(args.area)


if __name__ == "__main__":
    main()
