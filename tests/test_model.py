from io import BytesIO
import unittest

import torch

from common.model import MnistClassifier, preprocess


class ModelContractTest(unittest.TestCase):
    def test_cpu_weights_round_trip_preserves_logits(self) -> None:
        images = torch.zeros((2, 28, 28), dtype=torch.uint8)
        images[1].fill_(255)
        inputs = preprocess(images)

        self.assertEqual(inputs.shape, (2, 1, 28, 28))
        self.assertEqual(inputs.dtype, torch.float32)
        self.assertAlmostEqual(inputs[0, 0, 0, 0].item(), -0.4242, places=4)
        self.assertAlmostEqual(inputs[1, 0, 0, 0].item(), 2.8215, places=4)

        original = MnistClassifier().eval()
        with BytesIO() as weights, torch.inference_mode():
            torch.save(original.state_dict(), weights)
            weights.seek(0)
            reloaded = MnistClassifier().eval()
            reloaded.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True))

            self.assertEqual(reloaded(inputs).shape, (2, 10))
            torch.testing.assert_close(reloaded(inputs), original(inputs))
