#!/usr/bin/env python3
"""
Parse Texture structure from a ROM file.

Usage: uv run parse_texture.py rom.z64 <offset>

Example: uv run parse_texture.py pokemonsnap.z64 6B3958
"""

import struct
import sys
import argparse


def read_u8(data, offset):
    """Read a big-endian u8 from data at offset."""
    return struct.unpack_from('>B', data, offset)[0]


def read_u16(data, offset):
    """Read a big-endian u16 from data at offset."""
    return struct.unpack_from('>H', data, offset)[0]


def read_u32(data, offset):
    """Read a big-endian u32 from data at offset."""
    return struct.unpack_from('>I', data, offset)[0]


def read_s32(data, offset):
    """Read a big-endian s32 from data at offset."""
    return struct.unpack_from('>i', data, offset)[0]


def read_f32(data, offset):
    """Read a big-endian f32 from data at offset."""
    return struct.unpack_from('>f', data, offset)[0]


def format_float(f):
    """Format a float in a way that matches C float literals."""
    if f == 0.0:
        return "0.0"
    elif f == 1.0:
        return "1.0"
    elif f == int(f):
        return f"{int(f)}.0"
    else:
        # Use repr to get full precision
        return repr(f)


def format_pointer(ptr):
    """Format a pointer value."""
    if ptr == 0:
        return "NULL"
    return f"0x{ptr:08X}"


def format_gfx_format(value):
    """Format a G_IM_FMT constant."""
    formats = {
        0: "G_IM_FMT_RGBA",
        1: "G_IM_FMT_YUV",
        2: "G_IM_FMT_CI",
        3: "G_IM_FMT_IA",
        4: "G_IM_FMT_I",
    }
    return formats.get(value, f"0x{value:X}")


def format_gfx_size(value):
    """Format a G_IM_SIZ constant."""
    sizes = {
        0: "G_IM_SIZ_4b",
        1: "G_IM_SIZ_8b",
        2: "G_IM_SIZ_16b",
        3: "G_IM_SIZ_32b",
        5: "G_IM_SIZ_DD",
    }
    return sizes.get(value, f"0x{value:X}")


def read_colorpack(data, offset):
    """Read a ColorPack (4 bytes: r, g, b, a)."""
    r = read_u8(data, offset)
    g = read_u8(data, offset + 1)
    b = read_u8(data, offset + 2)
    a = read_u8(data, offset + 3)
    return (r, g, b, a)


def format_colorpack(color):
    """Format a ColorPack as a C initializer."""
    return f"{{ {color[0]}, {color[1]}, {color[2]}, {color[3]} }}"


def parse_texture(data, offset):
    """Parse a Texture structure from data at offset.

    Structure layout (0x78 bytes total):
    See include/sys/om.h for full structure definition.
    """
    texture = {}

    # 0x00: u16 pad00
    texture['pad00'] = read_u16(data, offset + 0x00)

    # 0x02: u8 fmt
    texture['fmt'] = read_u8(data, offset + 0x02)

    # 0x03: u8 paletteBitDepth
    texture['paletteBitDepth'] = read_u8(data, offset + 0x03)

    # 0x04: u32 images (pointer)
    texture['images'] = read_u32(data, offset + 0x04)

    # 0x08: u16 scale
    texture['scale'] = read_u16(data, offset + 0x08)

    # 0x0A: u16 unk0A
    texture['unk0A'] = read_u16(data, offset + 0x0A)

    # 0x0C: u16 widthMain
    texture['widthMain'] = read_u16(data, offset + 0x0C)

    # 0x0E: u16 heightMain
    texture['heightMain'] = read_u16(data, offset + 0x0E)

    # 0x10: s32 unk_10
    texture['unk_10'] = read_s32(data, offset + 0x10)

    # 0x14: f32 unk_14
    texture['unk_14'] = read_f32(data, offset + 0x14)

    # 0x18: f32 unk_18
    texture['unk_18'] = read_f32(data, offset + 0x18)

    # 0x1C: f32 scaleS
    texture['scaleS'] = read_f32(data, offset + 0x1C)

    # 0x20: f32 scaleT
    texture['scaleT'] = read_f32(data, offset + 0x20)

    # 0x24: f32 unk_24
    texture['unk_24'] = read_f32(data, offset + 0x24)

    # 0x28: f32 unk_28
    texture['unk_28'] = read_f32(data, offset + 0x28)

    # 0x2C: u32 palettes (pointer)
    texture['palettes'] = read_u32(data, offset + 0x2C)

    # 0x30: u16 flags
    texture['flags'] = read_u16(data, offset + 0x30)

    # 0x32: u8 unk_32
    texture['unk_32'] = read_u8(data, offset + 0x32)

    # 0x33: u8 unk_33
    texture['unk_33'] = read_u8(data, offset + 0x33)

    # 0x34: u16 blockWidth
    texture['blockWidth'] = read_u16(data, offset + 0x34)

    # 0x36: u16 blockHeight
    texture['blockHeight'] = read_u16(data, offset + 0x36)

    # 0x38: u16 widthAux
    texture['widthAux'] = read_u16(data, offset + 0x38)

    # 0x3A: u16 heightAux
    texture['heightAux'] = read_u16(data, offset + 0x3A)

    # 0x3C: f32 unk_3C
    texture['unk_3C'] = read_f32(data, offset + 0x3C)

    # 0x40: f32 unk_40
    texture['unk_40'] = read_f32(data, offset + 0x40)

    # 0x44: f32 unk_44
    texture['unk_44'] = read_f32(data, offset + 0x44)

    # 0x48: char[4] unk_48
    texture['unk_48'] = [read_u8(data, offset + 0x48 + i) for i in range(4)]

    # 0x4C: u32 unk_4C
    texture['unk_4C'] = read_u32(data, offset + 0x4C)

    # 0x50: ColorPack primRGBA
    texture['primRGBA'] = read_colorpack(data, offset + 0x50)

    # 0x54: u8 unk_54
    texture['unk_54'] = read_u8(data, offset + 0x54)

    # 0x55: u8 minLodValue
    texture['minLodValue'] = read_u8(data, offset + 0x55)

    # 0x56: u8 unk_56
    texture['unk_56'] = read_u8(data, offset + 0x56)

    # 0x57: u8 unk_57
    texture['unk_57'] = read_u8(data, offset + 0x57)

    # 0x58: ColorPack envRGBA
    texture['envRGBA'] = read_colorpack(data, offset + 0x58)

    # 0x5C: ColorPack blendRGBA
    texture['blendRGBA'] = read_colorpack(data, offset + 0x5C)

    # 0x60: ColorPack lightColor1
    texture['lightColor1'] = read_colorpack(data, offset + 0x60)

    # 0x64: ColorPack lightColor2
    texture['lightColor2'] = read_colorpack(data, offset + 0x64)

    # 0x68: s32 unk68
    texture['unk68'] = read_s32(data, offset + 0x68)

    # 0x6C: s32 unk6C
    texture['unk6C'] = read_s32(data, offset + 0x6C)

    # 0x70: s32 unk70
    texture['unk70'] = read_s32(data, offset + 0x70)

    # 0x74: s32 unk74
    texture['unk74'] = read_s32(data, offset + 0x74)

    return texture


def format_texture(texture, name="texture_name"):
    """Format a Texture structure as C code."""
    lines = [
        f"Texture {name} = {{",
        f"    {texture['pad00']},",
        f"    {format_gfx_format(texture['fmt'])},",
        f"    {format_gfx_size(texture['paletteBitDepth'])},",
        f"    {format_pointer(texture['images'])},",
        f"    {texture['scale']},",
        f"    {texture['unk0A']},",
        f"    {texture['widthMain']},",
        f"    {texture['heightMain']},",
        f"    {texture['unk_10']},",
        f"    {format_float(texture['unk_14'])},",
        f"    {format_float(texture['unk_18'])},",
        f"    {format_float(texture['scaleS'])},",
        f"    {format_float(texture['scaleT'])},",
        f"    {format_float(texture['unk_24'])},",
        f"    {format_float(texture['unk_28'])},",
        f"    {format_pointer(texture['palettes'])},",
        f"    0x{texture['flags']:X},",
        f"    {format_gfx_format(texture['unk_32'])},",
        f"    {format_gfx_size(texture['unk_33'])},",
        f"    {texture['blockWidth']},",
        f"    {texture['blockHeight']},",
        f"    {texture['widthAux']},",
        f"    {texture['heightAux']},",
        f"    {format_float(texture['unk_3C'])},",
        f"    {format_float(texture['unk_40'])},",
        f"    {format_float(texture['unk_44'])},",
        f"    {{ {', '.join(str(x) for x in texture['unk_48'])} }},",
        f"    {texture['unk_4C']},",
        f"    {format_colorpack(texture['primRGBA'])},",
        f"    {texture['unk_54']},",
        f"    {texture['minLodValue']},",
        f"    {texture['unk_56']},",
        f"    {texture['unk_57']},",
        f"    {format_colorpack(texture['envRGBA'])},",
        f"    {format_colorpack(texture['blendRGBA'])},",
        f"    {format_colorpack(texture['lightColor1'])},",
        f"    {format_colorpack(texture['lightColor2'])},",
        f"    {texture['unk68']},",
        f"    {texture['unk6C']},",
        f"    {texture['unk70']},",
        f"    {texture['unk74']},",
        "};"
    ]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Parse Texture structure from a ROM file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example: uv run parse_texture.py pokemonsnap.z64 6B3958'
    )
    parser.add_argument('rom', help='Path to ROM file')
    parser.add_argument('offset', help='Offset (hex) of Texture structure')
    parser.add_argument('--name', default='texture_name', help='Variable name for the texture')

    args = parser.parse_args()

    rom_path = args.rom
    offset = int(args.offset, 16)
    name = args.name

    # Read ROM file
    try:
        with open(rom_path, 'rb') as f:
            rom_data = f.read()
    except FileNotFoundError:
        print(f"Error: ROM file '{rom_path}' not found", file=sys.stderr)
        sys.exit(1)

    # Validate offset
    if offset >= len(rom_data):
        print(f"Error: Offset 0x{offset:X} is out of range (ROM size: 0x{len(rom_data):X})", file=sys.stderr)
        sys.exit(1)

    if offset + 0x78 > len(rom_data):
        print(f"Error: Not enough data to read Texture structure (need 0x78 bytes from 0x{offset:X})", file=sys.stderr)
        sys.exit(1)

    # Parse and output the texture
    texture = parse_texture(rom_data, offset)
    formatted = format_texture(texture, name)
    print(formatted)


if __name__ == "__main__":
    main()

