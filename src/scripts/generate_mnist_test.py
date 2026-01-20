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
    root="src/val_data/MNIST_IID",
    train=False,
    download=True,
    transform=transform
)

wrapped_dataset = Subset(base_dataset, range(len(base_dataset)))

torch.save(wrapped_dataset, "src/val_data/MNIST_IID/test.pth")

print("MNIST test.pth fixed")
