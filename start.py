#!/usr/bin/env python3
"""
Start script for Video-Shorter application.
Launches FastAPI backend and React frontend concurrently.
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

# Try to import whisper for pre-loading
try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False

def start_backend():
    """Start the FastAPI backend server."""
    print("Starting FastAPI backend on port 8000...")
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    
    cmd = [sys.executable, os.path.join(backend_dir, 'main.py')]
    return subprocess.Popen(cmd)

def start_frontend():
    """Start the React frontend dev server."""
    print("Starting React frontend dev server on port 3000...")
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    
    # Check if npm is available
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, timeout=5)
        if result.returncode != 0:
            raise RuntimeError("npm not found")
    except Exception as e:
        print(f"Error: npm not found. Please install Node.js from https://nodejs.org/")
        sys.exit(1)
    
    # Check if node_modules exists, if not run npm install
    node_modules = os.path.join(frontend_dir, 'node_modules')
    if not os.path.exists(node_modules):
        print("Installing npm dependencies...")
        result = subprocess.run(['npm', 'install'], cwd=frontend_dir, capture_output=False)
        if result.returncode != 0:
            print("Error installing npm dependencies")
            sys.exit(1)
    
    # Start npm start
    return subprocess.Popen(['npm', 'start'], cwd=frontend_dir)

if __name__ == "__main__":
    try:
        # Load environment variables if .env exists
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            print(f"Loading environment from {env_file}")
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key] = value
        else:
            print("⚠️  Warning: .env file not found.")
            print("Please create it with your DeepSeek API key using:")
            print("cp .env.example .env")
            print("Then edit .env and add your API key.\n")

        # Pre-download Whisper model before starting backend
        print("📥 Pre-loading Whisper model (base, ~139MB)...")
        print("This is only needed on first run.\n")
        try:
            if HAS_WHISPER:
                model = whisper.load_model("base")
                print("✓ Whisper model loaded successfully\n")
            else:
                print("⚠️  Whisper not available, will load during backend startup\n")
        except Exception as e:
            print(f"⚠️  Warning: Could not pre-load Whisper model: {e}")
            print("Will attempt to load when processing videos.\n")

        # Start backend
        backend_process = start_backend()
        time.sleep(3)  # Wait for backend to start
        
        # Start frontend
        frontend_process = start_frontend()
        time.sleep(5)  # Wait for frontend to start
        
        # Open browser
        print("\n" + "="*70)
        print("✅ Video-Shorter is running!")
        print("="*70)
        print("Frontend:        http://localhost:3000")
        print("Backend API:     http://localhost:8000")
        print("API Docs:        http://localhost:8000/docs")
        print("="*70)
        print("\nOpening browser...\n")
        
        webbrowser.open('http://localhost:3000')
        print("Press Ctrl+C to stop the services.\n")

        # Keep the process running
        while True:
            # Check if either process died
            if backend_process.poll() is not None:
                print("❌ Backend process stopped unexpectedly!")
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend process stopped unexpectedly!")
                break
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down services...")
        backend_process.terminate()
        frontend_process.terminate()
        try:
            backend_process.wait(timeout=5)
            frontend_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_process.kill()
            frontend_process.kill()
        print("Services stopped.")