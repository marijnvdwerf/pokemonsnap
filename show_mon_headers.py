#!/usr/bin/env python3
import os

for i in range(12, 0, -1):
    filepath = f"mon{i}.s"
    print(f"# {filepath}")

    if not os.path.exists(filepath):
        print("(File does not exist)\n")
        continue

    try:
        with open(filepath, 'r') as f:
            non_empty_lines = [line.rstrip() for line in f if line.strip()]
            for line in non_empty_lines[:6]:
                print(line)
        print()
    except Exception as e:
        print(f"Error reading file: {e}\n")
