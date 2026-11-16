"""
SRIVANI BOOKING MANAGER - Automated Windows Executable Builder
Cleans previous builds, runs PyInstaller, and verifies production artifact creation.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
SPEC_FILE = BASE_DIR / "srivani_manager.spec"

def clean_build():
    """Remove previous build outputs."""
    print("🧹 Cleaning previous build artifacts...")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR, ignore_errors=True)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    print("   Clean complete.")

def run_build():
    """Execute PyInstaller using the specification file."""
    print("🚀 Compiling Windows executable with PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]
    res = subprocess.run(cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"❌ PyInstaller compilation failed with exit code: {res.returncode}")
        return False
    return True

def verify_output():
    """Verify generated executable and dependencies."""
    exe_path = DIST_DIR / "SrivaniBookingManager" / "SrivaniBookingManager.exe"
    if not exe_path.exists():
        print(f"❌ Executable not found at expected location: {exe_path}")
        return False

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"✅ Executable built successfully: {exe_path}")
    print(f"   Executable file size: {size_mb:.2f} MB")
    print(f"   Distribution directory size: {sum(f.stat().st_size for f in exe_path.parent.glob('**/*') if f.is_file()) / (1024*1024):.2f} MB")
    return True

if __name__ == "__main__":
    clean_build()
    success = run_build()
    if success and verify_output():
        print("\n🎉 Windows Executable build completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Build process encountered errors.")
        sys.exit(1)
