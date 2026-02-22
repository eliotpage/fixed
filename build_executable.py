import os
import shutil
import subprocess
import sys
import platform

def build_executable():
    print("🔨 Building POPMAP standalone executable...")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Create a hidden imports list for all dependencies
    hidden_imports = [
        'flask',
        'flask_mail',
        'pyproj',
        'PIL',
        'scipy',
        'shapely',
        'rasterio',
        'dotenv',
        'werkzeug',
        'jinja2'
    ]
    
    # Build PyInstaller command
    cmd = [
        'pyinstaller',
        '--onedir',
        '--windowed',
        '--name=POPMAP',
        f'--add-data=templates:templates',
        f'--add-data=static:static',
        f'--add-data=data:data',
        f'--add-data=lib:lib',
    ]
    
    # Add hidden imports
    for imp in hidden_imports:
        cmd.append(f'--hidden-import={imp}')
    
    cmd.append('app.py')
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode == 0:
        print("✅ Executable built successfully!")
        exec_name = "POPMAP.exe" if platform.system() == "Windows" else "POPMAP"
        exec_path = os.path.join("dist", exec_name)
        print(f"📦 Executable location: {exec_path}")
        print(f"\n🚀 To run the app: {exec_path}")
    else:
        print("❌ Build failed!")
        sys.exit(1)

if __name__ == '__main__':
    build_executable()
