# ProxyCloud

Proxy Cloud is an open-source VPN that’s fast, unlimited, secure, and completely free.

<p align="center">
  <b>Available for Desktop and Android platforms</b>
</p>

<p align="center">
  <a href="https://github.com/code3-dev/ProxyCloud-Desktop/releases/latest"><img src="https://img.shields.io/badge/Desktop-Windows%20|%20Linux-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Desktop"></a>
  <a href="#android-version"><img src="https://img.shields.io/badge/Mobile-Android-3DDC84?style=for-the-badge&logo=android&logoColor=white" alt="Android"></a>
</p>

## Features

- Modern UI built with PyQt6
- Support for multiple protocols:
  - Shadowsocks (SS)
  - VMess
  - VLESS
- System proxy configuration
- API integration to fetch configurations from GitHub
- System tray integration
- Settings persistence

## Requirements

See `requirements.txt` for Python dependencies.

## Usage

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python main.py
   ```

## Building the Application

1. Build the application:
   ```
   python build.py
   ```

The built application will be available in the `dist/ProxyCloud` directory.

For detailed build instructions, see [BUILD.md](BUILD.md).

3. Add servers manually or fetch from the API

4. Connect to a server

## Directory Structure

- `main.py`: Main application entry point
- `utils/`: Utility modules
  - `proxy_parser.py`: Functions to parse SS, VMess, and VLESS URLs
  - `xray_config.py`: Xray configuration generator
  - `xray_process.py`: Xray process management
  - `system_proxy.py`: System proxy configuration
  - `tun_manager.py`: TUN mode support
  - `api_client.py`: API integration for fetching configurations
- `icons/`: Application icons
- `xray/`: Xray core executables for different platforms

## Android Version

ProxyCloud is also available as a Flutter-based Android application with the following features:

- V2Ray VPN with one-tap connection
- Subscription management
- Telegram MTProto proxies support
- Advanced tools (IP information, host checker, speed test)
- Modern dark-themed UI

For more information and installation instructions, check out the [Android repository](https://github.com/code3-dev/ProxyCloud).