#!/usr/bin/env python3
"""
Extract model header data (materials/textures) from Pokemon Snap ROM.

This tool generates C code for:
- Texture** materials array
- Texture* arrays for each part
- Texture structures with full initialization
- u8* texture frame arrays

Part numbers are based on the materials array index (e.g., entry 7 becomes part7).

Usage:
    uv run tools/model_header.py <rom_file> <vram_addr> <rom_addr> <name>

Example:
    uv run tools/model_header.py pokemonsnap.z64 80323FD0 7751D0 moltres
"""

import struct
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field


@dataclass
class TextureInfo:
    """Parsed Texture structure (0x78 bytes)"""
    vram_addr: int
    rom_addr: int
    pad00: int
    fmt: int
    paletteBitDepth: int
    images: int  # pointer
    scale: int
    unk0A: int
    widthMain: int
    heightMain: int
    unk_10: int
    unk_14: float
    unk_18: float
    scaleS: float
    scaleT: float
    unk_24: float
    unk_28: float
    palettes: int  # pointer
    flags: int
    unk_32: int
    unk_33: int
    blockWidth: int
    blockHeight: int
    widthAux: int
    heightAux: int
    unk_3C: float
    unk_40: float
    unk_44: float
    unk_48: List[int]
    unk_4C: int
    primRGBA: Tuple[int, int, int, int]
    unk_54: int
    minLodValue: int
    unk_56: int
    unk_57: int
    envRGBA: Tuple[int, int, int, int]
    blendRGBA: Tuple[int, int, int, int]
    lightColor1: Tuple[int, int, int, int]
    lightColor2: Tuple[int, int, int, int]
    unk68: int
    unk6C: int
    unk70: int
    unk74: int
    images_array: List[int] = field(default_factory=list)  # resolved texture pointers


class ModelHeaderExtractor:
    def __init__(self, rom_path: str, vram_start: int, rom_start: int, name: str):
        self.rom_path = Path(rom_path)
        self.vram_start = vram_start
        self.rom_start = rom_start
        self.name = name
        self.rom_data = self.load_rom()

        # Calculate vram base
        self.vram_base = vram_start & 0xFFFF0000
        self.rom_base = rom_start - (vram_start & 0xFFFF)

        # Discovered structures
        self.materials_array: List[Optional[int]] = []  # List of VRAM pointers or None
        self.texture_ptr_arrays: Dict[int, List[Optional[int]]] = {}  # vram -> list of texture pointers
        self.textures: Dict[int, TextureInfo] = {}  # vram -> TextureInfo
        self.known_addresses: Set[int] = set()  # All known structure addresses

    def load_rom(self) -> bytes:
        with open(self.rom_path, 'rb') as f:
            return f.read()

    def vram_to_rom(self, vram_addr: int) -> int:
        offset_in_segment = vram_addr - self.vram_base
        return self.rom_base + offset_in_segment

    def read_u8(self, rom_addr: int) -> int:
        if rom_addr < 0 or rom_addr + 1 > len(self.rom_data):
            return 0
        return struct.unpack('>B', self.rom_data[rom_addr:rom_addr+1])[0]

    def read_u16(self, rom_addr: int) -> int:
        if rom_addr < 0 or rom_addr + 2 > len(self.rom_data):
            return 0
        return struct.unpack('>H', self.rom_data[rom_addr:rom_addr+2])[0]

    def read_u32(self, rom_addr: int) -> int:
        if rom_addr < 0 or rom_addr + 4 > len(self.rom_data):
            return 0
        return struct.unpack('>I', self.rom_data[rom_addr:rom_addr+4])[0]

    def read_s32(self, rom_addr: int) -> int:
        if rom_addr < 0 or rom_addr + 4 > len(self.rom_data):
            return 0
        return struct.unpack('>i', self.rom_data[rom_addr:rom_addr+4])[0]

    def read_float(self, rom_addr: int) -> float:
        if rom_addr < 0 or rom_addr + 4 > len(self.rom_data):
            return 0.0
        return struct.unpack('>f', self.rom_data[rom_addr:rom_addr+4])[0]

    def is_valid_pointer(self, ptr: int) -> bool:
        return (ptr >> 24) == 0x80 and ptr != 0x80000000

    def read_colorpack(self, rom_addr: int) -> Tuple[int, int, int, int]:
        """Read a ColorPack (4 bytes: r, g, b, a)."""
        r = self.read_u8(rom_addr)
        g = self.read_u8(rom_addr + 1)
        b = self.read_u8(rom_addr + 2)
        a = self.read_u8(rom_addr + 3)
        return (r, g, b, a)

    def parse_texture(self, vram_addr: int) -> TextureInfo:
        """Parse a Texture structure (0x78 bytes) - DON'T parse images array yet"""
        rom_addr = self.vram_to_rom(vram_addr)

        texture = TextureInfo(
            vram_addr=vram_addr,
            rom_addr=rom_addr,
            pad00=self.read_u16(rom_addr + 0x00),
            fmt=self.read_u8(rom_addr + 0x02),
            paletteBitDepth=self.read_u8(rom_addr + 0x03),
            images=self.read_u32(rom_addr + 0x04),
            scale=self.read_u16(rom_addr + 0x08),
            unk0A=self.read_u16(rom_addr + 0x0A),
            widthMain=self.read_u16(rom_addr + 0x0C),
            heightMain=self.read_u16(rom_addr + 0x0E),
            unk_10=self.read_s32(rom_addr + 0x10),
            unk_14=self.read_float(rom_addr + 0x14),
            unk_18=self.read_float(rom_addr + 0x18),
            scaleS=self.read_float(rom_addr + 0x1C),
            scaleT=self.read_float(rom_addr + 0x20),
            unk_24=self.read_float(rom_addr + 0x24),
            unk_28=self.read_float(rom_addr + 0x28),
            palettes=self.read_u32(rom_addr + 0x2C),
            flags=self.read_u16(rom_addr + 0x30),
            unk_32=self.read_u8(rom_addr + 0x32),
            unk_33=self.read_u8(rom_addr + 0x33),
            blockWidth=self.read_u16(rom_addr + 0x34),
            blockHeight=self.read_u16(rom_addr + 0x36),
            widthAux=self.read_u16(rom_addr + 0x38),
            heightAux=self.read_u16(rom_addr + 0x3A),
            unk_3C=self.read_float(rom_addr + 0x3C),
            unk_40=self.read_float(rom_addr + 0x40),
            unk_44=self.read_float(rom_addr + 0x44),
            unk_48=[self.read_u8(rom_addr + 0x48 + i) for i in range(4)],
            unk_4C=self.read_u32(rom_addr + 0x4C),
            primRGBA=self.read_colorpack(rom_addr + 0x50),
            unk_54=self.read_u8(rom_addr + 0x54),
            minLodValue=self.read_u8(rom_addr + 0x55),
            unk_56=self.read_u8(rom_addr + 0x56),
            unk_57=self.read_u8(rom_addr + 0x57),
            envRGBA=self.read_colorpack(rom_addr + 0x58),
            blendRGBA=self.read_colorpack(rom_addr + 0x5C),
            lightColor1=self.read_colorpack(rom_addr + 0x60),
            lightColor2=self.read_colorpack(rom_addr + 0x64),
            unk68=self.read_s32(rom_addr + 0x68),
            unk6C=self.read_s32(rom_addr + 0x6C),
            unk70=self.read_s32(rom_addr + 0x70),
            unk74=self.read_s32(rom_addr + 0x74),
        )

        # Don't parse images array yet - we need to know all texture addresses first

        return texture

    def parse_texture_images_array(self, texture: TextureInfo, next_addr: Optional[int] = None):
        """Parse the images array for a texture, knowing where it should end"""
        if not self.is_valid_pointer(texture.images):
            return

        images_rom = self.vram_to_rom(texture.images)

        # Determine max entries based on next address
        if next_addr:
            max_bytes = next_addr - texture.images
            max_entries = max_bytes // 4
        else:
            max_entries = 20  # Fallback

        # Read texture pointers until we hit NULL or reach max
        for i in range(min(max_entries, 100)):  # Cap at 100 for safety
            ptr = self.read_u32(images_rom + i * 4)
            if ptr == 0:
                break
            texture.images_array.append(ptr)

    def parse_texture_ptr_array(self, vram_addr: int, next_known_addr: Optional[int] = None) -> List[Optional[int]]:
        """Parse an array of Texture* pointers"""
        rom_addr = self.vram_to_rom(vram_addr)
        ptrs = []

        # Determine max size based on next known address
        if next_known_addr:
            max_size = (next_known_addr - vram_addr) // 4
        else:
            max_size = 100  # Fallback

        for i in range(max_size):
            ptr = self.read_u32(rom_addr + i * 4)
            if ptr == 0:
                ptrs.append(None)
                # Check if this is the end (NULL terminator)
                # Look ahead to see if next entry would start a new array
                if i > 0 and next_known_addr and (vram_addr + (i + 1) * 4) >= next_known_addr:
                    break
            elif self.is_valid_pointer(ptr):
                ptrs.append(ptr)
                # Parse the texture
                if ptr not in self.textures:
                    self.textures[ptr] = self.parse_texture(ptr)
                    self.known_addresses.add(ptr)
            else:
                # Invalid pointer, might be end of array
                break

        return ptrs

    def parse_materials_array(self):
        """Parse the main materials array (Texture**)"""
        rom_addr = self.vram_to_rom(self.vram_start)

        # First pass: collect all valid pointers to find the range
        temp_ptrs = []
        valid_ptrs_in_segment = []  # Only pointers that come after materials array
        for i in range(1000):  # Max entries
            ptr = self.read_u32(rom_addr + i * 4)
            temp_ptrs.append(ptr)
            # Only consider pointers that come after the materials array start
            # (pointers before are external references)
            if self.is_valid_pointer(ptr) and ptr > self.vram_start:
                valid_ptrs_in_segment.append(ptr)

        # Find the minimum pointer address in our segment - this tells us where data starts
        if valid_ptrs_in_segment:
            min_data_addr = min(valid_ptrs_in_segment)
            # Materials array ends before the first data structure
            max_materials_entries = (min_data_addr - self.vram_start) // 4

            # Now parse only the materials array portion
            self.materials_array = []
            for i in range(max_materials_entries):
                ptr = temp_ptrs[i]
                if ptr == 0:
                    self.materials_array.append(None)
                elif self.is_valid_pointer(ptr):
                    self.materials_array.append(ptr)
                    # Only track addresses in our segment for structure parsing
                    if ptr > self.vram_start:
                        self.known_addresses.add(ptr)
                else:
                    # Shouldn't happen in the range we calculated
                    self.materials_array.append(None)
        else:
            self.materials_array = []

        # Second pass: parse each Texture* array
        sorted_addrs = sorted(self.known_addresses)

        for i, ptr in enumerate(self.materials_array):
            if ptr is not None:
                # Find next address for size calculation
                ptr_idx = sorted_addrs.index(ptr) if ptr in sorted_addrs else -1
                next_addr = sorted_addrs[ptr_idx + 1] if ptr_idx >= 0 and ptr_idx + 1 < len(sorted_addrs) else None

                tex_ptrs = self.parse_texture_ptr_array(ptr, next_addr)
                self.texture_ptr_arrays[ptr] = tex_ptrs

    def extract_all(self):
        """Main extraction logic"""
        print(f"Parsing materials array at 0x{self.vram_start:08X}...")
        self.parse_materials_array()

        print(f"Found {len(self.materials_array)} material entries")
        print(f"Found {len(self.texture_ptr_arrays)} texture pointer arrays")
        print(f"Found {len(self.textures)} textures")

        # Second pass: parse images arrays now that we know all texture addresses
        # Collect all relevant addresses (images arrays AND texture structures)
        all_addrs = []

        # Add all images pointer addresses
        for texture in self.textures.values():
            if self.is_valid_pointer(texture.images):
                all_addrs.append(texture.images)

        # Add all texture structure addresses (in our segment)
        for texture in self.textures.values():
            if texture.vram_addr > self.vram_start:  # Only in our segment
                all_addrs.append(texture.vram_addr)

        # Add all Texture* array addresses (in our segment)
        for ptr_array_vram in self.texture_ptr_arrays.keys():
            if ptr_array_vram > self.vram_start:
                all_addrs.append(ptr_array_vram)

        # Sort to determine next addresses
        all_addrs.sort()

        # Parse each images array with knowledge of where it ends
        for texture in self.textures.values():
            if self.is_valid_pointer(texture.images):
                # Find next address after this images array
                next_addr = None
                for addr in all_addrs:
                    if addr > texture.images:
                        next_addr = addr
                        break

                self.parse_texture_images_array(texture, next_addr)

        print(f"Parsed {sum(1 for t in self.textures.values() if t.images_array)} texture frame arrays")

    def format_gfx_format(self, value: int) -> str:
        """Format a G_IM_FMT constant."""
        formats = {
            0: "G_IM_FMT_RGBA",
            1: "G_IM_FMT_YUV",
            2: "G_IM_FMT_CI",
            3: "G_IM_FMT_IA",
            4: "G_IM_FMT_I",
        }
        return formats.get(value, f"0x{value:X}")

    def format_gfx_size(self, value: int) -> str:
        """Format a G_IM_SIZ constant."""
        sizes = {
            0: "G_IM_SIZ_4b",
            1: "G_IM_SIZ_8b",
            2: "G_IM_SIZ_16b",
            3: "G_IM_SIZ_32b",
            5: "G_IM_SIZ_DD",
        }
        return sizes.get(value, f"0x{value:X}")

    def format_float(self, f: float) -> str:
        """Format a float in a way that matches C float literals."""
        if f == 0.0:
            return "0.0"
        elif f == 1.0:
            return "1.0"
        elif f == int(f):
            return f"{int(f)}.0"
        else:
            return repr(f)

    def format_colorpack(self, color: Tuple[int, int, int, int]) -> str:
        """Format a ColorPack as a C initializer."""
        return f"{{ {color[0]}, {color[1]}, {color[2]}, {color[3]} }}"

    def format_pointer(self, ptr: int, as_texture_name: bool = False) -> str:
        """Format a pointer value."""
        if ptr == 0:
            return "NULL"
        if as_texture_name:
            return f"{self.name}_tex_{ptr:08X}"
        return f"(u8*)0x{ptr:08X}"

    def generate_code(self) -> str:
        """Generate C code for all structures"""
        lines = []

        # Build part number mapping (use array index as part number)
        part_info = {}  # vram of texture_ptr_array -> part number
        for idx, mat_ptr in enumerate(self.materials_array):
            if mat_ptr is not None:
                if mat_ptr not in part_info:
                    part_info[mat_ptr] = idx

        # Collect all unique texture addresses for extern declarations
        all_texture_ptrs = set()
        for texture in self.textures.values():
            for tex_ptr in texture.images_array:
                if tex_ptr != 0:
                    all_texture_ptrs.add(tex_ptr)

        # Generate extern declarations
        if all_texture_ptrs:
            for tex_ptr in sorted(all_texture_ptrs):
                lines.append(f"extern u8 {self.name}_tex_{tex_ptr:08X}[];")
            lines.append("")

        # Generate materials array FIRST (lowest ROM address)
        lines.append(f"Texture** {self.name}_materials[] = {{")
        for mat_ptr in self.materials_array:
            if mat_ptr is None:
                lines.append(f"    NULL,")
            else:
                part = part_info.get(mat_ptr)
                if part is not None:
                    lines.append(f"    {self.name}_part{part}_mat,")
                else:
                    lines.append(f"    NULL, // TODO: 0x{mat_ptr:08X}")
        lines.append("};")
        lines.append("")

        # Generate texture frame arrays SECOND (u8* arrays)
        for tex_vram, texture in self.textures.items():
            if texture.images_array:
                # Find which part this texture belongs to
                part = None
                mat_idx = None
                for ptr_array_vram, tex_ptrs in self.texture_ptr_arrays.items():
                    if tex_vram in tex_ptrs:
                        part = part_info.get(ptr_array_vram)
                        mat_idx = tex_ptrs.index(tex_vram)
                        break

                if part is not None and mat_idx is not None:
                    lines.append(f"u8* {self.name}_part{part}_mat{mat_idx}_textures[] = {{")
                    for tex_ptr in texture.images_array:
                        lines.append(f"    {self.format_pointer(tex_ptr, as_texture_name=True)},")
                    lines.append("};")
                    lines.append("")

        # Generate Texture structures THIRD
        for tex_vram, texture in self.textures.items():
            # Find which part/mat this is
            part = None
            mat_idx = None
            for ptr_array_vram, tex_ptrs in self.texture_ptr_arrays.items():
                if tex_vram in tex_ptrs:
                    part = part_info.get(ptr_array_vram)
                    mat_idx = tex_ptrs.index(tex_vram)
                    break

            if part is not None and mat_idx is not None:
                lines.append(f"Texture {self.name}_part{part}_mat{mat_idx} = {{")
                lines.append(f"    {texture.pad00},")
                lines.append(f"    {self.format_gfx_format(texture.fmt)},")
                lines.append(f"    {self.format_gfx_size(texture.paletteBitDepth)},")

                # images pointer
                if texture.images_array:
                    lines.append(f"    {self.name}_part{part}_mat{mat_idx}_textures,")
                else:
                    lines.append(f"    {self.format_pointer(texture.images)},")

                lines.append(f"    {texture.scale},")
                lines.append(f"    {texture.unk0A},")
                lines.append(f"    {texture.widthMain},")
                lines.append(f"    {texture.heightMain},")
                lines.append(f"    {texture.unk_10},")
                lines.append(f"    {self.format_float(texture.unk_14)},")
                lines.append(f"    {self.format_float(texture.unk_18)},")
                lines.append(f"    {self.format_float(texture.scaleS)},")
                lines.append(f"    {self.format_float(texture.scaleT)},")
                lines.append(f"    {self.format_float(texture.unk_24)},")
                lines.append(f"    {self.format_float(texture.unk_28)},")
                lines.append(f"    {self.format_pointer(texture.palettes)},")
                lines.append(f"    0x{texture.flags:X},")
                lines.append(f"    {self.format_gfx_format(texture.unk_32)},")
                lines.append(f"    {self.format_gfx_size(texture.unk_33)},")
                lines.append(f"    {texture.blockWidth},")
                lines.append(f"    {texture.blockHeight},")
                lines.append(f"    {texture.widthAux},")
                lines.append(f"    {texture.heightAux},")
                lines.append(f"    {self.format_float(texture.unk_3C)},")
                lines.append(f"    {self.format_float(texture.unk_40)},")
                lines.append(f"    {self.format_float(texture.unk_44)},")
                lines.append(f"    {{ {', '.join(str(x) for x in texture.unk_48)} }},")
                lines.append(f"    {texture.unk_4C},")
                lines.append(f"    {self.format_colorpack(texture.primRGBA)},")
                lines.append(f"    {texture.unk_54},")
                lines.append(f"    {texture.minLodValue},")
                lines.append(f"    {texture.unk_56},")
                lines.append(f"    {texture.unk_57},")
                # All ColorPack fields formatted as structs
                lines.append(f"    {self.format_colorpack(texture.envRGBA)},")
                lines.append(f"    {self.format_colorpack(texture.blendRGBA)},")
                lines.append(f"    {self.format_colorpack(texture.lightColor1)},")
                lines.append(f"    {self.format_colorpack(texture.lightColor2)},")
                lines.append(f"    {texture.unk68},")
                lines.append(f"    {texture.unk6C},")
                lines.append(f"    {texture.unk70},")
                lines.append(f"    {texture.unk74},")
                lines.append("};")
                lines.append("")

        # Generate Texture* arrays LAST (highest ROM address in the segment)
        for ptr_array_vram in self.texture_ptr_arrays.keys():
            tex_ptrs = self.texture_ptr_arrays[ptr_array_vram]
            part = part_info.get(ptr_array_vram)

            if part is not None:
                lines.append(f"Texture* {self.name}_part{part}_mat[] = {{")
                for i, tex_ptr in enumerate(tex_ptrs):
                    if tex_ptr is None:
                        lines.append(f"    NULL,")
                    else:
                        lines.append(f"    &{self.name}_part{part}_mat{i},")
                lines.append("};")
                lines.append("")

        return '\n'.join(lines)


def main():
    if len(sys.argv) != 5:
        print("Usage: uv run tools/model_header.py <rom_file> <vram_addr> <rom_addr> <name>")
        print("Example: uv run tools/model_header.py pokemonsnap.z64 80323FD0 7751D0 moltres")
        sys.exit(1)

    rom_file = sys.argv[1]
    vram_addr = int(sys.argv[2], 16)
    rom_addr = int(sys.argv[3], 16)
    name = sys.argv[4]

    extractor = ModelHeaderExtractor(rom_file, vram_addr, rom_addr, name)
    extractor.extract_all()

    print("\n" + "="*80)
    print("GENERATED C CODE:")
    print("="*80)
    print(extractor.generate_code())


if __name__ == '__main__':
    main()

