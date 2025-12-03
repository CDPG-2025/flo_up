# Multi-Machine Code Changes Summary

This document outlines all the code changes made to enable Flotilla to run with the server and clients on different machines.

---

## 🎯 Overview

The original Flotilla codebase was designed for single-machine deployment (localhost). To enable multi-machine deployment, we made strategic changes to:

1. **Client entry point** (`flo_client.py`)
2. **Server entry point** (`flo_server.py`)
3. **Configuration files** (server and client configs)
4. **IP address detection** (client utilities)

---

## 📝 Detailed Changes

### 1. **Client Entry Point** (`src/flo_client.py`)

#### **Added Command-Line Arguments**

**Lines 31-42**: Added two new arguments to support multi-machine and multi-client scenarios:

```python
parser.add_argument(
    "--client-num",
    type=int,
    default=1,
    help="Client number for running multiple clients (default: 1). Creates separate temp directories and unique ports.",
)
parser.add_argument(
    "--server-ip",
    type=str,
    default="localhost",
    help="IP address of the Flotilla Server (MQTT Broker). Default: localhost",
)
```

**Purpose**:
- `--client-num`: Allows multiple clients to run without conflicts (unique temp dirs, MQTT names, ports)
- `--server-ip`: Tells the client where the server is located (critical for multi-machine)

---

#### **Display Client IP Address**

**Lines 47-57**: Added code to detect and display the client's IP address:

```python
import socket
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        client_ip = s.getsockname()[0]
        print(f"\n{'='*60}")
        print(f"CLIENT IP ADDRESS: {client_ip}")
        print(f"{'='*60}\n")
except Exception:
    print("\n[WARNING] Could not determine Client IP.")
```

**Purpose**: Helps users verify which machine/IP the client is running on.

---

#### **Dynamic Configuration Overrides**

**Lines 62-93**: Modified the client configuration at runtime based on arguments:

##### **A. Unique Temp Directory** (Lines 62-66)
```python
base_temp_dir = client_config["general_config"]["temp_dir_path"]
temp_dir_path = os.path.join(f"{base_temp_dir}_{client_num}")
client_config["general_config"]["temp_dir_path"] = temp_dir_path
```

**Purpose**: Each client gets its own temp directory (`temp_1`, `temp_2`, etc.) to avoid file conflicts.

##### **B. Unique MQTT Client Name** (Lines 68-71)
```python
original_client_name = client_config["comm_config"]["mqtt"]["client_name"]
client_config["comm_config"]["mqtt"]["client_name"] = f"{original_client_name}_{client_num}"
```

**Purpose**: Each client needs a unique MQTT identifier to avoid connection conflicts.

##### **C. Unique gRPC Ports** (Lines 73-85)
```python
port_offset = (client_num - 1) * 2
original_sync_port = client_config["comm_config"]["grpc"]["sync_port"]
original_async_port = client_config["comm_config"]["grpc"]["async_port"]

client_config["comm_config"]["grpc"]["sync_port"] = original_sync_port + port_offset
client_config["comm_config"]["grpc"]["async_port"] = original_async_port + port_offset
```

**Purpose**: Each client needs unique gRPC ports:
- Client 1: 50053, 50054
- Client 2: 50055, 50056
- Client 3: 50057, 50058

##### **D. Override MQTT Broker IP** (Lines 87-93)
```python
server_ip = args.server_ip
if server_ip != "localhost":
    client_config["comm_config"]["mqtt"]["mqtt_broker"] = server_ip
    print(f"[FLOW] flo_client.py: Overriding MQTT Broker IP to: {server_ip}")
else:
    print(f"[FLOW] flo_client.py: Using default MQTT Broker IP: {client_config['comm_config']['mqtt']['mqtt_broker']}")
```

**Purpose**: **This is the KEY change for multi-machine!** It overrides the MQTT broker address to point to the server machine instead of localhost.

---

### 2. **Server Entry Point** (`src/flo_server.py`)

#### **Display Server IP Address**

**Lines 113-125**: Added code to detect and display the server's IP address:

```python
import socket
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        print(f"\n{'='*60}")
        print(f"SERVER IP ADDRESS: {server_ip}")
        print(f"Clients should connect using: --server-ip {server_ip}")
        print(f"{'='*60}\n")
except Exception:
    print("\n[WARNING] Could not determine public IP. Using localhost/127.0.0.1")
```

**Purpose**: 
- Shows the server's IP address when it starts
- Tells users exactly what command to use on client machines
- Critical for multi-machine setup

---

### 3. **Server Configuration** (`config/server_config.yaml`)

#### **REST API Binding**

**Line 17**: Changed REST API hostname to bind to all interfaces:

```yaml
restful:
  rest_hostname: 0.0.0.0  # Was likely "localhost" before
  rest_port: 12345
```

**Purpose**: 
- `0.0.0.0` means "listen on all network interfaces"
- Allows connections from remote machines
- If it was `localhost` or `127.0.0.1`, only local connections would work

---

### 4. **Client IP Detection** (`src/client/utils/ip.py`)

#### **Smart IP Detection Function**

**Lines 3-19**: The `get_ip_address()` function was designed to intelligently detect the client's IP:

```python
def get_ip_address(target_host: str = "google.com", target_port: int = 80) -> str:
    """Return the local IP address used to reach the given target.
    If the connection fails, fall back to 127.0.0.1.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((target_host, target_port))
            return s.getsockname()[0]
    except Exception:
        # Fallback to checking internet connectivity or localhost
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
```

**Purpose**:
- Detects the actual IP address the client will use to communicate
- First tries to connect to the MQTT broker (server) to get the correct interface
- Falls back to Google DNS (8.8.8.8) if that fails
- Returns localhost as last resort

**Why this matters**: A machine might have multiple network interfaces (WiFi, Ethernet, VPN, Docker networks). This ensures we get the RIGHT IP that can reach the server.

---

#### **Usage in Client Manager**

**In `src/client/client_manager.py` (Line 56)**:

```python
self.ip: str = get_ip_address_docker() if ev else get_ip_address(
    client_config["comm_config"]["mqtt"]["mqtt_broker"], 
    client_config["comm_config"]["mqtt"]["mqtt_broker_port"]
)
```

**Purpose**: When the client starts, it determines its IP by trying to connect to the MQTT broker. This ensures the gRPC server advertises the correct IP address to the server.

---

## 🔑 Key Architectural Decisions

### 1. **Runtime Configuration Override**
Instead of requiring users to manually edit YAML files, we use command-line arguments that override the configuration at runtime. This makes it much easier to:
- Run multiple clients on the same machine
- Switch between localhost and multi-machine deployments
- Avoid configuration file conflicts

### 2. **Automatic IP Detection**
Both server and client automatically detect and display their IP addresses. This:
- Reduces user error
- Makes setup instructions clearer
- Helps with debugging connectivity issues

### 3. **Server Binds to All Interfaces**
The server uses `0.0.0.0` for the REST API, which means:
- It accepts connections from any network interface
- Works for both localhost and remote connections
- No need to change config for different deployment scenarios

### 4. **Client Uses Server IP for IP Detection**
The client's IP detection function connects to the MQTT broker (server) to determine which local IP to use. This ensures:
- The client advertises the correct IP to the server
- gRPC communication works properly
- Multi-homed machines (multiple IPs) work correctly

---

## 📊 Before vs After Comparison

### **Before (Single Machine Only)**

```bash
# Server
python src/flo_server.py

# Client (same machine)
python src/flo_client.py

# Problem: Everything hardcoded to localhost
# - Client config: mqtt_broker: localhost
# - Server config: rest_hostname: localhost (maybe)
# - No way to specify different machine
```

### **After (Multi-Machine Support)**

```bash
# Server Machine (192.168.1.100)
python src/flo_server.py
# Output: "SERVER IP ADDRESS: 192.168.1.100"
# Output: "Clients should connect using: --server-ip 192.168.1.100"

# Client Machine (192.168.1.101)
python src/flo_client.py --server-ip 192.168.1.100 --client-num 1
# Output: "CLIENT IP ADDRESS: 192.168.1.101"
# Output: "Overriding MQTT Broker IP to: 192.168.1.100"

# Benefits:
# - No config file editing required
# - Clear IP addresses displayed
# - Works across machines
# - Multiple clients supported
```

---

## 🧪 What Makes It Work

### **Communication Flow**

1. **Server starts**:
   - Binds REST API to `0.0.0.0:12345` (all interfaces)
   - Connects to local MQTT broker at `localhost:1884`
   - Displays its IP address (e.g., `192.168.1.100`)

2. **Client starts with `--server-ip 192.168.1.100`**:
   - Overrides MQTT broker config to `192.168.1.100:1884`
   - Detects its own IP by connecting to `192.168.1.100:1884`
   - Starts gRPC server on detected IP (e.g., `192.168.1.101:50053`)
   - Sends registration to server via MQTT with gRPC address

3. **Server receives client registration**:
   - Gets client's gRPC address (e.g., `192.168.1.101:50053`)
   - Can now send training tasks to client via gRPC
   - Client can send updates back

4. **Session starts**:
   - Connects to server REST API
   - Server coordinates training across all registered clients
   - Each client trains locally and sends updates
   - Server aggregates and validates

---

## 🎯 Summary of Changes

| Component | Change | Purpose |
|-----------|--------|---------|
| `flo_client.py` | Added `--server-ip` argument | Tell client where server is |
| `flo_client.py` | Added `--client-num` argument | Support multiple clients |
| `flo_client.py` | Runtime config override for MQTT broker | Point to remote server |
| `flo_client.py` | Runtime config override for temp dir | Unique storage per client |
| `flo_client.py` | Runtime config override for MQTT name | Unique identity per client |
| `flo_client.py` | Runtime config override for gRPC ports | Avoid port conflicts |
| `flo_client.py` | Display client IP | User visibility |
| `flo_server.py` | Display server IP | User visibility |
| `server_config.yaml` | REST API binds to `0.0.0.0` | Accept remote connections |
| `client/utils/ip.py` | Smart IP detection | Get correct network interface |

---

## ✅ Result

With these changes, Flotilla now supports:

- ✅ **Single machine deployment** (original use case still works)
- ✅ **Multi-machine deployment** (server and clients on different machines)
- ✅ **Multiple clients on same machine** (for testing)
- ✅ **Mixed deployment** (some clients local, some remote)
- ✅ **Easy configuration** (command-line args instead of file editing)
- ✅ **Clear visibility** (IP addresses displayed on startup)
- ✅ **Automatic IP detection** (no manual configuration needed)

---

**The core insight**: By adding runtime configuration overrides via command-line arguments and automatic IP detection, we made Flotilla flexible enough to work in any deployment scenario without requiring users to manually edit configuration files.
