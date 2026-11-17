"""Model and preprocessing shared by training and inference."""

import torch
from torch import Tensor, nn


ARCHITECTURE = "mnist-cnn-v1"
IMAGE_SIZE = 28
CLASS_COUNT = 10
NORMALIZATION = {"mean": 0.1307, "std": 0.3081}


def preprocess(images: Tensor) -> Tensor:
    """Convert raw uint8 (..., 28, 28) pixels to normalized float32 (..., 1, 28, 28)."""
    scaled = images.unsqueeze(-3).to(torch.float32) / 255.0
    return (scaled - NORMALIZATION["mean"]) / NORMALIZATION["std"]


class MnistClassifier(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Flatten(),
            nn.Linear(32 * 7 * 7, CLASS_COUNT),
        )

    def forward(self, images: Tensor) -> Tensor:
        return self.network(images)
