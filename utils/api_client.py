import requests
import json
from typing import List, Dict, Any, Optional

def fetch_configs_from_api(api_url: str = "https://raw.githubusercontent.com/darkvpnapp/CloudflarePlus/refs/heads/main/proxy") -> List[Dict[str, Any]]:
    """
    Fetch proxy configurations from the specified API URL.
    """
    try:
        # Send a GET request to the API
        response = requests.get(api_url, timeout=10)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the response content
            content = response.text.strip()
            
            # Split the content by lines and filter out empty lines
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            # Parse each line as a proxy URL
            from utils.proxy_parser import parse_proxy_url
            
            configs = []
            for line in lines:
                config = parse_proxy_url(line)
                if config:
                    configs.append(config)
            
            return configs
        else:
            print(f"API request failed with status code: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching configs from API: {e}")
        return []

def fetch_config_by_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single proxy URL and return its configuration.
    """
    try:
        from utils.proxy_parser import parse_proxy_url
        return parse_proxy_url(url)
    except Exception as e:
        print(f"Error parsing proxy URL: {e}")
        return None