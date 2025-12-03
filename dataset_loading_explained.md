# How Datasets are Loaded in Flotilla

## Overview
Datasets in Flotilla are loaded at different stages for both **clients** (for training) and **server** (for validation). The loading happens in multiple phases: discovery, path resolution, and actual data loading into memory.

---

## 📁 Dataset Directory Structure

### Client-Side Training Data
```
src/data/                           # Base directory (from config)
└── CIFAR10_IID/                    # Dataset folder
    ├── train_data.pth              # PyTorch dataset file
    └── train_dataset_config.yaml   # Dataset metadata
```

### Server-Side Validation Data
```
val_data/                           # Base directory (from config)
└── <dataset_name>/                 # Dataset folder
    ├── val_data.pth                # PyTorch validation dataset
    └── dataset_config.yaml         # Dataset metadata
```

---

## 🔄 Dataset Loading Flow

### **PHASE 1: Configuration Loading**

#### Client Configuration
**File**: `config/client_config.yaml` (line 16)
```yaml
dataset_config:
  datasets_dir_path: src/data    # Where to find training datasets
```

#### Server Configuration
**File**: `config/server_config.yaml` (line 24)
```yaml
validation_data_dir_path: ./val_data    # Where to find validation datasets
```

---

### **PHASE 2: Dataset Discovery (Startup)**

#### Client-Side Discovery
**Location**: `src/client/client_manager.py` (lines 82-84)

```python
# Get available datasets and models
self.dataset_details, self.dataset_paths = get_available_datasets(
    self.datasets_dir_path  # "src/data"
)
```

**What happens:**
1. Scans the `src/data` directory for subdirectories
2. Each subdirectory is treated as a dataset
3. Reads `train_dataset_config.yaml` from each dataset folder
4. Returns two dictionaries:
   - `dataset_details`: Metadata about each dataset
   - `dataset_paths`: Full paths to the `.pth` files

#### Server-Side Discovery
**Location**: `src/server/server_session_manager.py` (lines 47-48)

```python
validation_data_dir_path = server_config["validation_data_dir_path"]
self.dataset_available = get_available_datasets(validation_data_dir_path)
```

**What happens:**
1. Scans the `val_data` directory for subdirectories
2. Reads `dataset_config.yaml` from each dataset folder
3. Returns dictionary with dataset metadata and paths

---

### **PHASE 3: Dataset Discovery Implementation**

#### Client Implementation
**File**: `src/client/client_file_manager.py` (lines 108-135)

```python
def get_available_datasets(path: str) -> list:
    """Function that returns a list of all datasets present in data directory."""
    
    available_datasets_dir = list()
    available_datasets = dict()
    available_datasets_path = dict()
    
    if os.path.isdir(path):
        # Get all subdirectories in the data folder
        available_datasets_dir = [f.name for f in os.scandir(path) if f.is_dir()]
        
        for dataset in available_datasets_dir:
            # Read the dataset config file
            with open(os.path.join(path, dataset, "train_dataset_config.yaml")) as file:
                try:
                    dataset_config = yaml.safe_load(file)
                except yaml.YAMLError as err:
                    print(err)
            
            # Store the full path to the .pth file
            available_datasets_path[dataset] = os.path.join(
                path, dataset, dataset_config["dataset_details"]["data_filename"]
            )
            
            # Remove data_filename from config and store metadata
            del dataset_config["dataset_details"]["data_filename"]
            available_datasets[dataset] = dataset_config

    return available_datasets, available_datasets_path
```

**Returns:**
- `available_datasets`: `{"CIFAR10_IID": {dataset_details: {...}, metadata: {...}}}`
- `available_datasets_path`: `{"CIFAR10_IID": "src/data/CIFAR10_IID/train_data.pth"}`

#### Server Implementation
**File**: `src/server/server_file_manager.py` (lines 86-107)

```python
def get_available_datasets(path: str) -> dict:
    """Function that returns a list of all datasets present in data directory."""
    
    available_datasets_dir = list()
    available_datasets = dict()
    
    if os.path.isdir(path):
        available_datasets_dir = [f.name for f in os.scandir(path) if f.is_dir()]
        
        for dataset in available_datasets_dir:
            with open(os.path.join(path, dataset, "dataset_config.yaml")) as file:
                try:
                    dataset_config = yaml.safe_load(file)
                except yaml.YAMLError as err:
                    print(err)
            
            available_datasets[dataset] = dataset_config
            # Store full path in the config
            available_datasets[dataset]["dataset_details"]["data_filename"] = os.path.join(
                path, dataset, dataset_config["dataset_details"]["data_filename"]
            )

    return available_datasets
```

---

### **PHASE 4: Actual Dataset Loading (During Training/Validation)**

#### When Dataset is Loaded into Memory

Datasets are **NOT** loaded during startup. They are loaded **on-demand** when:
- **Benchmark** is requested
- **Training** round starts
- **Validation** round starts

#### Loading Location
**File**: `src/client/client.py`

**Three entry points:**
1. **Benchmark()** (lines 88-102)
2. **Train()** (lines 181-198)
3. **Validate()** (lines 271-288)

All three use the same pattern:

```python
# Get the dataset path for the requested dataset_id
dataset_path: str = self.dataset_paths[dataset_id]  # e.g., "src/data/CIFAR10_IID/train_data.pth"

# Check if using custom or default dataloader
if use_custom_dataloader:
    # Load custom dataloader from model directory
    DataLoader = get_model_class(
        path=self.temp_dir_path,
        model_id=model_id,
        class_name="CustomDataLoader",
    )()
    train_loader, test_loader = DataLoader.get_train_test_dataset_loaders(
        batch_size=batch_size,
        dataset_path=dataset_path,
        args=custom_dataloader_args,
    )
else:
    # Use default dataloader
    train_loader, test_loader = self.dataloader.get_train_test_dataset_loaders(
        batch_size=batch_size, 
        dataset_path=dataset_path
    )
```

---

### **PHASE 5: Default DataLoader Implementation**

**File**: `src/client/client_dataset_loader.py` (lines 31-62)

```python
def get_train_test_dataset_loaders(self, batch_size=16, dataset_path=None):
    # THIS IS WHERE THE ACTUAL LOADING HAPPENS!
    dataset = torch.load(dataset_path, weights_only=False).dataset
    
    dataset_len = len(dataset)
    
    # Split dataset: 95% training, 5% testing
    split_idx = math.floor(0.95 * dataset_len)
    
    train_dataset = torch.utils.data.Subset(dataset, list(range(0, split_idx)))
    test_dataset = torch.utils.data.Subset(dataset, list(range(split_idx, dataset_len)))
    
    print(
        "client_dataset_loader.get_train_test_loader:: dataset size - ",
        len(train_dataset),
        len(test_dataset),
    )
    
    # Create PyTorch DataLoaders
    train_loader = torch.utils.data.DataLoader(
        train_dataset, shuffle=True, batch_size=batch_size
    )
    test_loader = torch.utils.data.DataLoader(
        test_dataset, shuffle=True, batch_size=batch_size
    )
    
    print(
        "client_dataset_loader.get_train_test_loader:: dataloader size - ",
        len(train_loader),
        len(test_loader),
    )
    
    return train_loader, test_loader
```

**Key Line:**
```python
dataset = torch.load(dataset_path, weights_only=False).dataset
```
This loads the `.pth` file into memory using PyTorch's `torch.load()`.

---

## 📊 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ STARTUP PHASE                                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. flo_client.py starts                                    │
│    ↓                                                        │
│ 2. Loads config/client_config.yaml                         │
│    - datasets_dir_path: "src/data"                         │
│    ↓                                                        │
│ 3. ClientManager.__init__()                                │
│    ↓                                                        │
│ 4. get_available_datasets("src/data")                      │
│    - Scans src/data/ for subdirectories                    │
│    - Reads train_dataset_config.yaml from each             │
│    - Returns dataset_paths dict                            │
│    ↓                                                        │
│ 5. Stores in self.dataset_paths                            │
│    {"CIFAR10_IID": "src/data/CIFAR10_IID/train_data.pth"}  │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ RUNTIME PHASE (When Training/Validation Requested)         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. Server sends Train/Validate request via gRPC            │
│    - Includes: dataset_id, batch_size, etc.                │
│    ↓                                                        │
│ 2. Client.Train() or Client.Validate() called              │
│    ↓                                                        │
│ 3. Get dataset path from stored dict                       │
│    dataset_path = self.dataset_paths[dataset_id]           │
│    ↓                                                        │
│ 4. Call DataLoader.get_train_test_dataset_loaders()        │
│    ↓                                                        │
│ 5. torch.load(dataset_path) ← ACTUAL LOADING HERE!         │
│    - Loads .pth file into memory                           │
│    - Creates PyTorch Dataset object                        │
│    ↓                                                        │
│ 6. Split into train/test (95%/5%)                          │
│    ↓                                                        │
│ 7. Create PyTorch DataLoaders                              │
│    - Handles batching, shuffling                           │
│    ↓                                                        │
│ 8. Return train_loader, test_loader                        │
│    ↓                                                        │
│ 9. Pass to ClientTrainer.train_model()                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Points

### 1. **Two-Stage Loading**
- **Discovery** (startup): Scans directories, reads configs, stores paths
- **Loading** (runtime): Actually loads `.pth` files into memory when needed

### 2. **Lazy Loading**
- Datasets are **NOT** loaded at startup
- Only loaded when training/validation is requested
- Saves memory when multiple datasets are available

### 3. **Dataset Caching**
- `Client` class stores `self.train_loader` and `self.test_loader`
- Reuses them if the same `dataset_id` is requested again
- Reloads only if `dataset_id` changes

### 4. **Configuration Sources**
- **Client datasets**: `config/client_config.yaml` → `dataset_config.datasets_dir_path`
- **Server validation**: `config/server_config.yaml` → `validation_data_dir_path`

### 5. **File Format**
- Datasets are stored as PyTorch `.pth` files
- Created using `torch.save()`
- Loaded using `torch.load()`

### 6. **Dataset Metadata**
Each dataset folder contains a YAML config file:
```yaml
dataset_details:
  data_filename: train_data.pth
  dataset_id: CIFAR10_IID
  dataset_tags:
    - IMAGE
  suitable_models:
    - CNN
metadata:
  label_distribution:
    '0': 0.1
    '1': 0.1
    # ... etc
  num_items: 240
```

---

## 🎯 Summary

**Where datasets are loaded:**

1. **Path Discovery**: `client_manager.py` → `get_available_datasets()` (startup)
2. **Actual Loading**: `client_dataset_loader.py` → `torch.load()` (on-demand)

**When datasets are loaded:**

1. **Discovery**: When `ClientManager` initializes
2. **Loading**: When `Benchmark()`, `Train()`, or `Validate()` is called

**What gets loaded:**

- PyTorch `.pth` files containing serialized dataset objects
- Split into 95% training / 5% testing
- Wrapped in PyTorch `DataLoader` for batching

The key insight is that **dataset discovery** happens at startup, but **actual data loading** is deferred until needed, making the system memory-efficient.
