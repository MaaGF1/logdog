# mk/build.py
import os
import sys
import subprocess
import shutil

def run_command(cmd, cwd, env=None):
    """Helper to run shell commands"""
    print(f"Executing: {' '.join(cmd)} in {cwd}")
    # Merge current environment with passed env
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
        
    result = subprocess.run(cmd, cwd=cwd, env=run_env, shell=(os.name == 'nt'))
    if result.returncode != 0:
        print(f"Error: Command failed with return code {result.returncode}")
        sys.exit(1)

def build():
    # 1. Path Setup
    # mk_dir: .../logdog/mk
    mk_dir = os.path.dirname(os.path.abspath(__file__))
    # root_dir: .../logdog
    root_dir = os.path.dirname(mk_dir)
    
    dist_dir = os.path.join(root_dir, 'dist')
    build_dir = os.path.join(root_dir, 'build')
    
    # 2. Clean previous PyInstaller artifacts
    # (We don't clean SCons artifacts to speed up incremental builds, 
    # unless you want to run 'scons -c')
    if os.path.exists(dist_dir):
        print(f"Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)
    if os.path.exists(build_dir):
        print(f"Cleaning {build_dir}...")
        shutil.rmtree(build_dir)

    print(f"Start building from Root: {root_dir}")

    # 3. Build C++ Core with SCons
    print("=== Step 1: Building C++ Core with SCons ===")
    scons_cmd = [sys.executable, "-m", "SCons"]
    run_command(scons_cmd, cwd=root_dir)

    # 4. Package with PyInstaller
    print("=== Step 2: Packaging with PyInstaller ===")
    pyinstaller_cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--workpath', build_dir,
        '--distpath', dist_dir,
        '--noconfirm',
        os.path.join(mk_dir, 'logdog.spec')
    ]
    
    run_command(pyinstaller_cmd, cwd=root_dir)
    
    print("=== Build Success! ===")
    
if __name__ == '__main__':
    build()