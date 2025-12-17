import os
import sys
import sysconfig

# === Configuration ===
env = Environment()

# Detect OS
is_windows = (os.name == 'nt')
is_linux = (os.name == 'posix')

# === Python & Pybind11 Setup ===
# We need to find Python include paths and libraries
try:
    import pybind11
    pybind11_include = pybind11.get_include()
except ImportError:
    print("Error: pybind11 not installed. Run 'pip install pybind11'")
    Exit(1)

python_include = sysconfig.get_path('include')
python_platinclude = sysconfig.get_path('platinclude')
python_libs_dir = sysconfig.get_config_var('LIBDIR')

# Compiler Flags
if is_windows:
    env.Append(CPPDEFINES=['WIN32', '_WINDOWS'])
    env.Append(CXXFLAGS=['/EHsc', '/O2', '/std:c++17', '/utf-8']) 
    # Link against pythonXY.lib
    py_ver = f"{sys.version_info.major}{sys.version_info.minor}"
    env.Append(LIBS=[f'python{py_ver}'])
    env.Append(LIBPATH=[os.path.join(sys.exec_prefix, 'libs')])
    
    # Extension suffix
    ext_suffix = ".pyd"
else:
    env.Append(CXXFLAGS=['-O3', '-std=c++17', '-fPIC'])
    # Python embedding/extension flags
    env.ParseConfig('python3-config --cflags --ldflags --embed')
    ext_suffix = ".so"

# Include Paths
env.Append(CPPPATH=[
    'src/core',
    python_include,
    python_platinclude,
    pybind11_include
])

# === Source Files ===
sources = [
    'src/core/bindings.cpp',
    'src/core/engine.cpp',
    'src/core/log_reader.cpp',
    'src/core/state_machine.cpp'
]

# === Build Target ===
# We build a shared library. 
# Note: The name MUST match the module definition in bindings.cpp: PYBIND11_MODULE(_logdog_core, ...)
target_name = '_logdog_core'

lib = env.SharedLibrary(
    target=os.path.join('src', target_name), 
    source=sources,
    SHLIBPREFIX='',         # No 'lib' prefix on Linux
    SHLIBSUFFIX=ext_suffix  # .pyd on Win, .so on Linux
)

# === Installation / Dist Prep ===
# Copy python scripts to a build/dist folder logic can be added here, 
# but usually PyInstaller handles the final packaging.
# For SCons, we just ensure the binary is next to main.py