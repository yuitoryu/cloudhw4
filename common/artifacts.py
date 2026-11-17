"""The file contract between a completed training run and inference."""

from dataclasses import dataclass
import json
import os
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
import torch

from common.model import ARCHITECTURE, CLASS_COUNT, IMAGE_SIZE, NORMALIZATION, MnistClassifier, preprocess


WEIGHTS_FILE = "model.pt"
METADATA_FILE = "metadata.json"
SAMPLES_FILE = "mnist-test.npz"
TEST_SAMPLE_COUNT = 10_000
REFERENCE_IDS = (0, 42, TEST_SAMPLE_COUNT - 1)


def model_directory() -> Path:
    return Path(os.environ.get("MODEL_DIR") or "artifacts")


@dataclass(frozen=True)
class Prediction:
    image_id: int
    predicted_digit: int
    actual_digit: int
    model_version: str


@dataclass(frozen=True)
class ModelArtifacts:
    model: MnistClassifier
    images: NDArray[np.uint8]
    labels: NDArray[np.int64]
    model_version: str

    def predict(self, image_id: int) -> Prediction:
        if not 0 <= image_id < TEST_SAMPLE_COUNT:
            raise ValueError(f"Image ID {image_id} is outside the MNIST test split")

        inputs = preprocess(torch.from_numpy(self.images[image_id])).unsqueeze(0)
        with torch.inference_mode():
            digit = int(self.model(inputs).argmax(dim=1).item())
        return Prediction(image_id, digit, int(self.labels[image_id]), self.model_version)


def load_artifacts(directory: Path) -> ModelArtifacts:
    for name in (METADATA_FILE, WEIGHTS_FILE, SAMPLES_FILE):
        path = directory / name
        if not path.is_file():
            raise FileNotFoundError(f"Required artifact missing: {path}")

    metadata = json.loads((directory / METADATA_FILE).read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or metadata.get("architecture") != ARCHITECTURE:
        raise ValueError(f"Expected architecture {ARCHITECTURE} in {METADATA_FILE}")
    if metadata.get("normalization") != NORMALIZATION:
        raise ValueError(f"Incompatible normalization in {METADATA_FILE}")
    version = metadata.get("model_version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError(f"Missing model version in {METADATA_FILE}")

    with np.load(directory / SAMPLES_FILE, allow_pickle=False) as samples:
        images = samples["images"]
        labels = samples["labels"]
    if images.shape != (TEST_SAMPLE_COUNT, IMAGE_SIZE, IMAGE_SIZE) or images.dtype != np.uint8:
        raise ValueError(f"Expected {TEST_SAMPLE_COUNT} raw uint8 MNIST images in {SAMPLES_FILE}")
    if labels.shape != (TEST_SAMPLE_COUNT,) or labels.dtype != np.int64:
        raise ValueError(f"Expected {TEST_SAMPLE_COUNT} int64 labels in {SAMPLES_FILE}")
    if np.any((labels < 0) | (labels >= CLASS_COUNT)):
        raise ValueError(f"Labels in {SAMPLES_FILE} must be digits 0 through 9")

    model = MnistClassifier().cpu().eval()
    model.load_state_dict(torch.load(directory / WEIGHTS_FILE, map_location="cpu", weights_only=True))
    return ModelArtifacts(model, images, labels, version)
