# CPU MNIST on GKE

A CPU-only training Job saves its model on a persistent volume. A separate FastAPI Deployment loads the saved model and serves a page for classifying MNIST test images by ID.

## Prerequisites and submission

The assignment requires CPU-only Google Cloud deployment, an interactive hosted URL, source files (40 points), and a report under five pages (60 points). Deadline, upload format, grading URL availability period, and additional course cloud restrictions are open questions. The requirements below follow ASSIGNMENT_PLAN.md.

| Requirement | Planned deliverable or evidence |
|---|---|
| Train on CPU in Google Cloud | training/train.py, training/Dockerfile, k8s/training-job.yaml and successful Job logs |
| Persist and reload the model | k8s/pvc.yaml, training output and inference startup logs with model version |
| Serve inference at a hosted URL | inference/app.py, inference/Dockerfile, k8s/inference-deployment.yaml and k8s/inference-service.yaml |
| Demonstrate user interaction and frontend/backend integration | inference/static/, public URL and input/output screenshots of image selection and prediction |
| Explain workflow, implementation, course concepts, observations, issues, self-healing and sources | report/report.pdf using evidence logs and Pod replacement observations |

## Model and API contract

`mnist-cnn-v1` accepts a batch of grayscale images shaped `[N, 1, 28, 28]` and returns ten logits per image. Training and inference share the same transform from raw `uint8` pixels to `float32`, dividing by `255` and then applying `(pixel - 0.1307) / 0.3081`. Only the training split updates the weights. The test split supplies evaluation results and browser samples. [TorchVision MNIST dataset](https://docs.pytorch.org/vision/main/generated/torchvision.datasets.MNIST.html)

Both processes use `MODEL_DIR`, which defaults to `artifacts/` locally and `/models` in the containers. Start inference after training exits successfully and leave inference stopped during retraining.

| Artifact | Contents |
|---|---|
| `model.pt` | PyTorch model state dictionary loaded onto CPU |
| `metadata.json` | Run version, architecture, seed, epochs, batch size, learning rate, normalization, test accuracy as a fraction, sample count, training and evaluation duration, and dependency versions |
| `mnist-test.npz` | `images` as raw `uint8` pixels shaped `[10000, 28, 28]` and `labels` as `int64` digits shaped `[10000]`, in original test-split order |

`POST /predict` accepts JSON such as `{"image_id":42}`. It requires an integer from 0 to 9999 inclusive and returns `image_id`, `predicted_digit`, `actual_digit`, and `model_version`. Invalid IDs return HTTP 422. `GET /sample/42` returns the raw sample as a PNG. `/healthz` checks the server process and `/readyz` returns the loaded model version. Missing or incompatible artifacts cause startup to fail with a diagnostic.

## Local execution

Use Python 3.12 on Windows or Linux x86-64 and run from the repository root. The first training run downloads MNIST. The following examples use PowerShell 7 and its UTF-8 log output. [PyTorch CPU wheels](https://pytorch.org/get-started/previous-versions/)

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r training/requirements.txt -r inference/requirements.txt
$env:OMP_NUM_THREADS = '2'
& .\.venv\Scripts\python.exe -m training.train 2>&1 | Tee-Object -FilePath .venv/local-training.log
if ($LASTEXITCODE -ne 0) { throw 'Training failed. Rerun it before starting inference.' }
```

After the trainer exits successfully, start inference.

```powershell
& .\.venv\Scripts\python.exe -m uvicorn inference.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/`. The trainer defaults to three epochs, batch size 128, learning rate 0.001, and seed 42. Run `python -m training.train --help` for overrides. Run the smoke test from another terminal while the server is running.

```powershell
& .\.venv\Scripts\python.exe scripts/smoke_test.py http://127.0.0.1:8000 --reference-log .venv/local-training.log
```

The optional `--reference-log` must come from the training run that produced the artifacts in use. Omit it for a contract check only.

## Local containers

Run these commands from the repository root with Docker Desktop's Linux engine. The training container exits after writing and reloading the artifacts. Inference mounts the same named volume read-only.

```powershell
docker build --platform linux/amd64 -f training/Dockerfile -t mnist-training:v1 .
docker build --platform linux/amd64 -f inference/Dockerfile -t mnist-inference:v1 .
docker volume create mnist-hw4-models
docker run --rm --cpus 2 --memory 2g --mount source=mnist-hw4-models,target=/models mnist-training:v1
if ($LASTEXITCODE -ne 0) { throw 'Training failed. Rerun it before starting inference.' }
docker run --detach --name mnist-hw4-inference --cpus 1 --memory 1g --publish 127.0.0.1:8080:8000 --mount source=mnist-hw4-models,target=/models,readonly mnist-inference:v1
```

Open `http://127.0.0.1:8080/` or run the smoke test against it. To verify the handoff survives container replacement, remove `mnist-hw4-inference`, repeat its `docker run`, then check that the same IDs return the same predictions and model version.

## Local Kubernetes

You can exercise the Job, claim, Deployment, and Service on an isolated Minikube profile. Load the two local images, use the Minikube `standard` StorageClass for the claim, and set the Job and Deployment image references to `mnist-training:v1` and `mnist-inference:v1`. Keep the five checked-in manifests for GKE and apply the local substitutions with `kubectl set image --local` and a copy of the PVC manifest. After the Job completes and the Deployment is ready, run `minikube -p mnist-hw4-local service mnist-inference -n mnist-hw4 --url` and use the printed URL for the smoke test. [Minikube Service access](https://minikube.sigs.k8s.io/docs/handbook/accessing/)

## Cloud deployment

The manifests use namespace `mnist-hw4`, the `standard-rwo` StorageClass, and a 10 GiB claim for a balanced Persistent Disk. The GKE class delays provisioning until the training Pod is scheduled. Training requests one CPU and 768 MiB, with limits of two CPUs and 2 GiB. Inference runs one replica with the `Recreate` strategy, requests 250 millicores and 384 MiB, and caps usage at one CPU and 1 GiB. Its startup probe allows up to two minutes to load artifacts. [GKE Persistent Disk CSI driver](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver) · [Compute Engine disk sizes](https://docs.cloud.google.com/compute/docs/disks/regional-persistent-disk)

The image paths in `k8s/` target the candidate project `summer-bond-475605-r6` and repository `mnist-hw4` in `us-central1`. Confirm course eligibility and quota before provisioning. If using a different registry, update both image paths. These commands assume a CPU-only GKE cluster with the Persistent Disk CSI driver, a Docker repository in Artifact Registry, and a node identity with repository read access. On this Windows setup, use the SDK's `kubectl.exe` to avoid the older client on `PATH`. [Environment and cloud checks](evidence/troubleshooting.md) · [GKE node identities](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/service-accounts)

```powershell
$registry = 'us-central1-docker.pkg.dev/summer-bond-475605-r6/mnist-hw4'
gcloud auth configure-docker us-central1-docker.pkg.dev
docker tag mnist-training:v1 "$registry/training:v1"
docker tag mnist-inference:v1 "$registry/inference:v1"
docker push "$registry/training:v1"
docker push "$registry/inference:v1"
```

Get credentials for the intended cluster, then choose its exact context name from the context list. If the Job fails, inspect its logs and rerun it successfully before applying the Deployment.

```powershell
$kubectl = Join-Path (Split-Path -Parent (Get-Command gcloud.cmd).Source) 'kubectl.exe'
& $kubectl config get-contexts
$gkeContext = Read-Host 'Enter the GKE context name'
if ($gkeContext -notlike 'gke_summer-bond-475605-r6_*') { throw 'Expected a GKE context in the configured project.' }
$gke = @('--context', $gkeContext)
& $kubectl @gke get storageclass standard-rwo
```

After checking the context and StorageClass, apply the workloads in order.

```powershell
& $kubectl @gke apply -f k8s/namespace.yaml
& $kubectl @gke apply --dry-run=server -f k8s/
if ($LASTEXITCODE -ne 0) { throw 'Manifest validation failed.' }
& $kubectl @gke apply -f k8s/pvc.yaml -f k8s/training-job.yaml
if ($LASTEXITCODE -ne 0) { throw 'Could not apply the training Job and claim.' }
& $kubectl @gke -n mnist-hw4 wait --for=condition=complete job/mnist-training --timeout=25m
if ($LASTEXITCODE -ne 0) { throw 'Training did not complete. Inspect the Job before starting inference.' }
$trainingPod = & $kubectl @gke -n mnist-hw4 get pods -l batch.kubernetes.io/job-name=mnist-training --field-selector=status.phase=Succeeded -o 'jsonpath={.items[0].metadata.name}'
if (-not $trainingPod) { throw 'Could not find the successful training Pod.' }
& $kubectl @gke -n mnist-hw4 logs $trainingPod | Set-Content -Encoding utf8 evidence/gke-training.log
if ($LASTEXITCODE -ne 0) { throw 'Could not capture the successful training log.' }
& $kubectl @gke -n mnist-hw4 get job,pvc
& $kubectl @gke apply -f k8s/inference-deployment.yaml
if ($LASTEXITCODE -ne 0) { throw 'Could not apply the inference Deployment.' }
& $kubectl @gke -n mnist-hw4 rollout status deployment/mnist-inference --timeout=5m
if ($LASTEXITCODE -ne 0) { throw 'Inference did not become ready.' }
& $kubectl @gke apply -f k8s/inference-service.yaml
& $kubectl @gke -n mnist-hw4 get service mnist-inference --watch
```

When an external IP appears, use its `http://` URL in the browser and in the smoke test with `--reference-log evidence/gke-training.log`. For retraining, scale inference to zero, wait for its Pod to terminate, then delete and reapply the training Job. After it completes, apply the Deployment manifest to restore one inference replica.

## Verification

The smoke test checks predictions and PNG samples at IDs `0`, `42`, and `9999` and verifies strict request validation. For the recovery check, record the inference Pod's name and UID, delete that Pod, wait for a ready replacement, and repeat the smoke test through the same Service address. The ReplicaSet restores the replica count, readiness controls traffic, and the claim preserves the artifacts. The single replica can cause a service interruption during replacement. [Kubernetes self-healing](https://kubernetes.io/docs/concepts/architecture/self-healing/)

The kubelet can restart failed containers under the Pod's restart policy. A failing liveness probe can also trigger a container restart. The local recovery experiment measured the replacement of one Pod on a single-node cluster. [Local measurements and evidence](evidence/measurements.md)

## Cleanup

After the required URL availability period is confirmed and met, remove assignment resources and verify the disposition of the persistent disk.
