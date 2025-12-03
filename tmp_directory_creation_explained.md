# How `tmp` Directory is Created in Flotilla

## Overview
The temporary directory (`tmp`) in Flotilla is created through a multi-step process that ensures each client has its own isolated workspace for storing temporary files, model caches, and client information.

## Creation Flow

### 1. **Configuration Loading** (`flo_client.py`)
**Location**: `/home/snowden/Desktop/flotilla/src/flo_client.py` (lines 60-66)

```python
# Load base configuration
client_config = OpenYaML(os.path.join("config", "client_config.yaml"))

# Get base temp directory from config
base_temp_dir = client_config["general_config"]["temp_dir_path"]  # Default: "temp"

# Create unique temp directory for this client instance
temp_dir_path = os.path.join(f"{base_temp_dir}_{client_num}")
client_config["general_config"]["temp_dir_path"] = temp_dir_path
```

**What happens here:**
- Reads the base temp directory name from `config/client_config.yaml` (default: `"temp"`)
- Appends the client number to create a unique directory name
- For example:
  - Client 1 → `temp_1`
  - Client 2 → `temp_2`
  - Client 3 → `temp_3`

### 2. **Client Info Generation** (`flo_client.py`)
**Location**: `/home/snowden/Desktop/flotilla/src/flo_client.py` (lines 96-103)

```python
# Check if client info already exists
if os.path.isfile(os.path.join(temp_dir_path, "client_info.yaml")):
    # Load existing client info
    client_info = OpenYaML(os.path.join(temp_dir_path, "client_info.yaml"))
    client_id: str = client_info["client_id"]
else:
    # Generate new client ID and create directory
    client_id: str = str(uuid.uuid4())
    client_info = generate_client_info(client_id, temp_dir_path)
```

**What happens here:**
- Checks if the temp directory already exists with a `client_info.yaml` file
- If it exists: loads the existing client information (preserves client identity)
- If it doesn't exist: generates a new UUID and calls `generate_client_info()`

### 3. **Physical Directory Creation** (`client_info.py`)
**Location**: `/home/snowden/Desktop/flotilla/src/client/utils/client_info.py` (line 7)

```python
def generate_client_info(client_id, path):
    # THIS IS WHERE THE DIRECTORY IS ACTUALLY CREATED!
    os.makedirs(path, exist_ok=True)
    
    # Create client_info.yaml file
    client_info_path = os.path.join(path, "client_info.yaml")
    client_info: dict = {"client_id": client_id, "benchmark_info": dict()}
    
    # Write client info to file
    with open(client_info_path, "w") as file:
        yaml.dump(client_info, file)
    
    return client_info
```

**What happens here:**
- `os.makedirs(path, exist_ok=True)` creates the directory (and any parent directories if needed)
- `exist_ok=True` means it won't error if the directory already exists
- Creates a `client_info.yaml` file inside the directory with the client's UUID

### 4. **Directory Setup in ClientManager** (`client_manager.py`)
**Location**: `/home/snowden/Desktop/flotilla/src/client/client_manager.py` (lines 76-78)

```python
# Store temp directory path
self.temp_dir_path = client_config["general_config"]["temp_dir_path"]

# Ensure directory exists
setup_dir(dir_path=self.temp_dir_path)
```

**What happens here:**
- The `ClientManager` also calls `setup_dir()` to ensure the directory exists
- This is a safety check in case the directory wasn't created earlier

### 5. **Setup Directory Function** (`client_file_manager.py`)
**Location**: `/home/snowden/Desktop/flotilla/src/client/client_file_manager.py` (lines 39-49)

```python
def setup_dir(dir_path: str) -> None:
    """Function that creates a directory at "dir_path", if it does not exist already"""
    try:
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)  # Creates single directory
    except Exception as e:
        print(f"Exception from setup_dir: {e}")
```

**What happens here:**
- Checks if the directory exists
- If not, creates it using `os.mkdir()` (only creates the final directory, not parents)
- Handles any exceptions gracefully

## Directory Structure

Once created, the temp directory has the following structure:

```
temp_1/                          # Unique temp directory for client 1
├── client_info.yaml             # Client UUID and benchmark info
└── model_cache/                 # Created later when models are received
    └── <model_id>/              # Separate folder for each model
        ├── __init__.py
        └── <model_files>
```

## Key Points

1. **Multiple Clients Support**: Each client gets its own temp directory (`temp_1`, `temp_2`, etc.) to avoid conflicts when running multiple clients simultaneously.

2. **Two Creation Points**:
   - **First**: `generate_client_info()` uses `os.makedirs()` (creates parent directories if needed)
   - **Second**: `setup_dir()` uses `os.mkdir()` (only creates the final directory)

3. **Persistence**: If the temp directory already exists from a previous run, the client reuses it and loads the existing `client_info.yaml` to maintain the same client ID.

4. **Configuration Source**: The base temp directory name comes from:
   - File: `config/client_config.yaml`
   - Key: `general_config.temp_dir_path`
   - Default value: `"temp"`

5. **Cleanup**: The temp directory can be cleaned up on exit based on the `cleanup_temp_on_exit` configuration option.

## Example Execution Flow

For a client started with `--client-num 2`:

1. Reads `"temp"` from config
2. Creates path `"temp_2"`
3. Checks if `temp_2/client_info.yaml` exists
4. If not, calls `generate_client_info()`:
   - Runs `os.makedirs("temp_2", exist_ok=True)` → **Directory created here!**
   - Creates `temp_2/client_info.yaml` with new UUID
5. `ClientManager` calls `setup_dir("temp_2")`:
   - Checks if directory exists (it does now)
   - Does nothing (directory already exists)
6. Later, when models are received, `model_cache/` subdirectory is created inside `temp_2/`

## Summary

The `tmp` (or `temp_X`) directory is created primarily by the `generate_client_info()` function using `os.makedirs()`, which is called from `flo_client.py` when a new client is started and no existing client info is found. The directory name is derived from the configuration file and appended with the client number to ensure uniqueness across multiple client instances.
