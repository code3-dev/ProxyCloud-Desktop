import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

def generate_xray_config(proxy_config: Dict[str, Any], tun_mode: bool = False) -> Dict[str, Any]:
    """
    Generate a complete Xray configuration based on the proxy settings.
    """
    # Try to load base configuration from base.json if it exists
    base_config = {}
    base_path = Path(__file__).parent.parent / "base.json"
    if base_path.exists():
        try:
            with open(base_path, 'r') as f:
                base_config = json.load(f)
        except Exception as e:
            print(f"Error loading base.json: {e}")
    
    # Start with a default configuration
    config = {
        "log": {
            "loglevel": "warning",
            "access": "access.log",
            "error": "error.log"
        },
        "inbounds": [],
        "outbounds": [],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "ip": ["geoip:private"],
                    "outboundTag": "direct"
                }
            ]
        }
    }
    
    # Apply DNS settings from base config if available
    if "dns" in base_config:
        config["dns"] = base_config["dns"]
    
    # Apply routing rules from base config if available
    if "routing" in base_config and "rules" in base_config["routing"]:
        config["routing"]["rules"] = base_config["routing"]["rules"]
    
    # Add inbound based on whether TUN mode is enabled
    if tun_mode:
        # TUN inbound for routing all traffic
        tun_inbound = {
            "tag": "tun-in",
            "port": 0,
            "protocol": "dokodemo-door",
            "settings": {
                "network": "tcp,udp",
                "followRedirect": True
            },
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            },
            "streamSettings": {
                "sockopt": {
                    "tproxy": "tproxy"
                }
            }
        }
        config["inbounds"].append(tun_inbound)
    else:
        # HTTP inbound for HTTP proxy
        http_inbound = {
            "tag": "http-in",
            "port": 10809,
            "listen": "127.0.0.1",
            "protocol": "http",
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            },
            "settings": {
                "auth": "noauth",
                "udp": True
            }
        }
        
        # SOCKS inbound for SOCKS proxy
        socks_inbound = {
            "tag": "socks-in",
            "port": 10808,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "sniffing": {
                "enabled": True,
                "destOverride": ["http", "tls"]
            },
            "settings": {
                "auth": "noauth",
                "udp": True
            }
        }
        
        config["inbounds"].extend([http_inbound, socks_inbound])
    
    # Add outbound based on proxy type
    proxy_outbound = {
        "tag": "proxy",
        "settings": {}
    }
    
    if proxy_config["type"] == "ss":
        proxy_outbound["protocol"] = "shadowsocks"
        proxy_outbound["settings"] = {
            "servers": [
                {
                    "address": proxy_config["server"],
                    "port": proxy_config["port"],
                    "method": proxy_config["method"],
                    "password": proxy_config["password"],
                    "level": 8  # Add user level from base.json
                }
            ]
        }
        
        # Check if we have base config with Shadowsocks streamSettings
        base_stream_settings = None
        if base_config and "outbounds" in base_config:
            for outbound in base_config["outbounds"]:
                if outbound.get("protocol") == "shadowsocks" and "streamSettings" in outbound:
                    base_stream_settings = outbound["streamSettings"]
                    break
        
        # Add stream settings if available in base config
        if base_stream_settings:
            proxy_outbound["streamSettings"] = base_stream_settings.copy()
            
        # Add mux settings from base config if available
        if base_config and "outbounds" in base_config:
            for outbound in base_config["outbounds"]:
                if outbound.get("protocol") == "shadowsocks" and "mux" in outbound:
                    proxy_outbound["mux"] = outbound["mux"]
                    break
    elif proxy_config["type"] == "vmess":
        proxy_outbound["protocol"] = "vmess"
        proxy_outbound["settings"] = {
            "vnext": [
                {
                    "address": proxy_config["server"],
                    "port": proxy_config["port"],
                    "users": [
                        {
                            "id": proxy_config["uuid"],
                            "alterId": proxy_config.get("alterId", 0),
                            "security": proxy_config.get("security", "auto"),
                            "level": 8  # Add user level from base.json
                        }
                    ]
                }
            ]
        }
        
        # Check if we have base config with VMess streamSettings
        base_stream_settings = None
        if base_config and "outbounds" in base_config:
            for outbound in base_config["outbounds"]:
                if outbound.get("protocol") == "vmess" and "streamSettings" in outbound:
                    base_stream_settings = outbound["streamSettings"]
                    break
        
        # Add stream settings
        network_type = proxy_config.get("network", "tcp")
        
        # Use base stream settings if available, otherwise create new ones
        if base_stream_settings:
            proxy_outbound["streamSettings"] = base_stream_settings.copy()
            # Override network type if specified in proxy_config
            if "network" in proxy_config:
                proxy_outbound["streamSettings"]["network"] = network_type
        else:
            proxy_outbound["streamSettings"] = {
                "network": network_type
            }
        
        # Configure TLS if enabled
        if proxy_config.get("tls", False) or proxy_config.get("security") == "tls":
            proxy_outbound["streamSettings"]["security"] = "tls"
            proxy_outbound["streamSettings"]["tlsSettings"] = {
                "allowInsecure": True,  # Allow insecure connections (self-signed certs)
                "serverName": proxy_config.get("sni", proxy_config.get("host", proxy_config["server"]))
            }
        
        # Configure WebSocket if used
        if network_type == "ws":
            proxy_outbound["streamSettings"]["wsSettings"] = {
                "path": proxy_config.get("ws-path", proxy_config.get("path", "/")),
                "headers": {
                    "Host": proxy_config.get("ws-host", proxy_config.get("host", proxy_config["server"]))
                }
            }
        
        # Configure HTTP/2 if used
        elif network_type == "h2" or network_type == "http":
            proxy_outbound["streamSettings"]["httpSettings"] = {
                "path": proxy_config.get("h2-path", proxy_config.get("path", "/")),
                "host": [proxy_config.get("h2-host", proxy_config.get("host", proxy_config["server"]))]
            }
            
        # Add mux settings from base config if available
        if base_config and "outbounds" in base_config:
            for outbound in base_config["outbounds"]:
                if outbound.get("protocol") == "vmess" and "mux" in outbound:
                    proxy_outbound["mux"] = outbound["mux"]
                    break
    elif proxy_config["type"] == "vless":
        proxy_outbound["protocol"] = "vless"
        proxy_outbound["settings"] = {
            "vnext": [
                {
                    "address": proxy_config["server"],
                    "port": proxy_config["port"],
                    "users": [
                        {
                            "id": proxy_config["uuid"],
                            "encryption": proxy_config.get("encryption", "none"),
                            "level": 8  # Add user level from base.json
                        }
                    ]
                }
            ]
        }
        
        # Check if we have base config with VLESS streamSettings
        base_stream_settings = None
        if base_config and "outbounds" in base_config:
            for outbound in base_config["outbounds"]:
                if outbound.get("protocol") == "vless" and "streamSettings" in outbound:
                    base_stream_settings = outbound["streamSettings"]
                    break
        
        # Add stream settings
        network_type = proxy_config.get("network", "tcp")
        
        # Use base stream settings if available, otherwise create new ones
        if base_stream_settings:
            proxy_outbound["streamSettings"] = base_stream_settings.copy()
            # Override network type if specified in proxy_config
            if "network" in proxy_config:
                proxy_outbound["streamSettings"]["network"] = network_type
        else:
            proxy_outbound["streamSettings"] = {
                "network": network_type
            }
        
        # Configure security (TLS/REALITY)
        if proxy_config.get("security"):
            proxy_outbound["streamSettings"]["security"] = proxy_config["security"]
            
            if proxy_config["security"] == "tls":
                proxy_outbound["streamSettings"]["tlsSettings"] = {
                    "serverName": proxy_config.get("sni", proxy_config["server"]),
                    "allowInsecure": True  # Allow insecure connections
                }
                
                if proxy_config.get("alpn"):
                    proxy_outbound["streamSettings"]["tlsSettings"]["alpn"] = proxy_config["alpn"].split(",")
                    
                if proxy_config.get("fp"):
                    proxy_outbound["streamSettings"]["tlsSettings"]["fingerprint"] = proxy_config["fp"]
        
        # Configure WebSocket if used
        if proxy_config.get("network") == "ws":
            proxy_outbound["streamSettings"]["wsSettings"] = {
                "path": proxy_config.get("ws-path", "/"),
                "headers": {
                    "Host": proxy_config.get("ws-host", proxy_config["server"])
                }
            }
        # Configure gRPC if used
        elif proxy_config.get("network") == "grpc":
            proxy_outbound["streamSettings"]["grpcSettings"] = {
                "serviceName": proxy_config.get("grpc-service-name", "")
            }
            
        # Add mux settings from base config if available
        if base_config and "outbounds" in base_config:
            for outbound in base_config["outbounds"]:
                if outbound.get("protocol") == "vless" and "mux" in outbound:
                    proxy_outbound["mux"] = outbound["mux"]
                    break
    
    # Add direct outbound for bypassing proxy for certain destinations
    direct_outbound = {
        "tag": "direct",
        "protocol": "freedom",
        "settings": {}
    }
    
    # Add block outbound for blocking certain destinations
    block_outbound = {
        "tag": "block",
        "protocol": "blackhole",
        "settings": {}
    }
    
    config["outbounds"] = [proxy_outbound, direct_outbound, block_outbound]
    
    return config

def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    Save the Xray configuration to a file.
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write the configuration to file
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

def load_config(config_path: str) -> Optional[Dict[str, Any]]:
    """
    Load an Xray configuration from a file.
    """
    try:
        if not os.path.exists(config_path):
            return None
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None