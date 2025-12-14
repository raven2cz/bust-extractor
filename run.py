#!/usr/bin/env python3
"""
Bust Extractor Pro - Launcher
==============================

Simple launcher script that starts the backend server
and opens the browser automatically.

Usage:
    python run.py
    
Or make executable (Linux/Mac):
    chmod +x run.py
    ./run.py

Author: raven2cz
Version: 2.0
"""

import os
import sys
import time
import webbrowser
import threading
from pathlib import Path


def check_dependencies():
    """
    Check if required dependencies are installed.
    
    Returns:
        List of missing dependency names
    """
    missing = []
    
    deps = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn[standard]"),
        ("PIL", "Pillow"),
        ("numpy", "numpy"),
        ("scipy", "scipy"),
        ("cv2", "opencv-python"),
    ]
    
    for module, package in deps:
        try:
            __import__(module)
            print(f"   ✓ {package}")
        except ImportError:
            missing.append(package)
            print(f"   ✗ {package} (missing)")
    
    return missing


def check_optional_deps():
    """Check optional AI model dependencies."""
    try:
        import rembg
        print("   ✓ rembg (AI background removal)")
        return True
    except ImportError:
        print("   ⚠ rembg (optional) - AI methods unavailable")
        print("     Install: pip install rembg onnxruntime-gpu")
        return False


def main():
    """Main entry point."""
    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    print("=" * 60)
    print("🎨 Bust Extractor Pro v2.0")
    print("=" * 60)
    print()
    
    # Check dependencies
    print("📦 Checking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print()
        print("❌ Missing required dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print()
        print("Install with:")
        print(f"   pip install {' '.join(missing)}")
        print()
        print("Or install all:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # Check optional dependencies
    check_optional_deps()
    print()
    
    # Create directories
    uploads_dir = script_dir / "uploads"
    outputs_dir = script_dir / "outputs"
    uploads_dir.mkdir(exist_ok=True)
    outputs_dir.mkdir(exist_ok=True)
    
    # Verify frontend exists
    frontend_dir = script_dir / "frontend"
    backend_dir = script_dir / "backend"
    
    print(f"📁 Project root: {script_dir}")
    print(f"📁 Frontend: {frontend_dir}")
    print(f"📁 Backend: {backend_dir}")
    print()
    
    if not frontend_dir.exists():
        print(f"❌ Frontend directory not found: {frontend_dir}")
        sys.exit(1)
    
    if not (frontend_dir / "index.html").exists():
        print(f"❌ index.html not found in frontend directory")
        sys.exit(1)
    
    if not backend_dir.exists():
        print(f"❌ Backend directory not found: {backend_dir}")
        sys.exit(1)
    
    # Add backend to path
    sys.path.insert(0, str(backend_dir))
    
    # Import and run server
    print("🚀 Starting server...")
    print()
    print("   📍 URL: http://localhost:8000")
    print("   ⌨️  Press Ctrl+C to stop")
    print()
    print("-" * 60)
    
    # Open browser after delay
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8000")
    
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Run server
    try:
        from server import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except KeyboardInterrupt:
        print()
        print("Server stopped.")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
