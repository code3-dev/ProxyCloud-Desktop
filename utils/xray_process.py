import os
import platform
import subprocess
import signal
import time
import psutil
from pathlib import Path
from typing import Optional, Dict, Any

class XrayProcessManager:
    def __init__(self):
        self.process = None
        self.config_path = None
        self.xray_path = self._get_xray_path()
        self.is_running = False
        self.log_dir = self._get_log_dir()
    
    def _get_xray_path(self) -> str:
        """
        Get the path to the Xray executable based on the operating system.
        """
        base_dir = Path(__file__).parent.parent
        
        if platform.system() == "Windows":
            return str(base_dir / "xray" / "win" / "xray.exe")
        else:  # Linux, Darwin, etc.
            return str(base_dir / "xray" / "linux" / "xray")
            
    def _get_log_dir(self) -> Path:
        """
        Get the directory for Xray logs, using AppData on Windows.
        """
        if platform.system() == "Windows":
            app_data = os.environ.get('APPDATA')
            if app_data:
                log_dir = Path(app_data) / "ProxyCloud" / "logs"
            else:
                log_dir = Path("logs")
        else:
            log_dir = Path("logs")
            
        # Ensure the directory exists with proper permissions
        try:
            log_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
        except Exception as e:
            print(f"Warning: Failed to create log directory: {e}")
            
        return log_dir
    
    def start(self, config_path: str) -> bool:
        """
        Start the Xray process with the specified configuration.
        """
        if self.is_running:
            self.stop()
        
        self.config_path = config_path
        
        try:
            # Ensure the Xray executable is executable on Unix-like systems
            if platform.system() != "Windows":
                os.chmod(self.xray_path, 0o755)
            
            # Create log files in the log directory
            log_time = time.strftime("%Y%m%d-%H%M%S")
            stdout_log = self.log_dir / f"xray-stdout-{log_time}.log"
            stderr_log = self.log_dir / f"xray-stderr-{log_time}.log"
            
            # Open log files with proper permissions
            stdout_file = open(stdout_log, "w")
            stderr_file = open(stderr_log, "w")
            
            # Set file permissions
            try:
                os.chmod(stdout_log, 0o644)
                os.chmod(stderr_log, 0o644)
            except Exception as e:
                print(f"Warning: Failed to set log file permissions: {e}")
            
            # Start the Xray process with log redirection
            self.process = subprocess.Popen(
                [self.xray_path, "-config", config_path],
                stdout=stdout_file,
                stderr=stderr_file,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Wait a moment to check if the process started successfully
            time.sleep(1)
            if self.process.poll() is None:  # Process is still running
                self.is_running = True
                return True
            else:
                # Read error from the log file
                stderr_file.close()
                with open(stderr_log, "r") as f:
                    error_output = f.read()
                print(f"Failed to start Xray: {error_output}")
                return False
        except Exception as e:
            print(f"Error starting Xray: {e}")
            return False
        except PermissionError as pe:
            print(f"Permission error starting Xray: {pe}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the Xray process.
        """
        if not self.is_running or self.process is None:
            self.is_running = False
            self.process = None
            return True
        
        try:
            # Try to terminate the process gracefully
            if platform.system() == "Windows":
                self.process.terminate()
            else:
                os.kill(self.process.pid, signal.SIGTERM)
            
            # Wait for the process to terminate
            for _ in range(10):  # Wait up to 5 seconds
                if self.process.poll() is not None:  # Process has terminated
                    break
                time.sleep(0.5)
            
            # If the process is still running, force kill it
            if self.process.poll() is None:
                if platform.system() == "Windows":
                    self.process.kill()
                else:
                    os.kill(self.process.pid, signal.SIGKILL)
            
            # Close stdout and stderr if they're still open
            if hasattr(self.process, 'stdout') and self.process.stdout:
                try:
                    self.process.stdout.close()
                except:
                    pass
                    
            if hasattr(self.process, 'stderr') and self.process.stderr:
                try:
                    self.process.stderr.close()
                except:
                    pass
            
            # Kill any remaining Xray processes with the same executable path
            self._kill_remaining_xray_processes()
            
            self.is_running = False
            self.process = None
            return True
        except Exception as e:
            print(f"Error stopping Xray: {e}")
            # Even if there's an error, mark as not running to prevent issues
            self.is_running = False
            self.process = None
            return False
            
    def _kill_remaining_xray_processes(self):
        """
        Kill any remaining Xray processes that might be running.
        """
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    # Check if it's an Xray process
                    if 'xray' in proc.info['name'].lower():
                        # Don't kill our own process if it's still valid
                        if self.process and proc.info['pid'] == self.process.pid:
                            continue
                        # Kill the process
                        p = psutil.Process(proc.info['pid'])
                        p.terminate()
                        p.wait(timeout=3)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception as e:
            print(f"Error killing remaining Xray processes: {e}")
    
    def restart(self) -> bool:
        """
        Restart the Xray process with the current configuration.
        """
        if self.config_path is None:
            return False
        
        self.stop()
        return self.start(self.config_path)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Xray process.
        """
        if not self.is_running or self.process is None:
            return {
                "running": False,
                "pid": None,
                "cpu_percent": 0,
                "memory_percent": 0
            }
        
        try:
            # Check if the process is still running
            if self.process.poll() is not None:  # Process has terminated
                self.is_running = False
                self.process = None
                return {
                    "running": False,
                    "pid": None,
                    "cpu_percent": 0,
                    "memory_percent": 0
                }
            
            # Get process statistics
            proc = psutil.Process(self.process.pid)
            return {
                "running": True,
                "pid": self.process.pid,
                "cpu_percent": proc.cpu_percent(),
                "memory_percent": proc.memory_percent()
            }
        except Exception as e:
            print(f"Error getting Xray status: {e}")
            self.is_running = False
            self.process = None
            return {
                "running": False,
                "pid": None,
                "cpu_percent": 0,
                "memory_percent": 0
            }