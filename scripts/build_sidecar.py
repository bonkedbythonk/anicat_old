import os
import subprocess
import shutil
import platform

def get_target_triple():
    # Get the target triple for Tauri sidecar naming
    arch = platform.machine().lower()
    if arch == "amd64":
        arch = "x86_64"
    elif arch == "arm64":
        arch = "aarch64"
        
    system = platform.system().lower()
    if system == "darwin":
        return f"{arch}-apple-darwin"
    elif system == "windows":
        return f"{arch}-pc-windows-msvc"
    elif system == "linux":
        return f"{arch}-unknown-linux-gnu"
    else:
        return f"{arch}-unknown-{system}"

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    triple = get_target_triple()
    print(f"Target triple: {triple}")
    
    binaries_dir = os.path.join(project_root, "web", "src-tauri", "binaries")
    os.makedirs(binaries_dir, exist_ok=True)
    
    spec_file = os.path.join("build_sidecar", "sidecar.spec")
    
    print("Running PyInstaller...")
    # Use 'uv run' if available, otherwise assume pyinstaller is in path
    try:
        subprocess.run(["uv", "run", "pyinstaller", "--noconfirm", spec_file], check=True)
    except FileNotFoundError:
        subprocess.run(["pyinstaller", "--noconfirm", spec_file], check=True)
        
    # Source binary name
    src_name = "anicat-server"
    if platform.system() == "Windows":
        src_name += ".exe"
        
    src_path = os.path.join("dist", src_name)
    
    # Target binary name
    dest_name = f"anicat-server-{triple}"
    if platform.system() == "Windows":
        dest_name += ".exe"
        
    dest_path = os.path.join(binaries_dir, dest_name)
    
    print(f"Copying {src_path} to {dest_path}")
    shutil.copy2(src_path, dest_path)
    
    print("\nSuccess! Sidecar binary is ready for Tauri.")
    print(f"Binary: {dest_path}")

if __name__ == "__main__":
    main()
