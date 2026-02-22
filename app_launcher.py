import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def main():
    os.chdir(get_resource_path('.'))
    
    print("🚀 Starting POPMAP...")
    print("⏳ Initializing Flask server...")
    
    # Start Flask in subprocess
    app_process = subprocess.Popen(
        [sys.executable, 'app.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=get_resource_path('.')
    )
    
    # Wait for server to start
    time.sleep(3)
    
    # Open browser
    print("🌐 Opening browser...")
    webbrowser.open('http://localhost:5000')
    
    print("✅ POPMAP is running!")
    print("📍 Access at: http://localhost:5000")
    print("🛑 Close this window to stop the server\n")
    
    try:
        app_process.wait()
    except KeyboardInterrupt:
        print("\n👋 Shutting down POPMAP...")
        app_process.terminate()
        app_process.wait()

if __name__ == '__main__':
    main()
