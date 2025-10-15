#!/usr/bin/env python3
"""
Extract model data from Pokemon Snap ROM and generate model.c, splat config, and symbols.

Usage:
    uv run extract_model.py pokemonsnap.z64 <vram_model_start> <rom_model_start> <name>

Example:
    uv run extract_model.py pokemonsnap.z64 0x8032A688 0x77B888 moltres

The vram address should point to the UnkEC64Arg3 array (model data).
"""

import struct
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field

from pygfxd import (
    gfxd_input_buffer,
    gfxd_output_buffer,
    gfxd_target,
    gfxd_endian,
    gfxd_execute,
    gfxd_buffer_to_string,
    GfxdEndian,
    gfxd_f3dex2,
)

ENTRY_SIZE = 44  # UnkEC64Arg3 size

@dataclass
class UnkEC64Arg3Entry:
    index: int
    pointer: int
    pos: Tuple[float, float, float]
    rot: Tuple[float, float, float]
    scale: Tuple[float, float, float]

@dataclass
class DObjPayload:
    vram_addr: int
    rom_addr: int
    type: str  # 'I', 'C', 'J'
    ptr1: int
    ptr2: int
    ptr3: Optional[int] = None
    is_first: bool = False
    is_last: bool = False

@dataclass
class DisplayListInfo:
    name: str
    vram_addr: int
    rom_addr: int
    size: int
    has_lod: bool = False  # Has near/far LOD branching
    num_lod_branches: int = 0  # Number of LOD branches (0, 1, or 2)
    lod_near_addr: int = 0  # VRAM address of near LOD variant
    lod_far_addr: int = 0   # VRAM address of far LOD variant
    dlist_calls: List[int] = field(default_factory=list)  # gsSPDisplayList references
    vertex_addresses: Set[int] = field(default_factory=set)  # VRAM addresses of vertices used
    data: bytes = field(default_factory=bytes)

class ModelExtractor:
    def __init__(self, rom_path: str, segment: str, vram_model_start: int, rom_model_start: int, name: str, variant: Optional[str] = None, segment_override: Optional[str] = None):
        self.rom_path = Path(rom_path)
        # Use segment_override if provided, otherwise append _code to segment
        self.segment_name = segment_override if segment_override else (segment + "_code")
        self.segment_dir = segment  # Keep the directory name separate for file paths
        self.vram_model_start = vram_model_start
        self.rom_model_start = rom_model_start
        self.name = name
        self.variant = variant
        self.rom_data = self.load_rom()

        self.entries: List[UnkEC64Arg3Entry] = []
        self.payloads: List[DObjPayload] = []
        self.dlists: Dict[int, DisplayListInfo] = {}  # vram -> DisplayListInfo
        self.parsing_dlists: Set[int] = set()  # Track display lists currently being parsed
        self.vtx_size = 0x2350  # Default, will be calculated
        self.vtx_vram_start = 0  # Will be calculated

        # Calculate vram base
        self.vram_base = vram_model_start & 0xFFFF0000
        self.rom_base = rom_model_start - (vram_model_start & 0xFFFF)

    def get_file_name(self, base_name: str) -> str:
        """Get file name with variant prefix (e.g., 'hd_first' or 'first')"""
        if self.variant:
            return f'{self.variant}_{base_name}'
        return base_name

    def get_symbol_name(self, base_name: str) -> str:
        """Get symbol name with variant infix (e.g., 'mew_hd_first' or 'mew_first')"""
        if self.variant:
            return f'{self.name}_{self.variant}_{base_name}'
        return f'{self.name}_{base_name}'

    def load_rom(self) -> bytes:
        with open(self.rom_path, 'rb') as f:
            return f.read()

    def vram_to_rom(self, vram_addr: int) -> int:
        offset_in_segment = vram_addr - self.vram_base
        return self.rom_base + offset_in_segment

    def rom_to_vram(self, rom_addr: int) -> int:
        offset_in_segment = rom_addr - self.rom_base
        return self.vram_base + offset_in_segment

    def read_u32(self, rom_addr: int) -> int:
        if rom_addr < 0 or rom_addr + 4 > len(self.rom_data):
            return 0
        return struct.unpack('>I', self.rom_data[rom_addr:rom_addr+4])[0]

    def read_float(self, rom_addr: int) -> float:
        if rom_addr < 0 or rom_addr + 4 > len(self.rom_data):
            return 0.0
        return struct.unpack('>f', self.rom_data[rom_addr:rom_addr+4])[0]

    def is_valid_pointer(self, ptr: int) -> bool:
        return (ptr >> 24) == 0x80 and ptr != 0x80000000

    def parse_unkec64arg3(self) -> int:
        """Parse UnkEC64Arg3 array"""
        rom_addr = self.rom_model_start
        count = 0
        max_entries = 100

        for _ in range(max_entries):
            if rom_addr + ENTRY_SIZE > len(self.rom_data):
                break

            index = self.read_u32(rom_addr)
            pointer = self.read_u32(rom_addr + 4)
            pos = tuple(self.read_float(rom_addr + 8 + i*4) for i in range(3))
            rot = tuple(self.read_float(rom_addr + 20 + i*4) for i in range(3))
            scale = tuple(self.read_float(rom_addr + 32 + i*4) for i in range(3))

            # Check for terminator: ONLY null pointer indicates end of array
            # A terminator has pointer=0 and all zero vectors (pos, rot, scale all 0)
            is_terminator = (pointer == 0 and
                           pos == (0.0, 0.0, 0.0) and
                           rot == (0.0, 0.0, 0.0) and
                           scale == (0.0, 0.0, 0.0))

            # Add the entry regardless of index value - index doesn't indicate termination
            entry = UnkEC64Arg3Entry(index, pointer, pos, rot, scale)
            self.entries.append(entry)

            count += 1
            rom_addr += ENTRY_SIZE

            if is_terminator and count > 1:
                # Found terminator after reading at least one valid entry
                # (the terminator has already been added to the list)
                break

        return count

    def parse_display_list(self, vram_addr: int, name: str) -> Optional[DisplayListInfo]:
        """Parse a display list using pygfxd to find its size and properties"""
        # Prevent circular references
        if vram_addr in self.parsing_dlists:
            return None

        rom_addr = self.vram_to_rom(vram_addr)

        if rom_addr < 0 or rom_addr >= len(self.rom_data):
            return None

        # Mark as being parsed
        self.parsing_dlists.add(vram_addr)

        # Read up to 4KB for display list (should be way more than enough)
        max_read = min(0x1000, len(self.rom_data) - rom_addr)
        dlist_data = self.rom_data[rom_addr:rom_addr + max_read]

        # Use pygfxd to parse the display list
        gfxd_input_buffer(dlist_data)

        # Create output buffer
        outb = bytes([0] * len(dlist_data) * 100)
        outbuf = gfxd_output_buffer(outb, len(outb))

        gfxd_target(gfxd_f3dex2)
        gfxd_endian(GfxdEndian.big, 4)

        # Parse
        gfxd_execute()

        # Get the parsed output
        parsed_output = gfxd_buffer_to_string(outbuf)

        # Analyze the parsed output
        has_lod = 'gsSPBranchLessZraw' in parsed_output
        vertex_addresses = set()
        branch_targets = []
        lod_branches = []  # Store LOD branch addresses in order
        dlist_calls = []  # Store gsSPDisplayList calls

        # Find vertex usage and branch targets from raw commands
        for offset in range(0, len(dlist_data), 8):
            cmd = self.read_u32(rom_addr + offset)
            cmd_type = (cmd >> 24) & 0xFF
            addr_word = self.read_u32(rom_addr + offset + 4)

            # gsSPEndDisplayList - stop parsing here
            if cmd_type == 0xDF:
                break

            # gsSPVertex command (0x01 in this game, 0x04 in standard F3DEX2)
            if cmd_type == 0x01 or cmd_type == 0x04:
                # If it's a valid VRAM address, collect it
                if (addr_word >> 24) == 0x80:
                    vertex_addresses.add(addr_word)

            # gsSPBranchLessZraw (0xE1) - LOD branching
            elif cmd_type == 0xE1:
                # First word contains branch target address
                branch_target = addr_word
                if (branch_target >> 24) == 0x80:
                    branch_targets.append(branch_target)
                    lod_branches.append(branch_target)  # Track for LOD variants

            # gsSPDisplayList (0xDE) - call to another display list
            elif cmd_type == 0xDE:
                if (addr_word >> 24) == 0x80:
                    dlist_calls.append(addr_word)

            # gsDPNoOpTag (0x00) - might contain display list references
            elif cmd_type == 0x00 and (addr_word >> 24) == 0x80:
                # Word2 contains a potential display list address
                branch_targets.append(addr_word)

        # Recursively collect vertices from branched display lists (depth 2)
        visited_branches = set()
        branches_to_process = list(branch_targets)

        while branches_to_process:
            branch_addr = branches_to_process.pop(0)
            if branch_addr in visited_branches:
                continue
            visited_branches.add(branch_addr)

            branch_rom = self.vram_to_rom(branch_addr)
            if not (0 <= branch_rom < len(self.rom_data)):
                continue

            # Read and parse the branched display list
            branch_data = self.rom_data[branch_rom:branch_rom + 0x200]
            for offset in range(0, len(branch_data), 8):
                cmd = self.read_u32(branch_rom + offset)
                cmd_type = (cmd >> 24) & 0xFF
                addr_word = self.read_u32(branch_rom + offset + 4)

                if cmd_type == 0x01 or cmd_type == 0x04:  # gsSPVertex
                    if (addr_word >> 24) == 0x80:
                        vertex_addresses.add(addr_word)
                elif cmd_type == 0xE1:  # gsSPBranchLessZraw
                    if (addr_word >> 24) == 0x80 and addr_word not in visited_branches:
                        branches_to_process.append(addr_word)
                elif cmd_type == 0x00 and (addr_word >> 24) == 0x80:  # gsDPNoOpTag
                    if addr_word not in visited_branches:
                        branches_to_process.append(addr_word)
                elif cmd_type == 0xDF:  # End of display list
                    break

        # Find the actual size by looking for gsSPEndDisplayList
        size = 0
        for offset in range(0, len(dlist_data), 8):
            cmd = self.read_u32(rom_addr + offset)
            if (cmd >> 24) == 0xDF:  # gsSPEndDisplayList
                size = offset + 8
                break

        if size == 0:
            size = len(dlist_data)

        data = self.rom_data[rom_addr:rom_addr + size]

        # Extract LOD near/far addresses based on number of branches
        num_lod_branches = len(lod_branches)

        # Validate LOD branch count
        if num_lod_branches > 2:
            print(f"WARNING: Display list {name} has {num_lod_branches} LOD branches (expected 0-2)")
            # Treat as if it has 2 branches for compatibility
            num_lod_branches = 2

        lod_near = lod_branches[0] if num_lod_branches >= 1 else 0
        lod_far = lod_branches[1] if num_lod_branches >= 2 else 0

        # Unmark as being parsed
        self.parsing_dlists.discard(vram_addr)

        return DisplayListInfo(
            name=name,
            vram_addr=vram_addr,
            rom_addr=rom_addr,
            size=size,
            has_lod=has_lod,
            num_lod_branches=num_lod_branches,
            lod_near_addr=lod_near,
            lod_far_addr=lod_far,
            dlist_calls=dlist_calls,
            vertex_addresses=vertex_addresses,
            data=data
        )


    def parse_lod_branches(self, dlist: DisplayListInfo):
        """Parse LOD branches for a display list after it's been added to self.dlists"""
        if dlist.lod_near_addr and dlist.lod_near_addr not in self.dlists:
            near_dlist = self.parse_display_list(dlist.lod_near_addr, f'{dlist.name}_near')
            if near_dlist:
                self.dlists[dlist.lod_near_addr] = near_dlist
                # Recursively parse branches of the near display list
                self.parse_lod_branches(near_dlist)

        if dlist.lod_far_addr and dlist.lod_far_addr not in self.dlists:
            far_dlist = self.parse_display_list(dlist.lod_far_addr, f'{dlist.name}_far')
            if far_dlist:
                self.dlists[dlist.lod_far_addr] = far_dlist
                # Recursively parse branches of the far display list
                self.parse_lod_branches(far_dlist)

    def parse_dlist_calls(self, dlist: DisplayListInfo, base_name: str, part_num: int = 0):
        """Parse gsSPDisplayList calls for first/last display lists

        Only parse if this is actually the first/last gfxdata entry.
        The targets of these calls get the part number based on the gfxdata position.

        Args:
            dlist: The display list to parse calls from
            base_name: 'first' or 'last'
            part_num: The position-based part number for this entry
        """
        # Only parse gsSPDisplayList calls from first/last
        if base_name not in ['first', 'last']:
            return

        for i, call_addr in enumerate(dlist.dlist_calls):
            if call_addr not in self.dlists:
                # The target uses the position-based part number
                call_name = f'part{part_num + i}_draw'

                called_dlist = self.parse_display_list(call_addr, call_name)
                if called_dlist:
                    self.dlists[call_addr] = called_dlist
                    # Also parse LOD branches for the called display list
                    self.parse_lod_branches(called_dlist)

    def parse_dobj_payload(self, vram_addr: int, payload_type: str, part_num: int, is_first: bool, is_last: bool) -> DObjPayload:
        """Parse DObjPayloadTypeI/C/J structure - type must be specified"""
        rom_addr = self.vram_to_rom(vram_addr)

        ptr1 = self.read_u32(rom_addr)
        ptr2 = self.read_u32(rom_addr + 4)
        ptr3 = None
        if payload_type == 'J':
            ptr3 = self.read_u32(rom_addr + 8)

        # Parse display lists based on type
        if payload_type == 'I':
            if ptr1 == 0 and ptr2 != 0:
                if is_first:
                    dlist = self.parse_display_list(ptr2, 'first')
                    if dlist:
                        self.dlists[ptr2] = dlist
                        self.parse_lod_branches(dlist)
                        self.parse_dlist_calls(dlist, 'first', part_num)
                elif is_last:
                    dlist = self.parse_display_list(ptr2, 'last')
                    if dlist:
                        self.dlists[ptr2] = dlist
                        self.parse_lod_branches(dlist)
                        self.parse_dlist_calls(dlist, 'last', part_num)
                else:
                    dlist = self.parse_display_list(ptr2, f'part{part_num}_draw')
                    if dlist:
                        self.dlists[ptr2] = dlist
                        self.parse_lod_branches(dlist)
            else:
                # Both ptr1 and ptr2 are non-zero
                if is_last:
                    # For last entry, ptr2 gets named 'last'
                    if ptr2 != 0:
                        dlist = self.parse_display_list(ptr2, 'last')
                        if dlist:
                            self.dlists[ptr2] = dlist
                            self.parse_lod_branches(dlist)
                            self.parse_dlist_calls(dlist, 'last', part_num)
                    # ptr1 still uses the part number
                    if ptr1 != 0:
                        dlist = self.parse_display_list(ptr1, f'part{part_num}_pre')
                        if dlist:
                            self.dlists[ptr1] = dlist
                            self.parse_lod_branches(dlist)
                else:
                    # Regular entry
                    if ptr1 != 0:
                        dlist = self.parse_display_list(ptr1, f'part{part_num}_pre')
                        if dlist:
                            self.dlists[ptr1] = dlist
                            self.parse_lod_branches(dlist)
                    if ptr2 != 0:
                        dlist = self.parse_display_list(ptr2, f'part{part_num}_draw')
                        if dlist:
                            self.dlists[ptr2] = dlist
                            self.parse_lod_branches(dlist)
        elif payload_type == 'C':
            if ptr2 != 0:
                if is_first:
                    dlist = self.parse_display_list(ptr2, 'first')
                    if dlist:
                        self.dlists[ptr2] = dlist
                        self.parse_lod_branches(dlist)
                        self.parse_dlist_calls(dlist, 'first', part_num)
                elif is_last:
                    dlist = self.parse_display_list(ptr2, 'last')
                    if dlist:
                        self.dlists[ptr2] = dlist
                        self.parse_lod_branches(dlist)
                        self.parse_dlist_calls(dlist, 'last', part_num)
                else:
                    dlist = self.parse_display_list(ptr2, f'part{part_num}_draw')
                    if dlist:
                        self.dlists[ptr2] = dlist
                        self.parse_lod_branches(dlist)
        elif payload_type == 'J':
            if is_first:
                if ptr3 != 0:
                    dlist = self.parse_display_list(ptr3, 'first')
                    if dlist:
                        self.dlists[ptr3] = dlist
                        self.parse_lod_branches(dlist)
                        self.parse_dlist_calls(dlist, 'first', part_num)
            elif is_last:
                if ptr3 != 0:
                    dlist = self.parse_display_list(ptr3, 'last')
                    if dlist:
                        self.dlists[ptr3] = dlist
                        self.parse_lod_branches(dlist)
                        self.parse_dlist_calls(dlist, 'last', part_num)
            else:
                if ptr2 != 0:
                    dlist = self.parse_display_list(ptr2, f'part{part_num}_pre')
                    if dlist:
                        self.dlists[ptr2] = dlist
                        self.parse_lod_branches(dlist)
                if ptr3 != 0:
                    dlist = self.parse_display_list(ptr3, f'part{part_num}_draw')
                    if dlist:
                        self.dlists[ptr3] = dlist
                        self.parse_lod_branches(dlist)

        return DObjPayload(vram_addr, rom_addr, payload_type, ptr1, ptr2, ptr3, is_first, is_last)

    def dump_raw_gfxdata(self, start_vram: int, end_vram: int, referenced_pointers: List[int]):
        """Dump raw gfxdata for inspection"""
        start_rom = self.vram_to_rom(start_vram)
        size = end_vram - start_vram
        num_words = size // 4

        print(f"\n{'='*80}")
        print(f"RAW GFXDATA DUMP (0x{start_vram:08X} - 0x{end_vram:08X})")
        print(f"{'='*80}\n")

        referenced_set = set(referenced_pointers)

        for i in range(num_words):
            offset = i * 4
            word_vram = start_vram + offset
            word = self.read_u32(start_rom + offset)

            marker = '*' if word_vram in referenced_set else ' '
            print(f"{marker} +0x{offset:04X} (0x{word_vram:08X}): 0x{word:08X}")

    def extract_all(self, payload_type: Optional[str] = None):
        """Main extraction logic

        Args:
            payload_type: Optional type override - 'direct', 'i', 'c', 'j', or None for analysis
        """
        # Step 1: Parse UnkEC64Arg3 array first
        count = self.parse_unkec64arg3()
        print(f"Found {count} UnkEC64Arg3 entries")

        # Step 2: Determine gfxdata array bounds from UnkEC64Arg3 pointers
        non_null_entries = [(i, e) for i, e in enumerate(self.entries) if e.pointer != 0]

        if not non_null_entries:
            print("No non-null pointers - direct model with no intermediate array")
            if payload_type is None:
                print("\nNo gfxdata array to inspect")
            return

        pointers = [e.pointer for i, e in non_null_entries]
        gfxdata_start_vram = min(pointers)
        gfxdata_end_vram = self.vram_model_start
        gfxdata_size = gfxdata_end_vram - gfxdata_start_vram

        print(f"Potential gfxdata array: 0x{gfxdata_start_vram:08X} - 0x{gfxdata_end_vram:08X} (0x{gfxdata_size:X} bytes)")

        # Step 3: If no type specified, dump raw data for inspection
        if payload_type is None:
            self.dump_raw_gfxdata(gfxdata_start_vram, gfxdata_end_vram, pointers)
            return

        # Step 4: Parse based on specified type
        if payload_type == 'direct':
            structure_type = 'direct'
            struct_size = 0
        elif payload_type == 'i':
            structure_type = 'intermediate'
            struct_size = 0x08
        elif payload_type == 'c':
            structure_type = 'intermediate'
            struct_size = 0x08
        elif payload_type == 'j':
            structure_type = 'intermediate'
            struct_size = 0x0C
        else:
            print(f"Unknown payload type: {payload_type}")
            return

        print(f"Using type: {payload_type.upper()}" + (f" (size: 0x{struct_size:X} bytes)" if struct_size else ""))

        # Step 5: Parse the gfxdata array
        if structure_type == 'intermediate':
            array_start_vram = gfxdata_start_vram
            array_start_rom = self.vram_to_rom(array_start_vram)
            array_end_vram = gfxdata_end_vram

            array_size = array_end_vram - array_start_vram
            num_entries = array_size // struct_size

            print(f"Parsing gfxdata array: {num_entries} entries (struct size: 0x{struct_size:X})")

            # Step 5a: First pass - parse all display lists with temporary names to detect gsSPDisplayList calls
            temp_dlists_by_entry = {}  # entry_idx -> list of (ptr_addr, dlist)
            for entry_idx in range(num_entries):
                entry_vram = array_start_vram + (entry_idx * struct_size)
                entry_rom = array_start_rom + (entry_idx * struct_size)

                # Check if this entry is referenced by any UnkEC64Arg3
                is_referenced = any(e.pointer == entry_vram for e in self.entries if e.pointer != 0)
                if not is_referenced:
                    continue

                # Read pointers
                ptr1 = self.read_u32(entry_rom)
                ptr2 = self.read_u32(entry_rom + 4)
                ptr3 = self.read_u32(entry_rom + 8) if struct_size == 0x0C else None

                # Parse display lists to check for gsSPDisplayList calls
                temp_dlists = []
                if payload_type.upper() == 'I':
                    if ptr1 != 0:
                        dlist = self.parse_display_list(ptr1, f'temp_{entry_idx}_ptr1')
                        if dlist:
                            temp_dlists.append((ptr1, dlist))
                    if ptr2 != 0:
                        dlist = self.parse_display_list(ptr2, f'temp_{entry_idx}_ptr2')
                        if dlist:
                            temp_dlists.append((ptr2, dlist))
                elif payload_type.upper() == 'C':
                    if ptr2 != 0:
                        dlist = self.parse_display_list(ptr2, f'temp_{entry_idx}')
                        if dlist:
                            temp_dlists.append((ptr2, dlist))
                elif payload_type.upper() == 'J':
                    if ptr2 != 0:
                        dlist = self.parse_display_list(ptr2, f'temp_{entry_idx}_ptr2')
                        if dlist:
                            temp_dlists.append((ptr2, dlist))
                    if ptr3 != 0:
                        dlist = self.parse_display_list(ptr3, f'temp_{entry_idx}_ptr3')
                        if dlist:
                            temp_dlists.append((ptr3, dlist))

                if temp_dlists:
                    temp_dlists_by_entry[entry_idx] = temp_dlists

            # Step 5b: Find entries with gsSPDisplayList calls
            entries_with_calls = []
            for entry_idx in sorted(temp_dlists_by_entry.keys()):
                for ptr_addr, dlist in temp_dlists_by_entry[entry_idx]:
                    if dlist.dlist_calls:
                        entries_with_calls.append(entry_idx)
                        break  # Only need to find one dlist with calls per entry

            # Step 5c: Determine which entries should be named first/last
            first_entry_idx = entries_with_calls[0] if entries_with_calls else None
            last_entry_idx = entries_with_calls[-1] if entries_with_calls else None

            # Step 5d: Second pass - parse with proper names
            self.payloads = []
            # Count non-padding, referenced entries to determine position-based part numbers
            non_padding_count = 0  # This tracks the natural part number (0, 1, 2, ...)
            part_counter = 1 if first_entry_idx is not None else 0  # For display list naming

            for entry_idx in range(num_entries):
                entry_vram = array_start_vram + (entry_idx * struct_size)
                entry_rom = array_start_rom + (entry_idx * struct_size)

                # Check if this entry is referenced by any UnkEC64Arg3
                is_referenced = any(e.pointer == entry_vram for e in self.entries if e.pointer != 0)

                if is_referenced:
                    # Determine if it's first/last based on gsSPDisplayList calls
                    is_first = (entry_idx == first_entry_idx)
                    is_last = (entry_idx == last_entry_idx)

                    # The part number is always the position-based count (for targets of first/last)
                    part_num = non_padding_count
                    non_padding_count += 1

                    payload = self.parse_dobj_payload(entry_vram, payload_type.upper(), part_num, is_first, is_last)
                    self.payloads.append(payload)

                    # Increment part_counter for naming regular display lists
                    if not (is_first or is_last):
                        part_counter += 1
                else:
                    # Read the entry to determine if it's truly NULL or just unreferenced
                    ptr1 = self.read_u32(entry_rom)
                    ptr2 = self.read_u32(entry_rom + 4)
                    ptr3 = self.read_u32(entry_rom + 8) if struct_size == 0x0C else None

                    # Use specified type for consistency
                    entry_type = payload_type.upper()

                    # Check if this is a padding entry
                    is_padding = (ptr1 == 4 and ptr2 == 0 and (ptr3 == 0 if ptr3 is not None else True))

                    # Parse display lists even for unreferenced entries (but not padding)
                    if not is_padding:
                        if entry_type == 'I':
                            # For TypeI, parse ptr1 and ptr2 as display lists
                            if ptr1 != 0 and ptr1 not in self.dlists:
                                dlist = self.parse_display_list(ptr1, f'part{part_counter}_pre')
                                if dlist:
                                    self.dlists[ptr1] = dlist
                                    self.parse_lod_branches(dlist)
                            if ptr2 != 0 and ptr2 not in self.dlists:
                                dlist = self.parse_display_list(ptr2, f'part{part_counter}_draw')
                                if dlist:
                                    self.dlists[ptr2] = dlist
                                    self.parse_lod_branches(dlist)
                            part_counter += 1
                        elif entry_type == 'C' and ptr2 != 0 and ptr2 not in self.dlists:
                            # For TypeC, parse ptr2 as display list
                            dlist = self.parse_display_list(ptr2, f'part{part_counter}_draw')
                            if dlist:
                                self.dlists[ptr2] = dlist
                                self.parse_lod_branches(dlist)
                            part_counter += 1
                        elif entry_type == 'J':
                            # For TypeJ, parse ptr2 and ptr3 as display lists
                            if ptr2 != 0 and ptr2 not in self.dlists:
                                dlist = self.parse_display_list(ptr2, f'part{part_counter}_pre')
                                if dlist:
                                    self.dlists[ptr2] = dlist
                                    self.parse_lod_branches(dlist)
                            if ptr3 != 0 and ptr3 not in self.dlists:
                                dlist = self.parse_display_list(ptr3, f'part{part_counter}_draw')
                                if dlist:
                                    self.dlists[ptr3] = dlist
                                    self.parse_lod_branches(dlist)
                            part_counter += 1

                    # Create entry (possibly with data, possibly NULL)
                    self.payloads.append(DObjPayload(
                        vram_addr=entry_vram,
                        rom_addr=entry_rom,
                        type=entry_type,
                        ptr1=ptr1,
                        ptr2=ptr2,
                        ptr3=ptr3,
                        is_first=False,
                        is_last=False
                    ))

        else:
            # Direct pointers to display lists
            # Step 1: Parse all display lists with temporary names to detect gsSPDisplayList calls
            non_null_entries = [(i, e) for i, e in enumerate(self.entries) if e.pointer != 0]
            temp_dlists = {}

            for idx, (entry_idx, entry) in enumerate(non_null_entries):
                temp_name = f'temp_{idx}'
                dlist = self.parse_display_list(entry.pointer, temp_name)
                if dlist:
                    temp_dlists[entry.pointer] = dlist

            # Step 2: Find which display lists have gsSPDisplayList calls (in order of appearance)
            dlists_with_calls = []
            for idx, (entry_idx, entry) in enumerate(non_null_entries):
                if entry.pointer in temp_dlists:
                    dlist = temp_dlists[entry.pointer]
                    if dlist.dlist_calls:
                        dlists_with_calls.append(entry.pointer)

            # Step 3: Determine first and last based on display lists with gsSPDisplayList calls
            first_addr = dlists_with_calls[0] if dlists_with_calls else None
            last_addr = dlists_with_calls[-1] if dlists_with_calls else None

            # Step 4: Rename and add display lists with proper names
            # If there's a "first" entry, start from part1; otherwise start from part0
            part_counter = 1 if first_addr is not None else 0
            for idx, (entry_idx, entry) in enumerate(non_null_entries):
                if entry.pointer not in temp_dlists:
                    continue

                dlist = temp_dlists[entry.pointer]

                # Calculate position-based part number (what this entry would be called without first/last)
                position_part_num = idx

                # Determine proper name
                if entry.pointer == first_addr:
                    name = 'first'
                    # Don't increment part_counter for first
                elif entry.pointer == last_addr:
                    name = 'last'
                    # Still increment part_counter so subsequent parts use the next number
                    part_counter += 1
                else:
                    name = f'part{part_counter}_draw'
                    part_counter += 1

                # Update the display list name
                dlist.name = name
                self.dlists[entry.pointer] = dlist
                self.parse_lod_branches(dlist)

                # Parse gsSPDisplayList calls for first/last, passing position-based part number
                if name in ['first', 'last']:
                    self.parse_dlist_calls(dlist, name, position_part_num)

        print(f"Found {len(self.payloads)} payload structures")
        print(f"Found {len(self.dlists)} display lists")

        # Calculate vtx size from vertex addresses
        all_vtx_addrs = set()
        for dlist in self.dlists.values():
            all_vtx_addrs.update(dlist.vertex_addresses)

        if all_vtx_addrs:
            self.vtx_vram_start = min(all_vtx_addrs)
            max_vtx_addr = max(all_vtx_addrs)
            # Add one more vertex (0x10 bytes) for safety
            self.vtx_size = (max_vtx_addr - self.vtx_vram_start) + 0x10
            vtx_count = self.vtx_size // 0x10
            print(f"Calculated vertex array: {vtx_count} vertices (0x{self.vtx_size:X} bytes)")
            print(f"  Vtx range: 0x{self.vtx_vram_start:08X} - 0x{max_vtx_addr:08X}")
        else:
            self.vtx_size = 0x2350
            # Estimate vtx start
            if self.dlists:
                first_dlist_vram = min(d.vram_addr for d in self.dlists.values())
                self.vtx_vram_start = first_dlist_vram - 0x2800
            else:
                self.vtx_vram_start = self.vram_model_start - 0x3000
            print(f"No vertex addresses found, using default vtx size: 0x{self.vtx_size:X}")

    def generate_model_c_tail(self) -> str:
        output = ["\n\n"]

        # Include vertex data
        output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name("model")}.vtx.inc.c"')

        # Sort display lists by vram
        sorted_dlists = sorted(self.dlists.values(), key=lambda d: d.vram_addr)

        # Generate includes
        for dlist in sorted_dlists:
            # Skip LOD branch display lists (they're included by their parent)
            if dlist.name.endswith('_near') or dlist.name.endswith('_far'):
                continue

            # Check if LOD variants actually exist in self.dlists
            has_near = dlist.lod_near_addr and dlist.lod_near_addr in self.dlists
            has_far = dlist.lod_far_addr and dlist.lod_far_addr in self.dlists

            if dlist.has_lod and dlist.num_lod_branches >= 1:
                # Has LOD branching - check how many variants exist
                if dlist.num_lod_branches == 1 and has_near:
                    # Just near variant
                    output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name(dlist.name + "_near")}.gfx.inc.c"')
                    output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name(dlist.name)}.gfx.inc.c"')
                elif dlist.num_lod_branches == 2 and has_near and has_far:
                    # Both near and far variants
                    output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name(dlist.name + "_near")}.gfx.inc.c"')
                    output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name(dlist.name + "_far")}.gfx.inc.c"')
                    output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name(dlist.name)}.gfx.inc.c"')
                else:
                    # LOD detected but variants not parsed successfully - just base
                    output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name(dlist.name)}.gfx.inc.c"')
            else:
                # No LOD - just the base display list
                output.append(f'#include "assets/{self.segment_dir}/{self.name}/{self.get_file_name(dlist.name)}.gfx.inc.c"')

        # Generate gfxdata array if we have payloads
        if self.payloads:
            # Determine the payload type from the first non-first/last payload
            payload_type = 'I'
            for payload in self.payloads:
                if not payload.is_first and not payload.is_last:
                    payload_type = payload.type
                    break

            type_name = f'DObjPayloadType{payload_type}'
            output.append(f'\n{type_name} {self.get_symbol_name("gfxdata")}[] = {{')

            for i, payload in enumerate(self.payloads):
                # Handle first/last entries
                if (payload.is_first or payload.is_last) and payload.ptr1 == 0:
                    # Only use simplified output if ptr1 is NULL
                    dlist_name = 'first' if payload.is_first else 'last'
                    if payload_type == 'I':
                        output.append(f'    {{ NULL, {self.get_symbol_name(dlist_name)} }},')
                    elif payload_type == 'C':
                        output.append(f'    {{ 0, {self.get_symbol_name(dlist_name)} }},')
                    elif payload_type == 'J':
                        output.append(f'    {{ 0, NULL, {self.get_symbol_name(dlist_name)} }},')
                elif payload.type == 'I':
                    # TypeI: { pre, draw } - use actual dlist names directly
                    pre = 'NULL'
                    draw = 'NULL'
                    if payload.ptr1 != 0 and payload.ptr1 in self.dlists:
                        pre = self.get_symbol_name(self.dlists[payload.ptr1].name)
                    if payload.ptr2 != 0 and payload.ptr2 in self.dlists:
                        draw = self.get_symbol_name(self.dlists[payload.ptr2].name)
                    output.append(f'    {{ {pre}, {draw} }},')
                elif payload.type == 'C':
                    # TypeC: { dlistID, dlist }
                    if payload.ptr2 == 0:
                        # NULL pointer
                        output.append(f'    {{ {payload.ptr1}, NULL }},')
                    elif payload.ptr2 in self.dlists:
                        dlist_name = self.get_symbol_name(self.dlists[payload.ptr2].name)
                        output.append(f'    {{ {payload.ptr1}, {dlist_name} }},')
                    else:
                        output.append(f'    {{ {payload.ptr1}, NULL  /* TODO: 0x{payload.ptr2:08X} */ }},')
                elif payload.type == 'J':
                    # TypeJ: { dlistID, dlist1, dlist2 }
                    dlist1 = self.get_symbol_name(self.dlists[payload.ptr2].name) if payload.ptr2 in self.dlists else 'NULL'
                    dlist2 = self.get_symbol_name(self.dlists[payload.ptr3].name) if payload.ptr3 and payload.ptr3 in self.dlists else 'NULL'
                    output.append(f'    {{ {payload.ptr1}, {dlist1}, {dlist2} }},')
            output.append('};')

        # Generate model array
        output.append(f'\nUnkEC64Arg3 {self.get_symbol_name("model")}[] = {{')

        # Calculate array start and struct size for index calculation
        array_start_vram = 0
        struct_size = 0x08
        if self.payloads:
            array_start_vram = min(p.vram_addr for p in self.payloads)
            # Determine struct size from payload type
            first_payload_type = next((p.type for p in self.payloads if not p.is_first and not p.is_last), 'I')
            struct_size = 0x0C if first_payload_type == 'J' else 0x08

        for i, entry in enumerate(self.entries):
            if entry.pointer == 0:
                gfx_ref = 'NULL'
            else:
                if self.payloads:
                    # Has intermediate structures - calculate array index from pointer offset
                    gfx_idx = (entry.pointer - array_start_vram) // struct_size
                    gfx_ref = f'&{self.get_symbol_name("gfxdata")}[{gfx_idx}]'
                else:
                    # Direct pointers - reference display list directly
                    if entry.pointer in self.dlists:
                        dlist_name = self.dlists[entry.pointer].name
                        gfx_ref = self.get_symbol_name(dlist_name)
                    else:
                        gfx_ref = 'NULL  // TODO: unknown pointer'

            output.append(f'    {{ {entry.index},')
            output.append(f'      {gfx_ref},')
            output.append(f'      {{ {entry.pos[0]}, {entry.pos[1]}, {entry.pos[2]} }},')
            output.append(f'      {{ {entry.rot[0]}, {entry.rot[1]}, {entry.rot[2]} }},')
            output.append(f'      {{ {entry.scale[0]}, {entry.scale[1]}, {entry.scale[2]} }} }},')

        output.append('};')
        output.append("")

        return '\n'.join(output)

    def generate_splat_config(self) -> str:
        output = []

        # Calculate vtx ROM start
        vtx_rom_start = self.vram_to_rom(self.vtx_vram_start)

        output.append(f'    - start: 0x{vtx_rom_start:X}')
        output.append(f'      type: .data')
        output.append(f'      dir: {self.name}')
        output.append(f'      name: {self.name}/model')
        output.append(f'      linker_section_order: .rodata')
        output.append(f'      subsegments:')

        # Collect all entries with their ROM addresses
        entries = []
        entries.append((vtx_rom_start, f'      - [0x{vtx_rom_start:X}, vtx, {self.get_file_name("model")}]'))

        # Add display lists
        for dlist in self.dlists.values():
            # Skip LOD branch display lists (they're added by their parent)
            if dlist.name.endswith('_near') or dlist.name.endswith('_far'):
                continue

            # Check if LOD variants actually exist in self.dlists
            has_near = dlist.lod_near_addr and dlist.lod_near_addr in self.dlists
            has_far = dlist.lod_far_addr and dlist.lod_far_addr in self.dlists

            if dlist.has_lod and dlist.num_lod_branches >= 1:
                # Has LOD - check how many variants exist
                if dlist.num_lod_branches == 1 and has_near:
                    # Just near variant
                    lod_near_rom = self.vram_to_rom(dlist.lod_near_addr)
                    entries.append((lod_near_rom, f'      - [0x{lod_near_rom:X}, gfx, {self.get_file_name(dlist.name + "_near")}]'))
                    entries.append((dlist.rom_addr, f'      - [0x{dlist.rom_addr:X}, gfx, {self.get_file_name(dlist.name)}]'))
                elif dlist.num_lod_branches == 2 and has_near and has_far:
                    # Both near and far variants
                    lod_near_rom = self.vram_to_rom(dlist.lod_near_addr)
                    lod_far_rom = self.vram_to_rom(dlist.lod_far_addr)
                    entries.append((lod_near_rom, f'      - [0x{lod_near_rom:X}, gfx, {self.get_file_name(dlist.name + "_near")}]'))
                    entries.append((lod_far_rom, f'      - [0x{lod_far_rom:X}, gfx, {self.get_file_name(dlist.name + "_far")}]'))
                    entries.append((dlist.rom_addr, f'      - [0x{dlist.rom_addr:X}, gfx, {self.get_file_name(dlist.name)}]'))
                else:
                    # LOD detected but variants not parsed - just base
                    entries.append((dlist.rom_addr, f'      - [0x{dlist.rom_addr:X}, gfx, {self.get_file_name(dlist.name)}]'))
            else:
                # No LOD - just base
                entries.append((dlist.rom_addr, f'      - [0x{dlist.rom_addr:X}, gfx, {self.get_file_name(dlist.name)}]'))

        # Sort by ROM address
        entries.sort(key=lambda x: x[0])

        # Add sorted entries to output
        for _, entry_str in entries:
            output.append(entry_str)

        return '\n'.join(output)

    def generate_symbols(self) -> str:
        output = ["\n"]

        # Use calculated vtx info
        output.append(f'{self.get_symbol_name("vtx")} = 0x{self.vtx_vram_start:08X}; // segment:{self.segment_name} size:0x{self.vtx_size:X}')

        # Collect all symbol entries
        symbol_entries = []

        # Display lists
        for dlist in self.dlists.values():
            # Skip LOD branch display lists (they're added by their parent)
            if dlist.name.endswith('_near') or dlist.name.endswith('_far'):
                continue

            # Check if LOD variants actually exist in self.dlists
            has_near = dlist.lod_near_addr and dlist.lod_near_addr in self.dlists
            has_far = dlist.lod_far_addr and dlist.lod_far_addr in self.dlists

            if dlist.has_lod and dlist.num_lod_branches >= 1:
                # Has LOD - check how many variants exist
                if dlist.num_lod_branches == 1 and has_near:
                    # Just near variant
                    symbol_entries.append((dlist.lod_near_addr, f'{self.get_symbol_name(dlist.name + "_near")} = 0x{dlist.lod_near_addr:08X}; // segment:{self.segment_name}'))
                    symbol_entries.append((dlist.vram_addr, f'{self.get_symbol_name(dlist.name)} = 0x{dlist.vram_addr:08X}; // segment:{self.segment_name}'))
                elif dlist.num_lod_branches == 2 and has_near and has_far:
                    # Both near and far variants
                    symbol_entries.append((dlist.lod_near_addr, f'{self.get_symbol_name(dlist.name + "_near")} = 0x{dlist.lod_near_addr:08X}; // segment:{self.segment_name}'))
                    symbol_entries.append((dlist.lod_far_addr, f'{self.get_symbol_name(dlist.name + "_far")} = 0x{dlist.lod_far_addr:08X}; // segment:{self.segment_name}'))
                    symbol_entries.append((dlist.vram_addr, f'{self.get_symbol_name(dlist.name)} = 0x{dlist.vram_addr:08X}; // segment:{self.segment_name}'))
                else:
                    # LOD detected but variants not parsed - just base
                    symbol_entries.append((dlist.vram_addr, f'{self.get_symbol_name(dlist.name)} = 0x{dlist.vram_addr:08X}; // segment:{self.segment_name}'))
            else:
                # No LOD
                symbol_entries.append((dlist.vram_addr, f'{self.get_symbol_name(dlist.name)} = 0x{dlist.vram_addr:08X}; // segment:{self.segment_name}'))

        # Sort by VRAM address
        symbol_entries.sort(key=lambda x: x[0])

        # Add sorted entries
        for _, symbol_str in symbol_entries:
            output.append(symbol_str)

        # GfxData and model
        if self.payloads:
            gfxdata_vram = min(p.vram_addr for p in self.payloads)
            output.append(f'{self.get_symbol_name("gfxdata")} = 0x{gfxdata_vram:08X}; // segment:{self.segment_name}')

        output.append(f'{self.get_symbol_name("model")} = 0x{self.vram_model_start:08X}; // segment:{self.segment_name} size:0x{len(self.entries) * ENTRY_SIZE:X}')

        return '\n'.join(output)

def main():
    parser = argparse.ArgumentParser(
        description='Extract model data from Pokemon Snap ROM and generate model.c, splat config, and symbols.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run extract_model.py pokemonsnap.z64 volcano 0x8032A688 0x77B888 moltres
  uv run extract_model.py pokemonsnap.z64 volcano 0x8032A688 0x77B888 moltres i
  uv run extract_model.py --variant hd pokemonsnap.z64 rainbow 0x8013DC80 0x4F0030 mew i
  uv run extract_model.py --segment rainbow_assets pokemonsnap.z64 rainbow 0x8013DC80 0x4F0030 mew i

Type options:
  (none)  - analyze and show raw data for inspection
  direct  - no intermediate gfxdata array
  i       - DObjPayloadTypeI (two pointers)
  c       - DObjPayloadTypeC (dlistID + pointer)
  j       - DObjPayloadTypeJ (dlistID + two pointers)
"""
    )

    parser.add_argument('--variant', type=str, help='Model variant (e.g., hd) - affects file and symbol naming')
    parser.add_argument('--segment', type=str, help='Override segment name (e.g., rainbow_code) instead of auto "{folder}_code"')
    parser.add_argument('rom_file', help='Path to ROM file (e.g., pokemonsnap.z64)')
    parser.add_argument('folder', help='Folder name (e.g., volcano, beach, mon, rainbow)')
    parser.add_argument('vram_addr', help='VRAM address of UnkEC64Arg3 array (hex)')
    parser.add_argument('rom_addr', help='ROM address of UnkEC64Arg3 array (hex)')
    parser.add_argument('name', help='Model name (e.g., moltres, mew)')
    parser.add_argument('type', nargs='?', choices=['direct', 'i', 'c', 'j'],
                       help='Payload type (omit for inspection mode)')

    args = parser.parse_args()

    vram_addr = int(args.vram_addr, 16)
    rom_addr = int(args.rom_addr, 16)
    payload_type = args.type.lower() if args.type else None

    extractor = ModelExtractor(args.rom_file, args.folder, vram_addr, rom_addr, args.name, args.variant, args.segment)
    extractor.extract_all(payload_type)

    # Only generate output if a type was specified
    if payload_type is not None:
        print("\n" + "="*80)
        print("MODEL.C TAIL:")
        print("="*80)
        print(extractor.generate_model_c_tail())

        print("\n" + "="*80)
        print("SPLAT CONFIG:")
        print("="*80)
        print(extractor.generate_splat_config())

        print("\n" + "="*80)
        print("SYMBOL DEFINITIONS:")
        print("="*80)
        print(extractor.generate_symbols())

if __name__ == '__main__':
    main()
