# POPMAP - Standalone Executable Build Guide

## Quick Start (Recommended)

### Linux/Mac
```bash
chmod +x run_popmap.sh
./run_popmap.sh
```

### Windows
```batch
run_popmap.bat
```

The script will:
1. ✅ Create a virtual environment
2. ✅ Install dependencies
3. ✅ Launch the app
4. ✅ Open your browser automatically

---

## Standalone Binary (Advanced)

For a true standalone binary without Python dependency, use one of these options:

### Option 1: PyInstaller (Requires Python with shared library)
```bash
pip install pyinstaller
pyinstaller --onedir --windowed \
  --add-data templates:templates \
  --add-data static:static \
  --add-data data:data \
  --add-data lib:lib \
  --collect-all flask \
  --collect-all rasterio \
  app.py
```
Then run: `./dist/POPMAP/POPMAP` or `dist\POPMAP\POPMAP.exe`

### Option 2: Auto-py-to-exe (GUI PyInstaller)
```bash
pip install auto-py-to-exe
auto-py-to-exe
```

### Option 3: Create Installer with NSIS (Windows)
```bash
# Create NSIS installer script for professional distribution
```

---

## Distribution Package

To distribute POPMAP as a complete package:

1. **Linux/Mac Users:**
   - Provide: `run_popmap.sh`
   - Requirements: Python 3.8+

2. **Windows Users:**
   - Provide: `run_popmap.bat`
   - Requirements: Python 3.8+ (install from python.org)

3. **All Platforms:**
   - Include: `requirements.txt`, `app.py`, `lib/`, `templates/`, `static/`, `data/`

---

## For Maximum Portability

Use **Docker** (works everywhere):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]
```

Then run:
```bash
docker build -t popmap .
docker run -p 5000:5000 popmap
```

---

## Pre-built Executables

If you need one-click executables for distribution:

1. **Windows Portable (.exe)** - Use Option 1 above
2. **macOS App Bundle** - Requires Code Signing
3. **Linux AppImage** - Use `linuxdeploy`

Contact the dev environment maintainer for platform-specific builds.
