
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
            