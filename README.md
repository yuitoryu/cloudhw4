# MNIST digit classifier

This cloud computing assignment uses PyTorch to train a CPU model that recognizes handwritten digits. On Google Kubernetes Engine, a training Job saved the model to a persistent volume. A separate FastAPI service loaded it to make predictions. The [deployment results](evidence/measurements.md) include test accuracy and what happened when Kubernetes replaced an inference Pod.

## Run locally

From the project folder, run these commands in PowerShell with Python 3.12 installed. The training step downloads MNIST and saves the model in `artifacts/`.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r training/requirements.txt -r inference/requirements.txt
.\.venv\Scripts\python -m training.train
.\.venv\Scripts\python -m uvicorn inference.app:app
```

Open `http://127.0.0.1:8000` on your computer and enter a test image ID from 0 to 9999. Try `42` to see the image and compare the predicted digit with its label.
