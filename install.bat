@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================
echo   ComfyUI Module - Autonomous Installer
echo ============================================
echo.
echo   This script sets up everything from scratch:
echo   - Embedded Python 3.12 (no system Python needed)
echo   - Portable Git (no system Git needed)
echo   - Portable FFmpeg (no system FFmpeg needed)
echo   - All Python dependencies
echo   - Then launches the ComfyUI installer
echo.

set "SCRIPT_DIR=%~dp0"
set "PYTHON_DIR=%SCRIPT_DIR%python_embedded"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "GIT_DIR=%SCRIPT_DIR%git_portable"
set "GIT_EXE=%GIT_DIR%\cmd\git.exe"
set "FFMPEG_DIR=%SCRIPT_DIR%ffmpeg_portable"
set "FFMPEG_EXE=%FFMPEG_DIR%\bin\ffmpeg.exe"

set "PYTHON_VERSION=3.12.8"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_ZIP=%SCRIPT_DIR%python_embedded.zip"

set "GIT_VERSION=2.47.1"
set "GIT_URL=https://github.com/git-for-windows/git/releases/download/v%GIT_VERSION%.windows.1/MinGit-%GIT_VERSION%-64-bit.zip"
set "GIT_ZIP=%SCRIPT_DIR%git_portable.zip"

set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "FFMPEG_ZIP=%SCRIPT_DIR%ffmpeg_portable.zip"

:: ============================================
:: Step 1: Download Embedded Python
:: ============================================
if exist "%PYTHON_EXE%" (
    echo [OK] Embedded Python already installed.
    goto :check_pip
)

echo [1/8] Downloading Python %PYTHON_VERSION% embedded...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     $ProgressPreference = 'SilentlyContinue'; ^
     Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_ZIP%'"

if not exist "%PYTHON_ZIP%" (
    echo.
    echo ERROR: Failed to download Python.
    echo   - Check your internet connection
    echo   - URL: %PYTHON_URL%
    echo.
    pause
    exit /b 1
)

echo [2/8] Extracting Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python extraction failed.
    pause
    exit /b 1
)

del "%PYTHON_ZIP%" 2>nul

:: ============================================
:: Step 2: Configure ._pth for site-packages
:: ============================================
echo [3/8] Configuring Python for package installation...

:: Create Lib\site-packages directory
if not exist "%PYTHON_DIR%\Lib\site-packages" (
    mkdir "%PYTHON_DIR%\Lib\site-packages"
)

:: Rewrite the ._pth file to enable import site and site-packages
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$pthFiles = Get-ChildItem '%PYTHON_DIR%\python*._pth'; ^
     if ($pthFiles.Count -gt 0) { ^
         $pth = $pthFiles[0]; ^
         $zipName = (Get-ChildItem '%PYTHON_DIR%\python*.zip' | Select-Object -First 1).Name; ^
         if (-not $zipName) { $zipName = 'python312.zip' }; ^
         $content = @($zipName, '.', 'Lib', 'Lib\site-packages', 'DLLs', '..\comfyui', '', 'import site'); ^
         $content | Set-Content -Path $pth.FullName -Encoding ASCII; ^
         Write-Host '   Configured:' $pth.Name ^
     } else { ^
         Write-Host 'WARNING: No ._pth file found' ^
     }"

:: ============================================
:: Step 3: Bootstrap pip (via get-pip.py)
:: ============================================
:check_pip
"%PYTHON_EXE%" -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [3/8] Downloading get-pip.py...
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
         $ProgressPreference = 'SilentlyContinue'; ^
         Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'"

    if not exist "%PYTHON_DIR%\get-pip.py" (
        echo ERROR: Failed to download get-pip.py.
        pause
        exit /b 1
    )

    echo [3/8] Installing pip...
    "%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py"
    if errorlevel 1 (
        echo ERROR: Failed to install pip.
        pause
        exit /b 1
    )

    del "%PYTHON_DIR%\get-pip.py" 2>nul
    "%PYTHON_EXE%" -m pip install --upgrade pip 2>nul
) else (
    echo [OK] pip already available.
)

:: ============================================
:: Step 4: Set up tkinter (needed for GUI)
:: ============================================
"%PYTHON_EXE%" -c "import _tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [4/8] Setting up tkinter for GUI...
    "%PYTHON_EXE%" -c "import sys; sys.path.insert(0, r'%SCRIPT_DIR%'); from core.python_manager import PythonManager; pm = PythonManager(); pm.setup_tkinter()"
    if errorlevel 1 (
        echo WARNING: Failed to set up tkinter. GUI may not work.
        echo   The CLI interface will still work: launcher.bat run
    )
) else (
    echo [OK] tkinter already available.
)

:: ============================================
:: Step 5: Download Portable Git
:: ============================================
if exist "%GIT_EXE%" (
    echo [OK] Portable Git already installed.
    goto :check_ffmpeg
)

echo [5/8] Downloading portable Git %GIT_VERSION%...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     $ProgressPreference = 'SilentlyContinue'; ^
     Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%GIT_ZIP%'"

if not exist "%GIT_ZIP%" (
    echo WARNING: Failed to download Git. Some features may not work.
    echo   Git clone operations require Git to be available.
    echo   - Check your internet connection
    echo   - URL: %GIT_URL%
    echo.
    goto :check_ffmpeg
)

echo [5/8] Extracting portable Git...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%GIT_ZIP%' -DestinationPath '%GIT_DIR%' -Force"

del "%GIT_ZIP%" 2>nul

:: ============================================
:: Step 6: Download Portable FFmpeg
:: ============================================
:check_ffmpeg
if exist "%FFMPEG_EXE%" (
    echo [OK] Portable FFmpeg already installed.
    goto :setup_path
)

echo [6/8] Downloading portable FFmpeg...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; ^
     $ProgressPreference = 'SilentlyContinue'; ^
     Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%FFMPEG_ZIP%'"

if not exist "%FFMPEG_ZIP%" (
    echo WARNING: Failed to download FFmpeg. Video features may not work.
    echo   Video export/import in custom nodes requires FFmpeg.
    echo   - Check your internet connection
    echo   - URL: %FFMPEG_URL%
    echo.
    goto :setup_path
)

echo [6/8] Extracting portable FFmpeg...
:: FFmpeg zip has a versioned top-level dir (e.g. ffmpeg-7.1-essentials_build/).
:: Extract to temp, then move bin/ to ffmpeg_portable/bin/.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$tempDir = '%SCRIPT_DIR%_ffmpeg_temp'; ^
     Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath $tempDir -Force; ^
     $inner = Get-ChildItem $tempDir -Directory | Select-Object -First 1; ^
     if ($inner -and (Test-Path \"$($inner.FullName)\bin\")) { ^
         New-Item -Path '%FFMPEG_DIR%\bin' -ItemType Directory -Force | Out-Null; ^
         Copy-Item \"$($inner.FullName)\bin\*\" '%FFMPEG_DIR%\bin\' -Force; ^
         Write-Host '   Extracted FFmpeg to ffmpeg_portable\bin\' ^
     } else { ^
         Write-Host 'WARNING: FFmpeg zip has unexpected structure' ^
     }; ^
     Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue"

del "%FFMPEG_ZIP%" 2>nul

:: ============================================
:: Step 6: Set up PATH and install requirements
:: ============================================
:setup_path
:: Add portable Git to PATH for this session
if exist "%GIT_EXE%" (
    set "PATH=%GIT_DIR%\cmd;%PATH%"
    echo [OK] Portable Git added to PATH.
)

:: Add portable FFmpeg to PATH for this session
if exist "%FFMPEG_EXE%" (
    set "PATH=%FFMPEG_DIR%\bin;%PATH%"
    echo [OK] Portable FFmpeg added to PATH.
)

echo [7/8] Installing installer requirements...
"%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt" --quiet 2>nul
if errorlevel 1 (
    echo Retrying with verbose output...
    "%PYTHON_EXE%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 (
        echo ERROR: Failed to install requirements.
        pause
        exit /b 1
    )
)

:: ============================================
:: Step 7: Launch the installer
:: ============================================
echo [8/8] Launching ComfyUI installer...
echo.
echo ============================================
echo.

"%PYTHON_EXE%" "%SCRIPT_DIR%installer_app.py" %*

if errorlevel 1 (
    echo.
    echo The installer exited with an error.
    echo.
    pause
)

endlocal
