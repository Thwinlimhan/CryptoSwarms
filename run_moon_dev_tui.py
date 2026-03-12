#!/usr/bin/env python3
"""
Moon Dev Quant App TUI Launcher
Handles installation, setup, and launching of the TUI application
"""
import sys
import subprocess
import os
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True


def install_requirements():
    """Install required packages"""
    requirements_file = Path("requirements_tui.txt")
    
    if not requirements_file.exists():
        print("❌ requirements_tui.txt not found")
        return False
    
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False


def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        "textual",
        "rich", 
        "aiohttp",
        "psutil"
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            missing.append(module)
            print(f"❌ {module} - missing")
    
    return len(missing) == 0


def setup_environment():
    """Setup environment variables and configuration"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        print("📝 Creating .env file from template...")
        env_file.write_text(env_example.read_text())
        print("✅ .env file created")
    
    # Set default environment variables
    os.environ.setdefault("MOON_DEV_TUI_DEBUG", "false")
    os.environ.setdefault("HYPERLIQUID_API_TIMEOUT", "30")
    os.environ.setdefault("POLYMARKET_API_TIMEOUT", "30")
    os.environ.setdefault("REFRESH_INTERVAL", "30")


def launch_tui():
    """Launch the Moon Dev Quant TUI application"""
    print("🚀 Launching Moon Dev Quant TUI...")
    print("=" * 50)
    print("🌙 MOON DEV QUANT - Live Trading Terminal")
    print("=" * 50)
    print()
    print("Keyboard shortcuts:")
    print("  F1/1 - Trade tab")
    print("  F2/2 - Code tab") 
    print("  F3/3 - Backtest tab")
    print("  F4/4 - Data tab")
    print("  Shift+Tab - Bypass permissions")
    print("  R - Refresh data")
    print("  Q - Quit")
    print()
    print("Starting application...")
    print()
    
    try:
        from moon_dev_tui import MoonDevQuantApp
        app = MoonDevQuantApp()
        app.run()
    except ImportError as e:
        print(f"❌ Failed to import TUI application: {e}")
        return False
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
        return True
    except Exception as e:
        print(f"❌ Application error: {e}")
        return False
    
    return True


def main():
    """Main launcher function"""
    print("🌙 Moon Dev Quant TUI Launcher")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Check if we need to install requirements
    if not check_dependencies():
        print("\n📦 Installing missing dependencies...")
        if not install_requirements():
            print("❌ Failed to install dependencies")
            sys.exit(1)
        
        # Check again after installation
        print("\n🔍 Verifying installation...")
        if not check_dependencies():
            print("❌ Some dependencies are still missing")
            sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Launch the TUI
    print("\n🚀 All checks passed, launching TUI...")
    if not launch_tui():
        sys.exit(1)


if __name__ == "__main__":
    main()