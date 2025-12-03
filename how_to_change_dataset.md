# How to Change/Add Datasets in Flotilla

This guide explains everything you need to do to change or add a new dataset in Flotilla.

---

## 📋 Table of Contents
1. [Quick Overview](#quick-overview)
2. [Option 1: Use Existing Dataset (CIFAR10, MNIST, etc.)](#option-1-use-existing-dataset)
3. [Option 2: Create Custom Dataset](#option-2-create-custom-dataset)
4. [Option 3: Use Synthetic Dataset](#option-3-use-synthetic-dataset)
5. [Configuration Changes](#configuration-changes)
6. [Troubleshooting](#troubleshooting)

---

## Quick Overview

To change datasets in Flotilla, you need to:

1. ✅ **Create dataset files** in the correct directory structure
2. ✅ **Create YAML config files** for the dataset
3. ✅ **Update server/client configs** (if needed)
4. ✅ **Update session config** to use the new dataset

**Key Directories:**
- **Client training data**: `src/data/<dataset_name>/`
- **Server validation data**: `val_data/<dataset_name>/`

---

## Option 1: Use Existing Dataset (CIFAR10, MNIST, etc.)

Flotilla has built-in support for popular datasets. Use the partitioner utility to create them.

### Step 1: Choose Your Dataset

Supported datasets:
- `MNIST`
- `EMNIST`
- `CIFAR10` ✅ (Currently used)
- `CIFAR100`
- `ImageNet`
- `SYNTHETIC`

### Step 2: Run the Partitioner

The partitioner creates dataset partitions for federated learning.

**Location**: `src/utils/partitioner.py`

**Example: Create MNIST Dataset**

```bash
cd src
python utils/partitioner.py \
    --dataset MNIST \
    --partition_type iid \
    --num_clients 5 \
    --output_dir data
```

**Partition Types Available:**
- `iid`: Independent and Identically Distributed (balanced)
- `dirichlet`: Non-IID using Dirichlet distribution
- `limit_label`: Limit number of classes per client
- `equal_partition`: Equal samples per client

**Common Arguments:**
```bash
--dataset MNIST              # Dataset name
--partition_type iid         # How to partition
--num_clients 5              # Number of client partitions
--output_dir data            # Output directory
--alpha 0.5                  # For dirichlet (lower = more non-IID)
--min_samples 100            # Minimum samples per client
```

### Step 3: Verify Dataset Structure

After running the partitioner, you should have:

```
src/data/
└── MNIST_IID/                      # Dataset folder
    ├── train_data.pth              # PyTorch dataset file
    └── train_dataset_config.yaml   # Metadata
```

### Step 4: Create Validation Dataset

For server-side validation:

```bash
cd src
python utils/partitioner.py \
    --dataset MNIST \
    --partition_type test \
    --output_dir ../val_data
```

This creates:
```
val_data/
└── MNIST/
    ├── test.pth
    └── dataset_config.yaml
```

---

## Option 2: Create Custom Dataset

If you have your own dataset, follow these steps:

### Step 1: Prepare Your Data

Convert your data to PyTorch format:

```python
import torch
from torch.utils.data import TensorDataset, DataLoader

# Example: Your custom data
X_train = torch.tensor(your_training_data)  # Shape: [num_samples, ...]
y_train = torch.tensor(your_training_labels)  # Shape: [num_samples]

# Create TensorDataset
train_dataset = TensorDataset(X_train, y_train)

# Create DataLoader
train_loader = DataLoader(train_dataset, batch_size=1, shuffle=False)
```

### Step 2: Create Directory Structure

```bash
mkdir -p src/data/MY_CUSTOM_DATASET
mkdir -p val_data/MY_CUSTOM_DATASET
```

### Step 3: Save Training Data

```python
import torch

# Save the DataLoader
torch.save(train_loader, 'src/data/MY_CUSTOM_DATASET/train_data.pth')
```

### Step 4: Create Training Config YAML

Create `src/data/MY_CUSTOM_DATASET/train_dataset_config.yaml`:

```yaml
dataset_details:
  data_filename: train_data.pth
  dataset_id: MY_CUSTOM_DATASET
  dataset_tags:
    - IMAGE              # or TEXT, TABULAR, etc.
    - CUSTOM
  suitable_models:
    - CNN                # Models that work with this dataset
    - LeNet5

metadata:
  label_distribution:    # Distribution of labels
    '0': 0.1
    '1': 0.15
    '2': 0.2
    # ... add all your classes
  num_items: 5000        # Total number of samples
```

### Step 5: Save Validation Data

```python
# Create validation dataset
val_dataset = TensorDataset(X_val, y_val)
val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False)

# Save
torch.save(val_loader, 'val_data/MY_CUSTOM_DATASET/test.pth')
```

### Step 6: Create Validation Config YAML

Create `val_data/MY_CUSTOM_DATASET/dataset_config.yaml`:

```yaml
dataset_details:
  data_filename: test.pth
  dataset_id: MY_CUSTOM_DATASET
  dataset_tags:
    - IMAGE
    - CUSTOM
  suitable_models:
    - CNN
    - LeNet5

metadata:
  label_distribution:
    '0': 0.1
    '1': 0.15
    # ... etc
  num_items: 1000
```

### Step 7: Complete Python Script Example

Here's a complete script to create a custom dataset:

```python
"""
create_my_dataset.py - Script to create custom dataset for Flotilla
"""
import os
import torch
import yaml
from torch.utils.data import TensorDataset, DataLoader
from collections import Counter

def create_custom_dataset():
    # 1. Load your data (replace with your actual data loading)
    # Example: Random data for demonstration
    num_train = 5000
    num_val = 1000
    num_classes = 10
    
    X_train = torch.randn(num_train, 3, 32, 32)  # Example: 32x32 RGB images
    y_train = torch.randint(0, num_classes, (num_train,))
    
    X_val = torch.randn(num_val, 3, 32, 32)
    y_val = torch.randint(0, num_classes, (num_val,))
    
    # 2. Create datasets
    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)
    
    # 3. Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=1, shuffle=False)
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False)
    
    # 4. Create directories
    dataset_name = "MY_CUSTOM_DATASET"
    train_dir = f"src/data/{dataset_name}"
    val_dir = f"val_data/{dataset_name}"
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(val_dir, exist_ok=True)
    
    # 5. Save data files
    torch.save(train_loader, f"{train_dir}/train_data.pth")
    torch.save(val_loader, f"{val_dir}/test.pth")
    print(f"✓ Saved data files")
    
    # 6. Calculate label distributions
    train_label_counts = Counter(y_train.tolist())
    train_label_dist = {str(k): v / num_train for k, v in train_label_counts.items()}
    
    val_label_counts = Counter(y_val.tolist())
    val_label_dist = {str(k): v / num_val for k, v in val_label_counts.items()}
    
    # 7. Create training config
    train_config = {
        "dataset_details": {
            "data_filename": "train_data.pth",
            "dataset_id": dataset_name,
            "dataset_tags": ["IMAGE", "CUSTOM"],
            "suitable_models": ["CNN", "LeNet5"]
        },
        "metadata": {
            "label_distribution": train_label_dist,
            "num_items": num_train
        }
    }
    
    with open(f"{train_dir}/train_dataset_config.yaml", "w") as f:
        yaml.dump(train_config, f, default_flow_style=False)
    print(f"✓ Created training config")
    
    # 8. Create validation config
    val_config = {
        "dataset_details": {
            "data_filename": "test.pth",
            "dataset_id": dataset_name,
            "dataset_tags": ["IMAGE", "CUSTOM"],
            "suitable_models": ["CNN", "LeNet5"]
        },
        "metadata": {
            "label_distribution": val_label_dist,
            "num_items": num_val
        }
    }
    
    with open(f"{val_dir}/dataset_config.yaml", "w") as f:
        yaml.dump(val_config, f, default_flow_style=False)
    print(f"✓ Created validation config")
    
    print(f"\n✅ Dataset '{dataset_name}' created successfully!")
    print(f"   Training: {train_dir}/")
    print(f"   Validation: {val_dir}/")

if __name__ == "__main__":
    create_custom_dataset()
```

**Run it:**
```bash
cd /home/snowden/Desktop/flotilla
python create_my_dataset.py
```

---

## Option 3: Use Synthetic Dataset

For quick testing, use the built-in synthetic dataset generator.

### Step 1: Run the Generator

```bash
cd src
python create_synthetic_dataset.py
```

This creates:
- `data/SYNTHETIC_IID/` - Training data
- `val_data/SYNTHETIC_IID/` - Validation data

### Step 2: Customize (Optional)

Edit `src/create_synthetic_dataset.py` to change:
- `num_train_samples`: Number of training samples
- `num_test_samples`: Number of validation samples
- `num_classes`: Number of classes
- `image_size`: Image dimensions
- `dataset_name`: Dataset name

---

## Configuration Changes

After creating your dataset, update the configuration files:

### 1. Update Session Config

**File**: `config/flotilla_quicksetup_config.yaml`

```yaml
training_config:
  dataset_id: MY_CUSTOM_DATASET  # ← Change this to your dataset name
  model_id: CNN
  batch_size: 32
  # ... rest of config
```

### 2. Verify Client Config (Usually No Change Needed)

**File**: `config/client_config.yaml`

```yaml
dataset_config:
  datasets_dir_path: src/data  # Should point to your data directory
```

### 3. Verify Server Config (Usually No Change Needed)

**File**: `config/server_config.yaml`

```yaml
validation_data_dir_path: ./val_data  # Should point to validation directory
```

---

## Complete Workflow Example

Let's say you want to switch from CIFAR10 to MNIST:

### Step 1: Create MNIST Dataset

```bash
cd /home/snowden/Desktop/flotilla/src

# Create training data
python utils/partitioner.py \
    --dataset MNIST \
    --partition_type iid \
    --num_clients 3 \
    --output_dir data

# Create validation data (run partitioner for test set)
# Or manually create val_data/MNIST/ with test.pth
```

### Step 2: Verify Directory Structure

```bash
ls -la src/data/MNIST_IID/
# Should show:
# - train_data.pth
# - train_dataset_config.yaml

ls -la val_data/MNIST/
# Should show:
# - test.pth
# - dataset_config.yaml
```

### Step 3: Update Session Config

Edit `config/flotilla_quicksetup_config.yaml`:

```yaml
training_config:
  dataset_id: MNIST_IID  # ← Changed from CIFAR10_IID
  model_id: LeNet5        # ← Use appropriate model for MNIST
  batch_size: 32
  num_epochs: 5
  learning_rate: 0.01
```

### Step 4: Run Flotilla

```bash
# Terminal 1: Start Docker services
docker-compose up

# Terminal 2: Start server
source .venv/bin/activate
python src/flo_server.py

# Terminal 3: Start client
source .venv/bin/activate
python src/flo_client.py

# Terminal 4: Start session
source .venv/bin/activate
python src/flo_session.py
```

---

## Troubleshooting

### Issue 1: "Dataset not found"

**Error**: `KeyError: 'MY_DATASET'`

**Solution**:
1. Check directory exists: `ls src/data/MY_DATASET/`
2. Check config file exists: `ls src/data/MY_DATASET/train_dataset_config.yaml`
3. Verify `dataset_id` in YAML matches folder name

### Issue 2: "Failed to load dataset"

**Error**: `FileNotFoundError` or `torch.load` error

**Solution**:
1. Verify `.pth` file exists and is not corrupted
2. Check `data_filename` in YAML matches actual file name
3. Ensure file was created with `torch.save(dataloader, path)`

### Issue 3: "Dataset ID mismatch"

**Error**: Dataset loads but training fails

**Solution**:
1. Ensure `dataset_id` in session config matches the folder name
2. Check both training and validation datasets have same `dataset_id`

### Issue 4: "Model incompatible with dataset"

**Error**: Shape mismatch or model errors

**Solution**:
1. Verify `suitable_models` in dataset config
2. Ensure model input shape matches dataset shape
3. For MNIST (28x28 grayscale), use LeNet5
4. For CIFAR10 (32x32 RGB), use CNN or AlexNet

### Issue 5: "Validation data not found"

**Error**: Server can't find validation dataset

**Solution**:
1. Create `val_data/<dataset_name>/` directory
2. Add `test.pth` and `dataset_config.yaml`
3. Verify `validation_data_dir_path` in server config

---

## Dataset Requirements Checklist

Before running Flotilla with a new dataset, verify:

- [ ] Training data directory exists: `src/data/<dataset_name>/`
- [ ] Training data file exists: `src/data/<dataset_name>/train_data.pth`
- [ ] Training config exists: `src/data/<dataset_name>/train_dataset_config.yaml`
- [ ] Validation data directory exists: `val_data/<dataset_name>/`
- [ ] Validation data file exists: `val_data/<dataset_name>/test.pth`
- [ ] Validation config exists: `val_data/<dataset_name>/dataset_config.yaml`
- [ ] Session config updated: `dataset_id` in `config/flotilla_quicksetup_config.yaml`
- [ ] Model is compatible with dataset shape
- [ ] YAML files have correct `dataset_id` and `data_filename`

---

## Quick Reference: File Locations

| What | Client (Training) | Server (Validation) |
|------|------------------|---------------------|
| **Directory** | `src/data/<dataset_name>/` | `val_data/<dataset_name>/` |
| **Data File** | `train_data.pth` | `test.pth` |
| **Config File** | `train_dataset_config.yaml` | `dataset_config.yaml` |
| **Config Path** | `config/client_config.yaml` | `config/server_config.yaml` |
| **Config Key** | `dataset_config.datasets_dir_path` | `validation_data_dir_path` |

---

## Summary

**To change dataset:**

1. **Create dataset files** in correct format (`.pth` files)
2. **Create YAML configs** with metadata
3. **Update session config** to use new `dataset_id`
4. **Restart Flotilla** components

**Three ways to create datasets:**
- Use partitioner for standard datasets (MNIST, CIFAR10, etc.)
- Create custom dataset from your own data
- Use synthetic dataset generator for testing

**Key points:**
- Dataset discovery happens at startup
- Actual loading happens on-demand during training
- Both client and server need their respective datasets
- `dataset_id` must match across all configs

Need help? Check the existing `CIFAR10_IID` dataset as a reference example!
