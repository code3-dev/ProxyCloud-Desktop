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
    
    def _get_xray_path(self) -> str:
        """
        Get the path to the Xray executable based on the operating system.
        """
        base_dir = Path(__file__).parent.parent
        
        if platform.system() == "Windows":
            return str(base_dir / "xray" / "win" / "xray.exe")
        else:  # Linux, Darwin, etc.
            return str(base_dir / "xray" / "linux" / "xray")
    
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
            
            # Start the Xray process
            self.process = subprocess.Popen(
                [self.xray_path, "-config", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            
            # Wait a moment to check if the process started successfully
            time.sleep(1)
            if self.process.poll() is None:  # Process is still running
                self.is_running = True
                return True
            else:
                error_output = self.process.stderr.read().decode('utf-8')
                print(f"Failed to start Xray: {error_output}")
                return False
        except Exception as e:
            print(f"Error starting Xray: {e}")
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