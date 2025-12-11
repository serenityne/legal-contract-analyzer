#!/usr/bin/env python3
"""
Legal Document Analyzer - Startup Script
Runs both the FastAPI backend and React frontend
"""

import subprocess
import sys
import os
import time
import threading
from pathlib import Path

def install_python_deps():
    """Install Python dependencies"""
    print("🔧 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("✅ Python dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing Python dependencies: {e}")
        return False
    return True

def install_react_deps():
    """Install React dependencies"""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False
    
    print("🔧 Installing React dependencies...")
    try:
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
        print("✅ React dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing React dependencies: {e}")
        print("💡 Make sure Node.js and npm are installed")
        return False
    return True

def start_backend():
    """Start FastAPI backend server"""
    print("🚀 Starting FastAPI backend server on http://localhost:8000...")
    try:
        subprocess.run([sys.executable, "api_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Backend server error: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Backend server stopped")

def start_frontend():
    """Start React frontend server"""
    frontend_dir = Path("frontend")
    print("🚀 Starting React frontend server on http://localhost:3000...")
    try:
        subprocess.run(["npm", "start"], cwd=frontend_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend server error: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Frontend server stopped")

def main():
    """Main startup function"""
    print("⚖️ Legal Document Analyzer - Modern React Frontend")
    print("=" * 60)
    
    # Check if we need to install dependencies
    if len(sys.argv) > 1 and sys.argv[1] == "--install":
        print("📦 Installing dependencies...")
        
        if not install_python_deps():
            sys.exit(1)
        
        if not install_react_deps():
            sys.exit(1)
        
        print("\n✅ All dependencies installed successfully!")
        print("💡 Now run: python start_app.py")
        return
    
    print("🔍 Checking dependencies...")
    
    # Check if node_modules exists
    if not Path("frontend/node_modules").exists():
        print("❌ React dependencies not installed")
        print("💡 Run: python start_app.py --install")
        sys.exit(1)
    
    print("✅ Dependencies check passed")
    print("\n🚀 Starting servers...")
    
    # Start backend in a thread
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Wait a moment for backend to start
    time.sleep(3)
    
    # Start frontend (blocking)
    try:
        start_frontend()
    except KeyboardInterrupt:
        print("\n🛑 Application stopped")

if __name__ == "__main__":
    main()
