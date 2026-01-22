"""
Create Synthetic Dataset for Flotilla (Corrected)
Generates random synthetic images (1x28x28) and labels for federated learning.
Places files in correct directories for Client (src/data) and Server (src/val_data).
"""
import os
import torch
import yaml
from collections import Counter
from torch.utils.data import TensorDataset, DataLoader
import shutil

def get_dataset_summary(dataloader):
    """Calculate label distribution from dataloader"""
    label_counts = Counter()
    total_items = 0
    
    for _, labels in dataloader:
        if labels.dim() > 0:
            for label in labels:
                label_counts[label.item()] += 1
                total_items += 1
        else:
            label_counts[labels.item()] += 1
            total_items += 1
    
    # Calculate distribution
    label_distribution = {str(k): v / total_items for k, v in label_counts.items()}
    
    return {
        'label_distribution': label_distribution,
        'num_items': total_items
    }

def create_synthetic_dataset(
    dataset_name="SYNTHETIC_CUSTOM",
    num_train_samples=5000,
    num_test_samples=1000,
    num_classes=10,
    image_size=(1, 28, 28), # Modified size for AlexNet/LeNet (Grayscale)
    num_clients=3
):
    print(f"\n{'='*60}")
    print(f"Creating Synthetic Dataset: {dataset_name}")
    print(f"Image size: {image_size}")
    print(f"{'='*60}\n")
    
    # Define directories
    # Note: Running from project root
    base_train_dir = f"src/data/{dataset_name}/train/iid"
    train_root_dir = f"src/data/{dataset_name}"
    
    # Validation data goes to src/val_data (relative to project root)
    base_val_dir = f"src/val_data/{dataset_name}"
    
    # Clean up existing
    if os.path.exists(train_root_dir):
        try:
            shutil.rmtree(train_root_dir)
        except OSError as e:
            print(f"Warning: Could not remove {train_root_dir}: {e}")
    if os.path.exists(base_val_dir):
        try:
            shutil.rmtree(base_val_dir)
        except OSError as e:
            print(f"Warning: Could not remove {base_val_dir}: {e}")
        
    os.makedirs(base_train_dir, exist_ok=True)
    os.makedirs(base_val_dir, exist_ok=True)
    
    # 1. Generate Validation Data
    print("📊 Generating validation data...")
    val_data = torch.randn(num_test_samples, *image_size)
    val_labels = torch.randint(0, num_classes, (num_test_samples,))
    val_data = (val_data - val_data.mean()) / (val_data.std() + 1e-8)
    
    val_dataset = TensorDataset(val_data, val_labels)
    val_loader = DataLoader(val_dataset, batch_size=1, shuffle=False)
    
    # Save validation data
    val_path = os.path.join(base_val_dir, "test.pth")
    torch.save(val_loader, val_path)
    
    # Create validation config (dataset_config.yaml)
    val_summary = get_dataset_summary(val_loader)
    val_config = {
        'dataset_details': {
            'data_filename': 'test.pth',
            'dataset_id': dataset_name,
            'dataset_tags': ['IMAGE', 'SYNTHETIC', 'CUSTOM'],
            'suitable_models': ['AlexNet_class', 'LeNet5', 'CNN', 'FedAT_CNN', 'FedAT_AlexNet']
        },
        'metadata': val_summary
    }
    
    with open(os.path.join(base_val_dir, 'dataset_config.yaml'), 'w') as f:
        yaml.dump(val_config, f, default_flow_style=False)
    
    print(f"✅ Validation data saved to: {val_path}")
    
    # 2. Generate Training Data
    print(f"\n📊 Generating training data for {num_clients} clients...")
    samples_per_client = num_train_samples // num_clients
    
    first_part_path = ""
    
    for client_id in range(num_clients):
        # Generate training data
        train_data = torch.randn(samples_per_client, *image_size)
        train_labels = torch.randint(0, num_classes, (samples_per_client,))
        train_data = (train_data - train_data.mean()) / (train_data.std() + 1e-8)
        
        train_dataset = TensorDataset(train_data, train_labels)
        train_loader = DataLoader(train_dataset, batch_size=1, shuffle=False)
        
        # Directory
        client_dir = os.path.join(base_train_dir, f"part_{client_id}")
        os.makedirs(client_dir, exist_ok=True)
        
        # Save
        train_filename = f"iid_part_{client_id}.pth"
        train_path = os.path.join(client_dir, train_filename)
        torch.save(train_loader, train_path)
        
        if client_id == 0:
            first_part_path = f"train/iid/part_0/{train_filename}"
            
        # Config for partition
        train_summary = get_dataset_summary(train_loader)
        train_config = {
            'dataset_details': {
                'data_filename': train_filename,
                'dataset_id': dataset_name,
                'dataset_tags': ['IMAGE', 'SYNTHETIC', 'CUSTOM'],
                'suitable_models': ['AlexNet_class', 'LeNet5', 'CNN', 'FedAT_CNN', 'FedAT_AlexNet']
            },
            'metadata': train_summary
        }
        with open(os.path.join(client_dir, 'train_dataset_config.yaml'), 'w') as f:
            yaml.dump(train_config, f, default_flow_style=False)
            
    # 3. Create Root Training Config (Critical for Client)
    print(f"\n✅ Creating root client config...")
    root_client_config = {
        'dataset_details': {
            'data_filename': first_part_path,
            'dataset_id': dataset_name,
            'dataset_tags': ['IMAGE', 'SYNTHETIC', 'CUSTOM'],
             'suitable_models': ['AlexNet_class', 'LeNet5', 'CNN', 'FedAT_CNN', 'FedAT_AlexNet']
        },
        'metadata': get_dataset_summary(train_loader) 
    }
    
    with open(os.path.join(train_root_dir, 'train_dataset_config.yaml'), 'w') as f:
        yaml.dump(root_client_config, f, default_flow_style=False)
        
    print(f"✅ Dataset generation complete.")
    print(f"Validation Dir: {base_val_dir}")
    print(f"Training Dir: {train_root_dir}")

if __name__ == "__main__":
    create_synthetic_dataset()
