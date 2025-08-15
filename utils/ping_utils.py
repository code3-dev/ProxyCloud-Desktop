import socket
import time
import threading
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

def tcp_ping(host: str, port: int, timeout: float = 1.0) -> Optional[float]:
    """
    Measure TCP connection time to a host:port.
    Returns the delay in milliseconds or None if connection failed.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        start_time = time.time()
        result = sock.connect_ex((host, port))
        end_time = time.time()
        
        sock.close()
        
        if result == 0:  # Connection successful
            return (end_time - start_time) * 1000  # Convert to milliseconds
        return None
    except Exception as e:
        print(f"Error during TCP ping to {host}:{port}: {e}")
        return None

def test_url_latency(url: str, timeout: float = 1.0) -> Optional[float]:
    """
    Test latency to a URL by establishing a TCP connection to the host.
    Returns the delay in milliseconds or None if connection failed.
    """
    try:
        parsed_url = urlparse(url)
        host = parsed_url.netloc
        
        # If port is specified in the URL, use it; otherwise, use default port based on scheme
        if ':' in host:
            host, port_str = host.split(':', 1)
            port = int(port_str)
        else:
            port = 443 if parsed_url.scheme == 'https' else 80
        
        return tcp_ping(host, port, timeout)
    except Exception as e:
        print(f"Error testing URL latency for {url}: {e}")
        return None

def measure_config_delay(config: Dict[str, Any], test_url: str = "https://www.gstatic.com/generate_204", timeout: float = 1.0) -> Dict[str, Any]:
    """
    Measure delay for a proxy configuration using TCP ping.
    Adds a 'delay' field to the config with the measured delay in milliseconds.
    If measurement fails, 'delay' will be None.
    """
    try:
        server = config.get('server')
        port = config.get('port', 0)
        
        if not server or not port:
            config['delay'] = None
            return config
        
        # Measure delay to the proxy server
        delay = tcp_ping(server, int(port), timeout)
        
        # Add delay to the config
        config['delay'] = delay
        return config
    except Exception as e:
        print(f"Error measuring config delay: {e}")
        config['delay'] = None
        return config

def measure_configs_delay(configs: List[Dict[str, Any]], test_url: str = "https://www.gstatic.com/generate_204", timeout: float = 1.0, max_threads: int = 10) -> List[Dict[str, Any]]:
    """
    Measure delay for multiple proxy configurations in parallel using threading.
    Returns the list of configs with added 'delay' field.
    """
    if not configs:
        return []
    
    # Create a copy of configs to avoid modifying the original
    configs_copy = configs.copy()
    
    # Function to process a batch of configs
    def process_batch(batch):
        for config in batch:
            measure_config_delay(config, test_url, timeout)
    
    # Split configs into batches for threading
    batch_size = max(1, len(configs_copy) // max_threads)
    batches = [configs_copy[i:i + batch_size] for i in range(0, len(configs_copy), batch_size)]
    
    # Create and start threads
    threads = []
    for batch in batches:
        thread = threading.Thread(target=process_batch, args=(batch,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    return configs_copy