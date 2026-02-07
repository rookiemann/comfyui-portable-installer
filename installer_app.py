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

    args = parser.parse_args()

    # Handle command-line operations
    if args.install:
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

        installer = ComfyInstaller()
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
        installer = ComfyInstaller()
        if not installer.is_installed:
            print("Error: ComfyUI is not installed. Run with --install first.")
            return 1

        server = ServerManager()

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

        server = ServerManager()
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

        installer = ComfyInstaller()

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


if __name__ == "__main__":
    sys.exit(main())
