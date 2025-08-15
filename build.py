import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def build_app():
    print("Building ProxyCloud application...")
    
    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Attempting to install...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=5.13.0"])
            print("PyInstaller installed successfully.")
            # Re-import after installation
            import PyInstaller
        except Exception as e:
            print(f"Error installing PyInstaller: {e}")
            print("\nPlease install PyInstaller manually using:")
            print("pip install pyinstaller>=5.13.0")
            print("\nThen run this script again.")
            sys.exit(1)
    
    # Determine the current OS
    current_os = platform.system()
    print(f"Detected OS: {current_os}")
    
    # Create build directory
    build_dir = Path("build")
    dist_dir = Path("dist")
    
    # Clean previous builds
    if build_dir.exists():
        print("Cleaning previous build directory...")
        shutil.rmtree(build_dir)
    
    if dist_dir.exists():
        print("Cleaning previous dist directory...")
        shutil.rmtree(dist_dir)
    
    # Create directories
    build_dir.mkdir(exist_ok=True)
    
    # Define PyInstaller command with OS-specific icon
    icon_path = "icons/logo.ico" if current_os == "Windows" else "icons/logo.png"
    
    pyinstaller_args = [
        "--name=ProxyCloud",
        "--onedir",
        "--windowed",
        f"--icon={icon_path}",
        "--add-data=icons;icons",
        "--add-data=xray;xray",
        "--add-data=base.json;.",
        "--add-data=default.json;.",
        "main.py"
    ]
    
    # Adjust path separator for non-Windows platforms
    if current_os != "Windows":
        pyinstaller_args = [arg.replace(";", ":") for arg in pyinstaller_args]
    
    # Run PyInstaller
    print("Running PyInstaller...")
    pyinstaller_cmd = [sys.executable, "-m", "PyInstaller"] + pyinstaller_args
    subprocess.check_call(pyinstaller_cmd)
    
    # Create settings directory in the dist folder
    settings_dir = dist_dir / "ProxyCloud" / "settings"
    settings_dir.mkdir(exist_ok=True)
    
    # Create configs directory in the dist folder
    configs_dir = dist_dir / "ProxyCloud" / "configs"
    configs_dir.mkdir(exist_ok=True)
    
    print("\nBuild completed successfully!")
    print(f"Application packaged at: {dist_dir / 'ProxyCloud'}")

def create_installer():
    """Create an installer for Windows using NSIS (if available)"""
    if platform.system() != "Windows":
        print("Installer creation is only supported on Windows.")
        return
    
    try:
        # Check if NSIS is installed
        nsis_path = shutil.which("makensis")
        if not nsis_path:
            print("NSIS not found. Please install NSIS to create an installer.")
            print("Download from: https://nsis.sourceforge.io/Download")
            return
        
        print("Creating Windows installer with NSIS...")
        
        # Create NSIS script
        nsis_script = Path("installer.nsi")
        with open(nsis_script, "w") as f:
            f.write(r"""
!include "MUI2.nsh"

; Application information
Name "ProxyCloud"
OutFile "ProxyCloud_Setup.exe"
InstallDir "$PROGRAMFILES\ProxyCloud"

; Interface settings
!define MUI_ABORTWARNING
!define MUI_ICON "icons\logo.ico"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installation
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy all files from dist\ProxyCloud
    File /r "dist\ProxyCloud\*.*"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Create start menu shortcut
    CreateDirectory "$SMPROGRAMS\ProxyCloud"
    CreateShortcut "$SMPROGRAMS\ProxyCloud\ProxyCloud.lnk" "$INSTDIR\ProxyCloud.exe"
    CreateShortcut "$SMPROGRAMS\ProxyCloud\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    
    ; Create desktop shortcut
    CreateShortcut "$DESKTOP\ProxyCloud.lnk" "$INSTDIR\ProxyCloud.exe"
    
    ; Add to Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud" \
                 "DisplayName" "ProxyCloud"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud" \
                 "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud" \
                 "DisplayIcon" "$INSTDIR\ProxyCloud.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud" \
                 "Publisher" "ProxyCloud Team"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud" \
                 "DisplayVersion" "1.0.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud" \
                 "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud" \
                 "NoRepair" 1
SectionEnd

; Uninstallation
Section "Uninstall"
    ; Remove files and directories
    RMDir /r "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$DESKTOP\ProxyCloud.lnk"
    RMDir /r "$SMPROGRAMS\ProxyCloud"
    
    ; Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ProxyCloud"
SectionEnd
            """)
        
        # Run NSIS
        subprocess.check_call([nsis_path, str(nsis_script)])
        
        print("\nInstaller created successfully!")
        print(f"Installer location: {Path().absolute() / 'ProxyCloud_Setup.exe'}")
        
    except Exception as e:
        print(f"Error creating installer: {e}")

if __name__ == "__main__":
    build_app()
    
    # Ask if user wants to create an installer (Windows only)
    if platform.system() == "Windows":
        create_installer_input = input("\nDo you want to create a Windows installer? (y/n): ")
        if create_installer_input.lower() == "y":
            create_installer()