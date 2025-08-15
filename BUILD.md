# Building ProxyCloud Application

This document provides instructions on how to build the ProxyCloud application from source code.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (to clone the repository)

### Windows Additional Requirements (for installer creation)

- NSIS (Nullsoft Scriptable Install System) - Optional, for creating Windows installer
  - Download from: https://nsis.sourceforge.io/Download

## Build Instructions

### Step 1: Install Required Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

### Step 2: Run the Build Script

#### On Windows:

Double-click the `build.bat` file or run it from the command line:

```bash
build.bat
```

#### On macOS/Linux:

Make the build script executable and run it:

```bash
chmod +x build.sh
./build.sh
```

### Step 3: Locate the Built Application

After a successful build, the application will be available in the `dist/ProxyCloud` directory.

## Creating an Installer (Windows Only)

If you have NSIS installed, the build script will offer to create a Windows installer. When prompted, type 'y' to create the installer.

The installer will be created as `ProxyCloud_Setup.exe` in the project root directory.

## Manual Build with PyInstaller

If you prefer to run PyInstaller manually, use the following command:

```bash
pyinstaller --name=ProxyCloud --onedir --windowed --icon=icons/logo.ico --add-data="icons;icons" --add-data="xray;xray" --add-data="base.json;." --add-data="default.json;." main.py
```

On macOS/Linux, replace semicolons with colons in the --add-data parameters:

```bash
pyinstaller --name=ProxyCloud --onedir --windowed --icon=icons/logo.ico --add-data="icons:icons" --add-data="xray:xray" --add-data="base.json:." --add-data="default.json:." main.py
```

## Troubleshooting

### Missing Dependencies

If you encounter errors about missing dependencies, ensure all required packages are installed:

```bash
pip install -r requirements.txt
```

### PyInstaller Issues

If PyInstaller fails to create the executable, try:

1. Updating PyInstaller: `pip install --upgrade pyinstaller`
2. Running with the `--debug=all` flag to get more information about the error

### Windows Defender or Antivirus Alerts

Some antivirus software may flag PyInstaller-created executables. This is a known false positive. You may need to add an exception in your antivirus software.

## Distribution

After building, you can distribute:

- The entire `dist/ProxyCloud` directory (for portable use)
- The Windows installer `ProxyCloud_Setup.exe` (Windows only)