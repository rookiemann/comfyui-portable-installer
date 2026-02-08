@echo off
setlocal enabledelayedexpansion

:: ComfyUI Module Launcher
:: Usage: launcher.bat [command] [options]

set "SCRIPT_DIR=%~dp0"

:: Determine Python executable (embedded first, then legacy venv)
set "PYTHON_EXE=%SCRIPT_DIR%python_embedded\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"
)

:: Add portable Git to PATH if available
if exist "%SCRIPT_DIR%git_portable\cmd\git.exe" (
    set "PATH=%SCRIPT_DIR%git_portable\cmd;%PATH%"
)

:: Add portable FFmpeg to PATH if available
if exist "%SCRIPT_DIR%ffmpeg_portable\bin\ffmpeg.exe" (
    set "PATH=%SCRIPT_DIR%ffmpeg_portable\bin;%PATH%"
)

echo.
echo ========================================
echo   ComfyUI Module Launcher
echo ========================================
echo.

:: Check for python
if not exist "%PYTHON_EXE%" (
    echo ERROR: Python not found.
    echo.
    echo   Run install.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

:: Parse command
set "COMMAND=%~1"
if "%COMMAND%"=="" set "COMMAND=install"

if /i "%COMMAND%"=="help" goto :show_help
if /i "%COMMAND%"=="setup" goto :run_setup
if /i "%COMMAND%"=="install" goto :run_install
if /i "%COMMAND%"=="run" goto :run_server
if /i "%COMMAND%"=="gui" goto :run_install
if /i "%COMMAND%"=="start" goto :run_server
if /i "%COMMAND%"=="api" goto :run_api
if /i "%COMMAND%"=="purge" goto :run_purge

echo Unknown command: %COMMAND%
goto :show_help

:show_help
echo.
echo Usage: launcher.bat [command] [options]
echo.
echo Commands:
echo   install, gui    Launch the installer GUI (default)
echo   run, start      Start ComfyUI server directly
echo   api             Start the REST API server
echo   setup           Run install.bat for full environment setup
echo   purge           Purge ComfyUI (keeps models and Python)
echo   help            Show this help
echo.
echo Server options (for 'run' command):
echo   --port PORT     Server port (default: 8188)
echo   --host HOST     Server host (default: 127.0.0.1)
echo   --vram MODE     VRAM mode: normal, low, none, cpu
echo   --gpu DEVICE    GPU index (0, 1, ...) or 'cpu' (default: all GPUs)
echo.
echo API options (for 'api' command):
echo   --api-port PORT  API port (default: 5000)
echo   --api-host HOST  API host (default: 127.0.0.1)
echo.
echo Examples:
echo   launcher.bat                     Launch GUI
echo   launcher.bat run                 Start server with defaults
echo   launcher.bat run --port 8189     Start server on port 8189
echo   launcher.bat run --gpu 0         Pin to GPU 0
echo   launcher.bat run --gpu cpu       CPU-only mode
echo   launcher.bat api                 Start REST API on port 5000
echo   launcher.bat api --api-port 8080 Start REST API on port 8080
echo.
pause
exit /b 0

:run_setup
echo Running full environment setup...
call "%SCRIPT_DIR%install.bat"
pause
exit /b 0

:run_install
echo Launching ComfyUI Module Installer GUI...
echo.
echo Python: %PYTHON_EXE%
echo Script: %SCRIPT_DIR%installer_app.py
echo.

"%PYTHON_EXE%" "%SCRIPT_DIR%installer_app.py"

if errorlevel 1 (
    echo.
    echo ERROR: The installer exited with an error.
    echo.
    pause
)
exit /b 0

:run_server
echo Starting ComfyUI server...

:: Collect remaining arguments
set "ARGS="
:collect_args
shift
if "%~1"=="" goto :start_server
set "ARGS=%ARGS% %~1"
goto :collect_args

:start_server
"%PYTHON_EXE%" "%SCRIPT_DIR%installer_app.py" --start %ARGS%
if errorlevel 1 (
    echo.
    echo ERROR: Server exited with an error.
    echo.
    pause
)
exit /b 0

:run_api
echo Starting ComfyUI Module REST API...

:: Collect remaining arguments
set "API_ARGS="
:collect_api_args
shift
if "%~1"=="" goto :start_api
set "API_ARGS=%API_ARGS% %~1"
goto :collect_api_args

:start_api
"%PYTHON_EXE%" "%SCRIPT_DIR%installer_app.py" --api %API_ARGS%
if errorlevel 1 (
    echo.
    echo ERROR: API server exited with an error.
    echo.
    pause
)
exit /b 0

:run_purge
echo Purging ComfyUI installation...
"%PYTHON_EXE%" "%SCRIPT_DIR%installer_app.py" --purge
pause
exit /b 0
