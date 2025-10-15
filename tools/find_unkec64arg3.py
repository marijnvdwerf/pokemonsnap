#!/usr/bin/env python3
"""
Find potential UnkEC64Arg3 lists in binary files.

UnkEC64Arg3 structure (44 bytes):
- 4 bytes: integer (ascending: 0, 1, 2, 3, ...)
- 4 bytes: pointer (NULL or 0x80######)
- 12 bytes: vec3 (3 floats)
- 12 bytes: vec3 (3 floats)
- 12 bytes: vec3 (3 floats)
"""

import struct
import os
from pathlib import Path

ENTRY_SIZE = 44

def is_valid_pointer(ptr):
    """Check if pointer is NULL or starts with 0x80"""
    return ptr == 0 or (ptr >> 24) == 0x80

def find_unkec64arg3_lists(filepath):
    """Search for UnkEC64Arg3 patterns in a binary file"""
    results = []

    with open(filepath, 'rb') as f:
        data = f.read()

    # Search through the file at 4-byte aligned positions
    for offset in range(0, len(data) - ENTRY_SIZE, 4):
        # Try to find a list starting at this offset
        count = 0
        current_offset = offset

        while current_offset + ENTRY_SIZE <= len(data):
            # Read the entry
            entry_data = data[current_offset:current_offset + ENTRY_SIZE]

            # Parse integer and pointer (big-endian)
            index = struct.unpack('>I', entry_data[0:4])[0]
            pointer = struct.unpack('>I', entry_data[4:8])[0]

            # Check if this matches our pattern
            if index == count:
                # First entry should have NULL pointer, others can be NULL or 0x80######
                if count == 0 and pointer == 0:
                    count += 1
                    current_offset += ENTRY_SIZE
                elif count > 0 and is_valid_pointer(pointer):
                    count += 1
                    current_offset += ENTRY_SIZE

                    # Check if this might be the last entry (has NULL pointer)
                    if pointer == 0 and count >= 2:
                        # This looks like a complete list
                        if count >= 3:  # Only report lists with at least 3 entries
                            results.append((offset, count))
                        break
                else:
                    break
            else:
                break

        # Also accept lists that end without a NULL pointer entry
        # (might just continue into next data)
        if count >= 3 and (offset, count) not in results:
            # Verify we didn't just find noise by checking if the next would break pattern
            if current_offset + ENTRY_SIZE <= len(data):
                next_entry = data[current_offset:current_offset + ENTRY_SIZE]
                next_index = struct.unpack('>I', next_entry[0:4])[0]
                next_pointer = struct.unpack('>I', next_entry[4:8])[0]

                # If next entry doesn't continue the pattern, we found a list
                if next_index != count or not is_valid_pointer(next_pointer):
                    results.append((offset, count))

    # Remove overlapping results, keep the longest
    filtered_results = []
    for offset, count in results:
        # Check if this overlaps with any result we've already added
        overlaps = False
        for existing_offset, existing_count in filtered_results:
            if (offset >= existing_offset and offset < existing_offset + existing_count * ENTRY_SIZE):
                overlaps = True
                break
            if (existing_offset >= offset and existing_offset < offset + count * ENTRY_SIZE):
                # This new one overlaps an existing, keep the longer one
                if count > existing_count:
                    filtered_results.remove((existing_offset, existing_count))
                else:
                    overlaps = True
                break

        if not overlaps:
            filtered_results.append((offset, count))

    return filtered_results

def main():
    """Search all .bin files in assets directory"""
    # Get script directory and find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    assets_dir = project_root / 'assets'

    # Find all .bin files with hex names
    bin_files = []
    for root, dirs, files in os.walk(assets_dir):
        for filename in files:
            if filename.endswith('.bin'):
                # Check if it's a hex-named file (just check first char is hex digit or letter)
                if filename[0] in '0123456789ABCDEFabcdef':
                    bin_files.append(os.path.join(root, filename))

    bin_files.sort()

    print("Searching for UnkEC64Arg3 lists...")
    print("=" * 80)

    all_results = []

    for filepath in bin_files:
        results = find_unkec64arg3_lists(filepath)
        if results:
            rel_path = os.path.relpath(filepath, assets_dir)
            for offset, count in results:
                all_results.append((rel_path, offset, count))

    # Print results
    if all_results:
        print(f"\nFound {len(all_results)} potential UnkEC64Arg3 lists:\n")
        print(f"{'File':<50} {'Offset':<10} {'Count':<10}")
        print("-" * 80)
        for filename, offset, count in all_results:
            print(f"{filename:<50} 0x{offset:06X}    {count}")
    else:
        print("\nNo UnkEC64Arg3 lists found.")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()

