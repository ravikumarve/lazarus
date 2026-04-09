# 🌐 Lazarus Web Dashboard - Port Configuration Guide

## 🚀 Quick Start

### Default Port (6666)
```bash
python3 -m web.server
# Access: http://localhost:6666
```

### Custom Port
```bash
# Method 1: Environment variable
export LAZARUS_PORT=8000
python3 -m web.server
# Access: http://localhost:8000

# Method 2: Command-line argument (uvicorn)
uvicorn web.server:app --port 8000
# Access: http://localhost:8000

# Method 3: One-liner
LAZARUS_PORT=8000 python3 -m web.server
# Access: http://localhost:8000
```

### Custom Host
```bash
# Bind to localhost only (more secure)
export LAZARUS_HOST=127.0.0.1
export LAZARUS_PORT=8080
python3 -m web.server
# Access: http://127.0.0.1:8080

# Bind to all interfaces (for network access)
export LAZARUS_HOST=0.0.0.0
export LAZARUS_PORT=9000
python3 -m web.server
# Access: http://localhost:9000 or http://your-ip:9000
```

## 🔧 Permanent Configuration

### Add to your shell profile (~/.bashrc, ~/.zshrc)
```bash
export LAZARUS_PORT=8888
export LAZARUS_HOST=127.0.0.1
```

### Or create a .env file
```bash
echo "LAZARUS_PORT=8888" >> .env
echo "LAZARUS_HOST=127.0.0.1" >> .env
```

## 🎯 Common Use Cases

### Development (Local Access Only)
```bash
export LAZARUS_PORT=3000
export LAZARUS_HOST=127.0.0.1
python3 -m web.server
```

### Network Access (Multiple Devices)
```bash
export LAZARUS_PORT=8080
export LAZARUS_HOST=0.0.0.0
python3 -m web.server
# Access from other devices: http://your-computer-ip:8080
```

### Production (Standard HTTP Port)
```bash
export LAZARUS_PORT=80
export LAZARUS_HOST=0.0.0.0
python3 -m web.server
# Access: http://your-domain.com
```

## 🛠️ Troubleshooting

### Port Already in Use
```bash
# Find what's using the port
sudo lsof -i :6666

# Kill the process
sudo kill -9 <PID>

# Or choose a different port
export LAZARUS_PORT=7777
```

### Permission Denied (Ports < 1024)
```bash
# For ports 80, 443, etc. you need sudo
sudo LAZARUS_PORT=80 python3 -m web.server

# Or use a higher port
export LAZARUS_PORT=8080
```

### Firewall Issues
```bash
# Allow port through firewall (Ubuntu/Debian)
sudo ufw allow 6666

# Or for specific IP
sudo ufw allow from 192.168.1.100 to any port 6666
```

## 🌐 Network Configuration Examples

### Local Network Access
```bash
# Allow access from local network
export LAZARUS_HOST=0.0.0.0
export LAZARUS_PORT=8888
python3 -m web.server

# Other devices can access via:
# http://your-computer-ip:8888
# Find your IP: ip addr show or ifconfig
```

### Docker/Container Usage
```bash
# Map container port to host port
docker run -p 8080:6666 your-lazarus-image

# Access: http://localhost:8080
```

### Reverse Proxy (Nginx)
```nginx
location /lazarus/ {
    proxy_pass http://127.0.0.1:6666/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 🔍 Port Discovery

### Find Available Ports
```bash
# Check if port is available
netstat -tuln | grep :6666

# Or using ss
ss -tuln | grep :6666

# Find random available port
python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"
```

### Test Port Accessibility
```bash
# From local machine
curl http://localhost:6666/status

# From another machine
curl http://server-ip:6666/status
```

## 📊 Default Ports Reference

| Port | Purpose | Security | Notes |
|------|---------|----------|-------|
| 6666 | Default Lazarus | Medium | Easy to remember |
| 3000 | Development | High | Common dev port |
| 8080 | Alternative | Medium | Common alternative |
| 8888 | Alternative | Medium | Easy to remember |
| 80 | HTTP | Low | Requires root/sudo |
| 443 | HTTPS | Low | Requires SSL setup |

## ⚠️ Security Notes

1. **Ports below 1024** require root privileges
2. **0.0.0.0** binds to all interfaces (network accessible)
3. **127.0.0.1** binds to localhost only (more secure)
4. Use **firewall rules** to restrict access
5. Consider **SSL/TLS** for production use

## 🚀 Quick Reference

```bash
# Most common configurations:

# Development (local only)
LAZARUS_PORT=3000 LAZARUS_HOST=127.0.0.1 python3 -m web.server

# Network access
LAZARUS_PORT=8080 LAZARUS_HOST=0.0.0.0 python3 -m web.server

# Production-like
LAZARUS_PORT=8888 LAZARUS_HOST=0.0.0.0 python3 -m web.server
```

The dashboard automatically adapts to whatever port you choose - no code changes needed!