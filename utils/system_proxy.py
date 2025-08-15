import platform
import subprocess
import os
from typing import Dict, Any, Optional, Tuple

class SystemProxyManager:
    def __init__(self):
        self.system = platform.system()
        self.http_port = 10809
        self.socks_port = 10808
        self.is_enabled = False
    
    def enable(self, http_port: int = 10809, socks_port: int = 10808) -> bool:
        """
        Enable system proxy settings.
        """
        self.http_port = http_port
        self.socks_port = socks_port
        
        if self.system == "Windows":
            return self._enable_windows_proxy()
        elif self.system == "Darwin":  # macOS
            return self._enable_macos_proxy()
        elif self.system == "Linux":
            return self._enable_linux_proxy()
        else:
            print(f"Unsupported operating system: {self.system}")
            return False
    
    def disable(self) -> bool:
        """
        Disable system proxy settings.
        """
        if self.system == "Windows":
            return self._disable_windows_proxy()
        elif self.system == "Darwin":  # macOS
            return self._disable_macos_proxy()
        elif self.system == "Linux":
            return self._disable_linux_proxy()
        else:
            print(f"Unsupported operating system: {self.system}")
            return False
    
    def _enable_windows_proxy(self) -> bool:
        """
        Enable system proxy on Windows.
        """
        try:
            import winreg
            
            # Open the Internet Settings registry key
            internet_settings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_WRITE
            )
            
            # Save current settings for later restoration
            self._save_current_windows_settings()
            
            # Set proxy settings
            winreg.SetValueEx(internet_settings, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(internet_settings, "ProxyServer", 0, winreg.REG_SZ, f"127.0.0.1:{self.http_port}")
            winreg.SetValueEx(internet_settings, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
            
            # Close the registry key
            winreg.CloseKey(internet_settings)
            
            # Notify the system about the proxy change
            self._notify_windows_proxy_change()
            
            self.is_enabled = True
            return True
        except Exception as e:
            print(f"Error enabling Windows proxy: {e}")
            return False
    
    def _disable_windows_proxy(self) -> bool:
        """
        Disable system proxy on Windows.
        """
        try:
            import winreg
            
            # Open the Internet Settings registry key
            internet_settings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_WRITE
            )
            
            # Restore previous settings or disable proxy
            if hasattr(self, "_previous_windows_settings"):
                proxy_enable = self._previous_windows_settings.get("ProxyEnable", 0)
                proxy_server = self._previous_windows_settings.get("ProxyServer", "")
                proxy_override = self._previous_windows_settings.get("ProxyOverride", "<local>")
                
                winreg.SetValueEx(internet_settings, "ProxyEnable", 0, winreg.REG_DWORD, proxy_enable)
                if proxy_server:
                    winreg.SetValueEx(internet_settings, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
                if proxy_override:
                    winreg.SetValueEx(internet_settings, "ProxyOverride", 0, winreg.REG_SZ, proxy_override)
            else:
                # Just disable the proxy
                winreg.SetValueEx(internet_settings, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            
            # Close the registry key
            winreg.CloseKey(internet_settings)
            
            # Notify the system about the proxy change
            self._notify_windows_proxy_change()
            
            self.is_enabled = False
            return True
        except Exception as e:
            print(f"Error disabling Windows proxy: {e}")
            return False
    
    def _save_current_windows_settings(self) -> None:
        """
        Save current Windows proxy settings for later restoration.
        """
        try:
            import winreg
            
            # Open the Internet Settings registry key
            internet_settings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0, winreg.KEY_READ
            )
            
            # Read current settings
            self._previous_windows_settings = {}
            
            try:
                self._previous_windows_settings["ProxyEnable"] = winreg.QueryValueEx(internet_settings, "ProxyEnable")[0]
            except:
                self._previous_windows_settings["ProxyEnable"] = 0
            
            try:
                self._previous_windows_settings["ProxyServer"] = winreg.QueryValueEx(internet_settings, "ProxyServer")[0]
            except:
                self._previous_windows_settings["ProxyServer"] = ""
            
            try:
                self._previous_windows_settings["ProxyOverride"] = winreg.QueryValueEx(internet_settings, "ProxyOverride")[0]
            except:
                self._previous_windows_settings["ProxyOverride"] = "<local>"
            
            # Close the registry key
            winreg.CloseKey(internet_settings)
        except Exception as e:
            print(f"Error saving Windows proxy settings: {e}")
    
    def _notify_windows_proxy_change(self) -> None:
        """
        Notify Windows about proxy settings change.
        """
        try:
            import win32con
            import win32gui
            
            # Notify the system about the proxy change
            internet_option_settings_changed = 39
            internet_option_refresh = 37
            win32gui.SendMessageTimeout(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 0, 0, 1000)
            win32gui.SendMessageTimeout(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, internet_option_settings_changed, 0, 1000)
            win32gui.SendMessageTimeout(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, internet_option_refresh, 0, 1000)
        except Exception as e:
            print(f"Error notifying Windows about proxy change: {e}")
    
    def _enable_macos_proxy(self) -> bool:
        """
        Enable system proxy on macOS.
        """
        try:
            # Save current settings for later restoration
            self._save_current_macos_settings()
            
            # Set HTTP proxy
            subprocess.run([
                "networksetup", "-setwebproxy", "Wi-Fi", "127.0.0.1", str(self.http_port)
            ])
            subprocess.run([
                "networksetup", "-setsecurewebproxy", "Wi-Fi", "127.0.0.1", str(self.http_port)
            ])
            
            # Set SOCKS proxy
            subprocess.run([
                "networksetup", "-setsocksfirewallproxy", "Wi-Fi", "127.0.0.1", str(self.socks_port)
            ])
            
            # Enable proxies
            subprocess.run(["networksetup", "-setwebproxystate", "Wi-Fi", "on"])
            subprocess.run(["networksetup", "-setsecurewebproxystate", "Wi-Fi", "on"])
            subprocess.run(["networksetup", "-setsocksfirewallproxystate", "Wi-Fi", "on"])
            
            self.is_enabled = True
            return True
        except Exception as e:
            print(f"Error enabling macOS proxy: {e}")
            return False
    
    def _disable_macos_proxy(self) -> bool:
        """
        Disable system proxy on macOS.
        """
        try:
            # Disable proxies
            subprocess.run(["networksetup", "-setwebproxystate", "Wi-Fi", "off"])
            subprocess.run(["networksetup", "-setsecurewebproxystate", "Wi-Fi", "off"])
            subprocess.run(["networksetup", "-setsocksfirewallproxystate", "Wi-Fi", "off"])
            
            self.is_enabled = False
            return True
        except Exception as e:
            print(f"Error disabling macOS proxy: {e}")
            return False
    
    def _save_current_macos_settings(self) -> None:
        """
        Save current macOS proxy settings for later restoration.
        """
        try:
            # This is a simplified version, in a real application you might want to
            # save more detailed settings and handle multiple network interfaces
            self._previous_macos_settings = {}
            
            # Get HTTP proxy state
            result = subprocess.run(
                ["networksetup", "-getwebproxy", "Wi-Fi"],
                capture_output=True, text=True
            )
            self._previous_macos_settings["http_enabled"] = "Enabled: Yes" in result.stdout
            
            # Get HTTPS proxy state
            result = subprocess.run(
                ["networksetup", "-getsecurewebproxy", "Wi-Fi"],
                capture_output=True, text=True
            )
            self._previous_macos_settings["https_enabled"] = "Enabled: Yes" in result.stdout
            
            # Get SOCKS proxy state
            result = subprocess.run(
                ["networksetup", "-getsocksfirewallproxy", "Wi-Fi"],
                capture_output=True, text=True
            )
            self._previous_macos_settings["socks_enabled"] = "Enabled: Yes" in result.stdout
        except Exception as e:
            print(f"Error saving macOS proxy settings: {e}")
    
    def _enable_linux_proxy(self) -> bool:
        """
        Enable system proxy on Linux.
        """
        try:
            # Save current settings for later restoration
            self._save_current_linux_settings()
            
            # Set environment variables
            os.environ["http_proxy"] = f"http://127.0.0.1:{self.http_port}"
            os.environ["https_proxy"] = f"http://127.0.0.1:{self.http_port}"
            os.environ["all_proxy"] = f"socks5://127.0.0.1:{self.socks_port}"
            
            # Set GNOME proxy settings if available
            try:
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy", "mode", "manual"
                ])
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.http", "host", "127.0.0.1"
                ])
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.http", "port", str(self.http_port)
                ])
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.https", "host", "127.0.0.1"
                ])
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.https", "port", str(self.http_port)
                ])
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.socks", "host", "127.0.0.1"
                ])
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy.socks", "port", str(self.socks_port)
                ])
            except:
                # GNOME settings not available, continue with environment variables only
                pass
            
            self.is_enabled = True
            return True
        except Exception as e:
            print(f"Error enabling Linux proxy: {e}")
            return False
    
    def _disable_linux_proxy(self) -> bool:
        """
        Disable system proxy on Linux.
        """
        try:
            # Unset environment variables
            if "http_proxy" in os.environ:
                del os.environ["http_proxy"]
            if "https_proxy" in os.environ:
                del os.environ["https_proxy"]
            if "all_proxy" in os.environ:
                del os.environ["all_proxy"]
            
            # Disable GNOME proxy settings if available
            try:
                subprocess.run([
                    "gsettings", "set", "org.gnome.system.proxy", "mode", "none"
                ])
            except:
                # GNOME settings not available
                pass
            
            self.is_enabled = False
            return True
        except Exception as e:
            print(f"Error disabling Linux proxy: {e}")
            return False
    
    def _save_current_linux_settings(self) -> None:
        """
        Save current Linux proxy settings for later restoration.
        """
        try:
            self._previous_linux_settings = {}
            
            # Save environment variables
            if "http_proxy" in os.environ:
                self._previous_linux_settings["http_proxy"] = os.environ["http_proxy"]
            if "https_proxy" in os.environ:
                self._previous_linux_settings["https_proxy"] = os.environ["https_proxy"]
            if "all_proxy" in os.environ:
                self._previous_linux_settings["all_proxy"] = os.environ["all_proxy"]
            
            # Save GNOME proxy settings if available
            try:
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.system.proxy", "mode"],
                    capture_output=True, text=True
                )
                self._previous_linux_settings["gnome_proxy_mode"] = result.stdout.strip()
            except:
                # GNOME settings not available
                pass
        except Exception as e:
            print(f"Error saving Linux proxy settings: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the system proxy.
        """
        return {
            "enabled": self.is_enabled,
            "http_port": self.http_port,
            "socks_port": self.socks_port
        }