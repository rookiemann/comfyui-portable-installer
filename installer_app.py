#!/usr/bin/env python
"""
ComfyUI Module Installer - Main Application Entry Point

This script launches the Tkinter installer application.
It can also be imported to access the core modules directly.

Usage:
    python installer_app.py          # Launch GUI
    python installer_app.py --help   # Show help
"""
import sys
import argparse
from pathlib import Path

# Ensure the module directory is in path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ComfyUI Module Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python installer_app.py              # Launch installer GUI
    python installer_app.py --install    # Run full install (no GUI)
    python installer_app.py --start      # Start ComfyUI server
    python installer_app.py --stop       # Stop ComfyUI server
    python installer_app.py --api        # Start REST API server
    python installer_app.py --comfyui-dir "E:\\other\\ComfyUI" --start
                                         # Start an external ComfyUI
        """
    )

    parser.add_argument(
        "--install", action="store_true",
        help="Run full installation without GUI"
    )
    parser.add_argument(
        "--start", action="store_true",
        help="Start ComfyUI server"
    )
    parser.add_argument(
        "--stop", action="store_true",
        help="Stop ComfyUI server"
    )
    parser.add_argument(
        "--purge", action="store_true",
        help="Purge ComfyUI (keeps Python environment and models)"
    )
    parser.add_argument(
        "--purge-all", action="store_true",
        help="Purge everything including models and venv"
    )
    parser.add_argument(
        "--port", type=int, default=8188,
        help="Server port (default: 8188)"
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="Server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--vram", choices=["normal", "low", "none", "cpu"],
        default="normal",
        help="VRAM mode (default: normal)"
    )
    parser.add_argument(
        "--gpu", type=str, default=None,
        help="GPU device index (0, 1, ...) or 'cpu'. Default: use all GPUs"
    )
    parser.add_argument(
        "--api", action="store_true",
        help="Start the REST API server instead of GUI"
    )
    parser.add_argument(
        "--api-port", type=int, default=5000,
        help="API server port (default: 5000)"
    )
    parser.add_argument(
        "--api-host", type=str, default="127.0.0.1",
        help="API server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--comfyui-dir", type=str, default=None,
        help="Path to an external ComfyUI installation to manage"
    )

    args = parser.parse_args()

    # If an external ComfyUI directory was specified, persist it in settings
    if args.comfyui_dir:
        from config import save_settings
        ext = Path(args.comfyui_dir).resolve()
        if not (ext / "main.py").exists():
            print(f"Error: No main.py found in {ext}")
            print("Please specify a valid ComfyUI installation directory.")
            return 1
        save_settings({"comfyui_dir": str(ext)})

    # Handle command-line operations
    if args.api:
        return run_api(args.api_host, args.api_port)
    elif args.install:
        return run_install()
    elif args.start:
        return run_server(args.host, args.port, args.vram, args.gpu)
    elif args.stop:
        return stop_server()
    elif args.purge:
        return run_purge(purge_all=False)
    elif args.purge_all:
        return run_purge(purge_all=True)
    else:
        # Launch GUI
        return run_gui()


def run_gui():
    """Launch the Tkinter GUI application."""
    try:
        from ui.main_window import MainWindow
        app = MainWindow()
        app.run()
        return 0
    except ImportError as e:
        print(f"Error importing UI modules: {e}")
        print("Make sure all dependencies are installed.")
        return 1
    except Exception as e:
        print(f"Error launching GUI: {e}")
        return 1


def run_install():
    """Run full installation without GUI."""
    print("ComfyUI Module - Full Installation")
    print("=" * 40)

    try:
        from core.comfy_installer import ComfyInstaller

        def progress(current, total, message):
            bar_length = 30
            if total > 0:
                progress = current / total
                filled = int(bar_length * progress)
                bar = "=" * filled + "-" * (bar_length - filled)
                print(f"\r[{bar}] {int(progress * 100)}% {message}", end="", flush=True)
            else:
                print(f"\r{message}", end="", flush=True)

        from config import get_active_comfyui_dir
        active = get_active_comfyui_dir()
        installer = ComfyInstaller(comfyui_dir=active, models_dir=active / "models")
        success = installer.full_install(progress)

        print()  # New line after progress
        if success:
            print("\nInstallation completed successfully!")
            return 0
        else:
            print("\nInstallation failed!")
            return 1

    except Exception as e:
        print(f"\nError during installation: {e}")
        return 1


def run_server(host: str, port: int, vram_mode: str, gpu_device: str = None):
    """Start the ComfyUI server."""
    gpu_desc = f" on GPU {gpu_device}" if gpu_device and gpu_device != "cpu" else (" on CPU" if gpu_device == "cpu" else "")
    print(f"Starting ComfyUI server on {host}:{port}{gpu_desc}...")

    try:
        from core.server_manager import ServerManager
        from core.comfy_installer import ComfyInstaller

        # Check if installed
        from config import get_active_comfyui_dir
        active = get_active_comfyui_dir()
        installer = ComfyInstaller(comfyui_dir=active)
        if not installer.is_installed:
            print("Error: ComfyUI is not installed. Run with --install first.")
            return 1

        server = ServerManager(comfyui_dir=active)

        def log_callback(line):
            print(line)

        success = server.start_server(
            host=host,
            port=port,
            vram_mode=vram_mode,
            log_callback=log_callback,
            gpu_device=gpu_device,
        )

        if success:
            print(f"\nServer running at http://{host}:{port}")
            print("Press Ctrl+C to stop...")

            try:
                # Keep running until interrupted
                import time
                while server.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping server...")
                server.stop_server()

            return 0
        else:
            print("Failed to start server!")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def stop_server():
    """Stop the ComfyUI server."""
    print("Stopping ComfyUI server...")

    try:
        from core.server_manager import ServerManager
        from config import get_active_comfyui_dir

        server = ServerManager(comfyui_dir=get_active_comfyui_dir())
        if server.is_running:
            server.stop_server()
            print("Server stopped.")
        else:
            print("Server is not running.")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def run_purge(purge_all: bool = False):
    """Purge ComfyUI installation."""
    if purge_all:
        print("ComfyUI Module - FULL PURGE")
        print("WARNING: This will delete EVERYTHING including models!")
    else:
        print("ComfyUI Module - Purge ComfyUI")
        print("This will delete ComfyUI but KEEP Python environment and models.")

    print("=" * 40)

    # Confirm
    response = input("Are you sure? (yes/no): ").strip().lower()
    if response != "yes":
        print("Purge cancelled.")
        return 0

    try:
        from core.comfy_installer import ComfyInstaller

        def progress(current, total, message):
            print(f"  {message}")

        from config import get_active_comfyui_dir
        active = get_active_comfyui_dir()
        installer = ComfyInstaller(comfyui_dir=active, models_dir=active / "models")

        if purge_all:
            success = installer.purge_all(progress)
        else:
            success = installer.purge_comfyui(progress)

        if success:
            print("\nPurge completed successfully!")
            if purge_all:
                print("Run install.bat to reinstall everything.")
            else:
                print("Run with --install for fresh ComfyUI installation.")
            return 0
        else:
            print("\nPurge failed!")
            return 1

    except Exception as e:
        print(f"\nError during purge: {e}")
        return 1


def run_api(host: str = "127.0.0.1", port: int = 5000):
    """Start the REST API server."""
    print(f"Starting ComfyUI Module REST API on {host}:{port}...")

    try:
        from api.server import create_app, run_server
        app = create_app()
        run_server(app, host=host, port=port)
        return 0
    except ImportError as e:
        print(f"Error importing API modules: {e}")
        return 1
    except Exception as e:
        print(f"Error starting API server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
