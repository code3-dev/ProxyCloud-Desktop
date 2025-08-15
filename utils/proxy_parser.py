import base64
import json
import re
import urllib.parse
from typing import Dict, Any, Optional

def parse_ss_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Parse Shadowsocks URL format: ss://base64(method:password@host:port)#tag
    or ss://base64(method:password)@host:port#tag
    """
    if not url.startswith('ss://'):
        return None
    
    try:
        # Remove the 'ss://' prefix
        url = url[5:]
        
        # Extract the tag if present
        tag = ''
        if '#' in url:
            url, tag = url.split('#', 1)
            tag = urllib.parse.unquote(tag)
        
        # Check if the URL is using the legacy format or the new format
        if '@' in url:
            # New format: ss://base64(method:password)@host:port
            try:
                user_info, server_info = url.split('@', 1)
            except ValueError:
                print(f"Error parsing SS URL: missing @ separator")
                return None
            
            # If user_info is base64 encoded
            if not ':' in user_info:
                try:
                    # Fix padding issues
                    # Remove any existing padding
                    user_info = user_info.rstrip('=')
                    # Add proper padding
                    padding = (4 - len(user_info) % 4) % 4
                    if padding:
                        user_info += '=' * padding
                    user_info = base64.urlsafe_b64decode(user_info).decode('utf-8')
                except Exception as e:
                    # Silently return None instead of printing error
                    # This prevents error messages from flooding the UI
                    return None  # Return None if base64 decoding fails
            
            try:
                if ':' not in user_info:
                    print(f"Error parsing SS URL: missing : separator in method:password")
                    return None
                    
                method, password = user_info.split(':', 1)
                
                if ':' not in server_info:
                    print(f"Error parsing SS URL: missing : separator in host:port")
                    return None
                    
                host, port = server_info.split(':', 1)
            except ValueError as e:
                print(f"Error parsing SS URL components: {e}")
                return None
        else:
            # Legacy format: ss://base64(method:password@host:port)
            try:
                # Add padding if necessary
                padding = 4 - len(url) % 4
                if padding < 4:
                    url += '=' * padding
                decoded = base64.urlsafe_b64decode(url).decode('utf-8')
                
                # Extract method, password, host, and port
                if '@' not in decoded:
                    print(f"Error parsing SS URL: missing @ separator in decoded string")
                    return None
                    
                method_pass, host_port = decoded.split('@', 1)
                
                if ':' not in method_pass:
                    print(f"Error parsing SS URL: missing : separator in method:password")
                    return None
                    
                method, password = method_pass.split(':', 1)
                
                if ':' not in host_port:
                    print(f"Error parsing SS URL: missing : separator in host:port")
                    return None
                    
                host, port = host_port.split(':', 1)
            except Exception as e:
                print(f"Error parsing SS URL: {e}")
                return None
        
        return {
            'type': 'ss',
            'method': method,
            'password': password,
            'server': host,
            'port': int(port),
            'tag': tag
        }
    except Exception as e:
        print(f"Error parsing SS URL: {e}")
        return None

def parse_vmess_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Parse VMess URL format: vmess://base64(json)
    """
    if not url.startswith('vmess://'):
        return None
    
    try:
        # Remove the 'vmess://' prefix
        b64_str = url[8:]
        
        # Remove any existing padding
        b64_str = b64_str.rstrip('=')
        
        # Add proper padding
        padding = (4 - len(b64_str) % 4) % 4
        if padding:
            b64_str += '=' * padding
        
        # Decode the base64 string
        try:
            decoded = base64.urlsafe_b64decode(b64_str).decode('utf-8')
        except Exception as e:
            print(f"Error decoding VMess base64: {e}")
            return None
        
        # Parse the JSON
        try:
            config = json.loads(decoded)
        except json.JSONDecodeError as e:
            print(f"Error parsing VMess JSON: {e}")
            return None
        
        # Create a standardized config
        result = {
            'type': 'vmess',
            'server': config.get('add', ''),
            'port': int(config.get('port', 0)),
            'uuid': config.get('id', ''),
            'alterId': int(config.get('aid', 0)),
            'security': config.get('scy', 'auto'),
            'network': config.get('net', 'tcp'),
            'tag': config.get('ps', '')
        }
        
        # Add network specific settings
        if result['network'] == 'ws':
            result['ws-path'] = config.get('path', '')
            result['ws-host'] = config.get('host', '')
        elif result['network'] == 'h2':
            result['h2-path'] = config.get('path', '')
            result['h2-host'] = config.get('host', '')
        elif result['network'] == 'quic':
            result['quic-security'] = config.get('quic-security', '')
            result['quic-key'] = config.get('quic-key', '')
        
        # TLS settings
        if config.get('tls', '') == 'tls':
            result['tls'] = True
            result['sni'] = config.get('sni', '')
        else:
            result['tls'] = False
        
        return result
    except Exception as e:
        print(f"Error parsing VMess URL: {e}")
        return None

def parse_vless_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Parse VLESS URL format: vless://uuid@host:port?encryption=none&security=tls&type=ws&host=xxx&path=xxx#tag
    """
    if not url.startswith('vless://'):
        return None
    
    try:
        # Remove the 'vless://' prefix
        url = url[8:]
        
        # Extract the tag if present
        tag = ''
        if '#' in url:
            url, tag = url.split('#', 1)
            tag = urllib.parse.unquote(tag)
        
        # Extract the UUID and server information
        uuid_part, server_part = url.split('@', 1)
        
        # Extract host and port
        server_info, params_str = server_part.split('?', 1) if '?' in server_part else (server_part, '')
        host, port = server_info.split(':', 1)
        
        # Parse parameters
        params = dict(urllib.parse.parse_qsl(params_str))
        
        result = {
            'type': 'vless',
            'server': host,
            'port': int(port),
            'uuid': uuid_part,
            'tag': tag,
            'encryption': params.get('encryption', 'none')
        }
        
        # Security settings
        if 'security' in params:
            result['security'] = params['security']
            if params['security'] == 'tls':
                result['sni'] = params.get('sni', '')
                result['alpn'] = params.get('alpn', '')
                result['fp'] = params.get('fp', '')
        
        # Transport settings
        if 'type' in params:
            result['network'] = params['type']
            if params['type'] == 'ws':
                result['ws-path'] = params.get('path', '')
                result['ws-host'] = params.get('host', '')
            elif params['type'] == 'h2':
                result['h2-path'] = params.get('path', '')
                result['h2-host'] = params.get('host', '')
            elif params['type'] == 'grpc':
                result['grpc-service-name'] = params.get('serviceName', '')
        
        return result
    except Exception as e:
        print(f"Error parsing VLESS URL: {e}")
        return None

def parse_proxy_url(url: str) -> Optional[Dict[str, Any]]:
    """
    Parse a proxy URL and return a standardized configuration.
    Supports SS, VMess, and VLESS protocols.
    """
    if url.startswith('ss://'):
        return parse_ss_url(url)
    elif url.startswith('vmess://'):
        return parse_vmess_url(url)
    elif url.startswith('vless://'):
        return parse_vless_url(url)
    else:
        return None