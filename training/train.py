"""Train on the official MNIST training split and export CPU inference artifacts."""

import argparse
from dataclasses import asdict
from importlib.metadata import version
import json
import logging
import math
from pathlib import Path
from platform import python_version
from tempfile import TemporaryDirectory
from time import perf_counter
from uuid import uuid4

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from torchvision.datasets import MNIST  # type: ignore[import-untyped]

from common.artifacts import METADATA_FILE, REFERENCE_IDS, SAMPLES_FILE, WEIGHTS_FILE, load_artifacts, model_directory
from common.model import ARCHITECTURE, NORMALIZATION, MnistClassifier, preprocess


LOGGER = logging.getLogger(__name__)


def save_artifacts(directory: Path, model: MnistClassifier, test_data: MNIST, metadata: dict[str, object]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=directory) as staging_directory:
        staging = Path(staging_directory)
        torch.save(model.state_dict(), staging / WEIGHTS_FILE)
        np.savez_compressed(staging / SAMPLES_FILE, images=test_data.data.numpy(), labels=test_data.targets.numpy())
        (staging / METADATA_FILE).write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

        # Publish metadata last so an interrupted replacement cannot look complete.
        (directory / METADATA_FILE).unlink(missing_ok=True)
        for name in (WEIGHTS_FILE, SAMPLES_FILE, METADATA_FILE):
            (staging / name).replace(directory / name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--model-dir", type=Path, default=model_directory())
    args = parser.parse_args()
    if args.epochs < 1 or args.batch_size < 1:
        parser.error("epochs and batch size must be positive")
    if not math.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("learning rate must be finite and positive")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    torch.manual_seed(args.seed)
    LOGGER.info("Loading MNIST splits, then training on CPU with seed %d", args.seed)
    train_data = MNIST(args.data_dir, train=True, download=True)
    test_data = MNIST(args.data_dir, train=False, download=True)
    train_batches = DataLoader(TensorDataset(train_data.data, train_data.targets), batch_size=args.batch_size, shuffle=True)
    test_batches = DataLoader(TensorDataset(test_data.data, test_data.targets), batch_size=args.batch_size)

    started = perf_counter()
    model = MnistClassifier().cpu()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    loss_function = nn.CrossEntropyLoss()
    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for images, labels in train_batches:
            optimizer.zero_grad()
            loss = loss_function(model(preprocess(images)), labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * labels.numel()
        LOGGER.info("Epoch %d/%d, mean training loss %.4f", epoch + 1, args.epochs, total_loss / len(train_data))

    model.eval()
    correct = 0
    with torch.inference_mode():
        for images, labels in test_batches:
            predictions = model(preprocess(images)).argmax(dim=1)
            correct += int((predictions == labels).sum().item())
    elapsed = perf_counter() - started
    accuracy = correct / len(test_data)
    LOGGER.info("Test accuracy %.2f%% (%d/%d); CPU training and evaluation %.2fs", accuracy * 100, correct, len(test_data), elapsed)

    metadata = {
        "model_version": uuid4().hex,
        "architecture": ARCHITECTURE,
        "seed": args.seed,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "normalization": NORMALIZATION,
        "test_accuracy": accuracy,
        "test_sample_count": len(test_data),
        "training_duration_seconds": elapsed,
        "dependency_versions": {
            "python": python_version(),
            "torch": str(torch.__version__),
            "torchvision": version("torchvision"),
            "numpy": np.__version__,
        },
    }
    directory = args.model_dir.resolve()
    save_artifacts(directory, model, test_data, metadata)
    reloaded = load_artifacts(directory)
    LOGGER.info("Reloaded model %s from %s", reloaded.model_version, directory)
    for image_id in REFERENCE_IDS:
        LOGGER.info("REFERENCE %s", json.dumps(asdict(reloaded.predict(image_id)), sort_keys=True))


if __name__ == "__main__":
    main()
