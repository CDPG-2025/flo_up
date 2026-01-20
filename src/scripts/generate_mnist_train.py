import torch
from torchvision import datasets, transforms
from torch.utils.data import Subset
from torchvision import transforms

transform = transforms.Compose([
    transforms.Grayscale(num_output_channels=3),
    transforms.ToTensor(),
    transforms.Normalize(
        (0.1307, 0.1307, 0.1307),
        (0.3081, 0.3081, 0.3081)
    )
])

base_dataset = datasets.MNIST(
    root="src/data/MNIST_IID",
    train=True,
    download=True,
    transform=transform
)

# IMPORTANT: wrap with Subset so .dataset exists
wrapped_dataset = Subset(base_dataset, range(len(base_dataset)))

torch.save(wrapped_dataset, "src/data/MNIST_IID/train_data.pth")

print("MNIST train_data.pth fixed")
