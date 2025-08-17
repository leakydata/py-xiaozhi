"""PyInstaller hook file: hook-vosk.py.

Solves the problem of vosk not finding the model or dependent libraries when packaging.
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

from src.utils.resource_finder import find_models_dir

# Add the src directory to the Python path to import the resource finder
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print(f"Current working directory: {os.getcwd()}")

# Collect datas and binaries
datas = []
binaries = []

# Collect vosk metadata
try:
    datas.extend(copy_metadata("vosk"))
    print("✓ Successfully collected vosk metadata")
except Exception as e:
    print(f"Warning: Failed to collect vosk metadata: {e}")

# Collect vosk data files (including dynamic libraries)
try:
    vosk_data_files = collect_data_files("vosk")
    datas.extend(vosk_data_files)
    print(f"✓ Collected {len(vosk_data_files)} vosk data files")
except Exception as e:
    print(f"Warning: Failed to collect vosk data files: {e}")

# Collect vosk dynamic libraries
try:
    vosk_binaries = collect_dynamic_libs("vosk")
    binaries.extend(vosk_binaries)
    print(f"✓ Collected {len(vosk_binaries)} vosk dynamic libraries")
except Exception as e:
    print(f"Warning: Failed to collect vosk dynamic libraries: {e}")

# Manually find and add the libvosk.dyld file
try:
    import vosk
    vosk_dir = Path(vosk.__file__).parent
    libvosk_path = vosk_dir / "libvosk.dyld"

    if libvosk_path.exists():
        # Add to the list of binary files
        binaries.append((str(libvosk_path), "vosk"))
        print(f"✓ Manually added libvosk.dyld: {libvosk_path}")
    else:
        print("Warning: libvosk.dyld file not found")

    # Also check for other possible dynamic library files
    for lib_file in vosk_dir.glob("*.dylib"):
        binaries.append((str(lib_file), "vosk"))
        print(f"✓ Added dynamic library: {lib_file}")

except Exception as e:
    print(f"Warning: Failed to manually add vosk dynamic libraries: {e}")

# Use the unified resource finder to find the model directory
models_dir = find_models_dir()
if models_dir:
    print(f"Found model directory: {models_dir}")

    # Traverse all subdirectories under the model directory
    for item in models_dir.iterdir():
        if item.is_dir():
            print(f"Collecting model: {item}")
            # Collect all files in the entire model directory
            try:
                model_files = collect_data_files(str(item))
                datas.extend(model_files)
                print(f"Collected {len(model_files)} model files")
            except Exception as e:
                print(f"Warning: Failed to collect model files {item}: {e}")
else:
    print("Model directory not found")

print(f"Total collected {len(datas)} data files")
print(f"Total collected {len(binaries)} binary files")

# Show the first few files as an example
for i, data in enumerate(datas[:3]):
    print(f"  Data file {i+1}: {data}")

for i, binary in enumerate(binaries[:3]):
    print(f"  Binary file {i+1}: {binary}")

# Collect all vosk submodules
try:
    hiddenimports = collect_submodules("vosk")
    print(f"✓ Collected {len(hiddenimports)} vosk submodules")
except Exception as e:
    print(f"Warning: Failed to collect vosk submodules: {e}")
    hiddenimports = []

# Add other dependencies that may not be automatically discovered
additional_imports = [
    "vosk",  # Ensure the main module is included
    "cffi",  # cffi dependency for vosk
    "packaging.version",  # vosk version check
    "numpy",  # Audio processing
    "sounddevice",  # Recording function
    "_cffi_backend",  # cffi backend
]

# Merge all imports
hiddenimports.extend(additional_imports)
print(f"Total hidden imports: {len(hiddenimports)}")