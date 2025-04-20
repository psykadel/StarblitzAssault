@echo off

echo Building Starblitz Assault Installer for Windows
echo ===============================================

:: Create necessary directories
echo Setting up build environment...
if not exist .temp\pyinstaller mkdir .temp\pyinstaller

:: Get absolute path to project root
set PROJECT_ROOT=%cd%

:: Set environment variables for PyInstaller
set PYTHONOPTIMIZE=1
set PYTHONDONTWRITEBYTECODE=1

:: Clean previous build files if they exist
if exist .temp\pyinstaller (
    echo Cleaning temporary PyInstaller directory...
    rmdir /s /q .temp\pyinstaller
    mkdir .temp\pyinstaller
)
if exist dist\StarblitzAssault (
    echo Cleaning previous build...
    rmdir /s /q dist\StarblitzAssault
)

:: Run PyInstaller
echo Building installer with PyInstaller...
python -m PyInstaller ^
    --name=StarblitzAssault ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --workpath=.temp\pyinstaller ^
    --specpath=.temp\pyinstaller ^
    --distpath=dist ^
    --add-data="%PROJECT_ROOT%\assets;assets" ^
    --add-data="%PROJECT_ROOT%\config;config" ^
    --icon="%PROJECT_ROOT%\starblitz-icon.ico" ^
    main.py

:: Check if build was successful
if %ERRORLEVEL% neq 0 (
    echo Build failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

:: Check if build directory exists
if exist dist\StarblitzAssault (
    echo Build completed successfully.
) else (
    echo Build process did not generate expected directory.
    exit /b 1
)

echo.
echo Build complete!
echo The application can be found in the dist\StarblitzAssault directory.
echo. 