# mk/build.py
import os
import sys
import subprocess
import shutil

def build():
    # Locate the directory
    # mk_dir: .../logdog/mk
    mk_dir = os.path.dirname(os.path.abspath(__file__))
    # root_dir: .../logdog
    root_dir = os.path.dirname(mk_dir)
    
    dist_dir = os.path.join(root_dir, 'dist')
    build_dir = os.path.join(root_dir, 'build')
    
    # Clean up old build artifacts
    if os.path.exists(dist_dir):
        print(f"Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)
    if os.path.exists(build_dir):
        print(f"Cleaning {build_dir}...")
        shutil.rmtree(build_dir)

    print(f"Start building from Root: {root_dir}")

    # PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--workpath', build_dir,
        '--distpath', dist_dir,
        os.path.join(mk_dir, 'logdog.spec')
    ]

    print(f"Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, cwd=root_dir)
    
    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)
    
    print("Build success!")
    
if __name__ == '__main__':
    build()