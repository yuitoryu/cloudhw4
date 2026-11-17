"""Check a running inference service against the assignment's HTTP contract."""

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REFERENCE_IDS = (0, 42, 9999)


def request(url: str, payload: dict[str, object] | None = None) -> tuple[int, bytes]:
    if payload is None:
        query = Request(url)
    else:
        body = json.dumps(payload).encode("utf-8")
        query = Request(url, data=body, headers={"Content-Type": "application/json"})

    try:
        with urlopen(query, timeout=10) as response:
            return response.status, response.read()
    except HTTPError as error:
        with error:
            return error.code, error.read()


def read_references(path: Path) -> dict[int, dict[str, object]]:
    references: dict[int, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        _, marker, payload = line.partition(" REFERENCE ")
        if marker:
            prediction = json.loads(payload)
            references[prediction["image_id"]] = prediction
    return references


def check(base_url: str, references: dict[int, dict[str, object]] | None) -> None:
    for path in ("/", "/healthz", "/readyz"):
        status, _ = request(base_url + path)
        if status != 200:
            raise ValueError(f"{path} returned {status}, expected 200")

    for image_id in REFERENCE_IDS:
        status, body = request(base_url + "/predict", {"image_id": image_id})
        if status != 200:
            raise ValueError(f"Prediction for ID {image_id} returned {status}: {body!r}")

        prediction = json.loads(body)
        if type(prediction.get("image_id")) is not int or prediction["image_id"] != image_id:
            raise ValueError(f"Wrong image ID in response: {prediction}")
        for field in ("predicted_digit", "actual_digit"):
            digit = prediction.get(field)
            if type(digit) is not int or not 0 <= digit <= 9:
                raise ValueError(f"Invalid {field} in response: {prediction}")
        version = prediction.get("model_version")
        if not isinstance(version, str) or not version:
            raise ValueError(f"Missing model version in response: {prediction}")
        if references is not None and prediction != references.get(image_id):
            raise ValueError(f"Prediction for ID {image_id} differs from the training log: {prediction}")

        status, image = request(f"{base_url}/sample/{image_id}")
        if status != 200 or not image.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"Sample {image_id} did not return a PNG (HTTP {status})")
        print(json.dumps(prediction, sort_keys=True))

    invalid_payloads: list[dict[str, object]] = [{}]
    invalid_payloads.extend({"image_id": value} for value in (-1, 10000, 1.5, 42.0, "abc", "42", True))
    for payload in invalid_payloads:
        status, _ = request(base_url + "/predict", payload)
        if status != 422:
            raise ValueError(f"Invalid payload {payload!r} returned {status}, expected 422")
    print(f"Smoke test passed against {base_url}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", nargs="?", default="http://127.0.0.1:8000")
    parser.add_argument("--reference-log", type=Path, help="compare predictions and version with the training log")
    args = parser.parse_args()
    references = read_references(args.reference_log) if args.reference_log else None
    check(args.base_url.rstrip("/"), references)


if __name__ == "__main__":
    main()
