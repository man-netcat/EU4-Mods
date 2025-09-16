#!/usr/bin/env python3
import os
import sys

if len(sys.argv) != 2:
    print("Usage: python3 new_mod.py <mod_name>")
    sys.exit(1)

mod_name = sys.argv[1]
base_folder = os.path.dirname(os.path.abspath(__file__))
mod_folder = os.path.join(base_folder, mod_name)
mod_file_path = os.path.join(base_folder, f"{mod_name}.mod")
descriptor_path = os.path.join(mod_folder, "descriptor.mod")

content = f"""version="1"
tags={{
}}
name="{mod_name}"
supported_version="v1.37.5.0"
"""

# Create the mod folder
os.makedirs(mod_folder, exist_ok=True)

# Write .mod file (adds path line)
with open(mod_file_path, "w") as f:
    f.write(content)
    f.write(f'path="{mod_folder}"\n')

# Write descriptor.mod inside the folder
with open(descriptor_path, "w") as f:
    f.write(content)

print(f"Mod folder and files for '{mod_name}' have been created successfully.")
