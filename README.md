# CPU MNIST on GKE

A CPU-only training Job saves its model on a persistent volume. A separate FastAPI Deployment loads the saved model and serves a page for classifying MNIST test images by ID.

## Prerequisites and submission

The assignment requires CPU-only Google Cloud deployment, an interactive hosted URL, source files (40 points), and a report under five pages (60 points). Deadline, upload format, grading URL availability period, and additional course cloud restrictions are open questions.

| Requirement | Deliverable or evidence |
|---|---|
| Train on CPU in Google Cloud | training/train.py, training/Dockerfile, k8s/training-job.yaml and successful Job logs |
| Persist and reload the model | k8s/pvc.yaml, training output and inference startup logs with model version |
| Serve inference at a hosted URL | inference/app.py, inference/Dockerfile, k8s/inference-deployment.yaml and k8s/inference-service.yaml |
| Demonstrate user interaction and frontend/backend integration | inference/static/, public URL and input/output screenshots of image selection and prediction |
| Explain workflow, implementation, course concepts, observations, issues, self-healing and sources | [Four-page report](report/report.pdf) with measurements, public browser output and Pod replacement evidence |

For grading, open the [public MNIST demo](http://35.254.41.86/) and submit image ID `42`. The page shows the image, predicted and actual digits, and the model version. The [submission section](#submission-package) lists the files and the archive command.

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

These commands use Python 3.12 and PowerShell 7 on Windows x86-64. Run them from the repository root. The first training run downloads MNIST. [PyTorch CPU wheels](https://pytorch.org/get-started/previous-versions/)

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

Run these commands from the repository root with Docker Desktop's Linux engine. If you're retraining, stop and remove the existing `mnist-hw4-inference` container first. The training container exits after writing and reloading the artifacts. Inference mounts the same named volume read-only.

```powershell
docker build --platform linux/amd64 -f training/Dockerfile -t mnist-training:v1 .
if ($LASTEXITCODE -ne 0) { throw 'Training image build failed.' }
docker build --platform linux/amd64 -f inference/Dockerfile -t mnist-inference:v1 .
if ($LASTEXITCODE -ne 0) { throw 'Inference image build failed.' }
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
docker volume create mnist-hw4-models
if ($LASTEXITCODE -ne 0) { throw 'Could not create the model volume.' }
docker run --rm --cpus 2 --memory 2g --mount source=mnist-hw4-models,target=/models mnist-training:v1 2>&1 | Tee-Object -FilePath artifacts/docker-training.log
if ($LASTEXITCODE -ne 0) { throw 'Training failed. Rerun it before starting inference.' }
docker run --detach --name mnist-hw4-inference --cpus 1 --memory 1g --publish 127.0.0.1:8080:8000 --mount source=mnist-hw4-models,target=/models,readonly mnist-inference:v1
if ($LASTEXITCODE -ne 0) { throw 'Could not start inference.' }
```

Wait for `docker logs mnist-hw4-inference` to show `Application startup complete`. Open `http://127.0.0.1:8080/` and use the host Python from the local setup to compare the live predictions with the reference predictions in the training log.

```powershell
& .\.venv\Scripts\python.exe scripts/smoke_test.py http://127.0.0.1:8080 --reference-log artifacts/docker-training.log
```

Stop and remove the inference container, then start it again with the same volume.

```powershell
docker stop mnist-hw4-inference
if ($LASTEXITCODE -ne 0) { throw 'Could not stop inference.' }
docker rm mnist-hw4-inference
if ($LASTEXITCODE -ne 0) { throw 'Could not remove inference.' }
docker run --detach --name mnist-hw4-inference --cpus 1 --memory 1g --publish 127.0.0.1:8080:8000 --mount source=mnist-hw4-models,target=/models,readonly mnist-inference:v1
if ($LASTEXITCODE -ne 0) { throw 'Could not recreate inference.' }
```

Once the replacement finishes starting, repeat the smoke test with the same training log. Both runs should match the predicted digit, actual digit, and model version for IDs `0`, `42`, and `9999`.

### Verify missing-artifact handling locally

Check the missing-artifact case with an empty read-only mount. The process should exit with code 3 and report `Required artifact missing: /models/metadata.json`. [Startup error log](evidence/missing-artifacts.log)

```powershell
docker run --rm --network none --tmpfs /models:ro -e MODEL_DIR=/models mnist-inference:v1
$LASTEXITCODE
```

## Local Kubernetes

You can exercise the Job, claim, Deployment, and Service on an isolated Minikube profile. Load the two local images, use the Minikube `standard` StorageClass for the claim, and set the Job and Deployment image references to `mnist-training:v1` and `mnist-inference:v1`. Keep the five checked-in manifests for GKE and apply the local substitutions with `kubectl set image --local` and a copy of the PVC manifest. After the Job completes and the Deployment is ready, run `minikube -p mnist-hw4-local service mnist-inference -n mnist-hw4 --url` and use the printed URL for the smoke test. [Minikube Service access](https://minikube.sigs.k8s.io/docs/handbook/accessing/)

## Cloud deployment

The MNIST demo serves the model trained on GKE. [Public MNIST demo](http://35.254.41.86/) · [Deployment and smoke-test evidence](evidence/measurements.md#gke-deployment)

The manifests use namespace `mnist-hw4`, the `standard-rwo` StorageClass, and a 10 GiB claim for a balanced Persistent Disk. The GKE class delays provisioning until the training Pod is scheduled. Training requests one CPU and 768 MiB, with limits of two CPUs and 2 GiB. Inference runs one replica with the `Recreate` strategy, requests 250 millicores and 384 MiB, and caps usage at one CPU and 1 GiB. Its startup probe allows up to two minutes to load artifacts. [GKE Persistent Disk CSI driver](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver) · [Compute Engine disk sizes](https://docs.cloud.google.com/compute/docs/disks/regional-persistent-disk)

The assignment uses the regional GKE Autopilot cluster `mnist-hw4` in `us-central1` under project `summer-bond-475605-r6`. The two manifests point to immutable `v2` tags in the private Artifact Registry repository `mnist-hw4`. If using a different registry or release tag, update both image references. Use a `kubectl` client within one minor version of the GKE control plane. This deployment used the official Windows v1.36.4 client at `artifacts/gke-kubectl.exe`. [Windows kubectl installation](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/)

For cloud deployment, use Docker with its Linux engine, the Google Cloud CLI, `gke-gcloud-auth-plugin`, a compatible `kubectl`, and a Google Cloud project with billing enabled. Replace `$project` and `$region` below for your environment. On a fresh project, enable Compute Engine, GKE, and Artifact Registry. Create a private Docker repository and a dedicated node service account. Grant that account `roles/container.defaultNodeServiceAccount` in the project and `roles/artifactregistry.reader` on the repository. The examples assume your CLI account can create those resources and act as the node account. [Autopilot cluster setup](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/creating-an-autopilot-cluster) · [Artifact Registry access](https://docs.cloud.google.com/artifact-registry/docs/access-control)

```powershell
$project = 'summer-bond-475605-r6'
$region = 'us-central1'
$nodeAccount = "mnist-hw4-node@$project.iam.gserviceaccount.com"
$nodeMember = "serviceAccount:$nodeAccount"
gcloud services enable compute.googleapis.com container.googleapis.com artifactregistry.googleapis.com --project=$project
gcloud artifacts repositories create mnist-hw4 --project=$project --location=$region --repository-format=docker --immutable-tags
gcloud iam service-accounts create mnist-hw4-node --project=$project
gcloud projects add-iam-policy-binding $project --member=$nodeMember --role=roles/container.defaultNodeServiceAccount --condition=None
gcloud artifacts repositories add-iam-policy-binding mnist-hw4 --project=$project --location=$region --member=$nodeMember --role=roles/artifactregistry.reader --condition=None
gcloud container clusters create-auto mnist-hw4 --project=$project --location=$region --release-channel=regular --service-account=$nodeAccount --labels=assignment=mnist-hw4
```

Build the two local images with the `docker build` commands in Local containers and push the `linux/amd64` runtime manifests. Use a new `$releaseTag` for future builds because the registry tags are immutable. Set `spec.template.spec.containers[0].image` in each of `k8s/training-job.yaml` and `k8s/inference-deployment.yaml` to its matching registry image and tag before applying the manifests. [Local container builds](#local-containers)

```powershell
$registryHost = "$region-docker.pkg.dev"
$registry = "$registryHost/$project/mnist-hw4"
$releaseTag = 'v2'
gcloud auth configure-docker $registryHost
if ($LASTEXITCODE -ne 0) { throw 'Could not configure Artifact Registry authentication.' }
docker tag mnist-training:v1 "$registry/training:$releaseTag"
if ($LASTEXITCODE -ne 0) { throw 'Could not tag the training image.' }
docker tag mnist-inference:v1 "$registry/inference:$releaseTag"
if ($LASTEXITCODE -ne 0) { throw 'Could not tag the inference image.' }
docker push --platform linux/amd64 "$registry/training:$releaseTag"
if ($LASTEXITCODE -ne 0) { throw 'Could not push the training image.' }
docker push --platform linux/amd64 "$registry/inference:$releaseTag"
if ($LASTEXITCODE -ne 0) { throw 'Could not push the inference image.' }
```

Get credentials into a dedicated kubeconfig and use the explicit GKE context for every deployment command. On Windows x86-64, the following block downloads and verifies the client used in this deployment. If you already have a compatible client, set `$kubectl` to its path and skip the download. If the Job fails, inspect its logs and rerun it successfully before applying the Deployment.

```powershell
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
$env:KUBECONFIG = Join-Path (Resolve-Path artifacts) 'gke-kubeconfig.yaml'
$kubectl = Join-Path (Resolve-Path artifacts) 'gke-kubectl.exe'
$clientDownload = 'https://dl.k8s.io/release/v1.36.4/bin/windows/amd64/kubectl.exe'
Invoke-WebRequest -Uri $clientDownload -OutFile $kubectl -ErrorAction Stop
$expectedHash = (Invoke-RestMethod -Uri "$clientDownload.sha256" -ErrorAction Stop).Trim()
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $kubectl).Hash -ne $expectedHash) {
    throw 'kubectl checksum verification failed.'
}
gcloud container clusters get-credentials mnist-hw4 --project=$project --location=$region
if ($LASTEXITCODE -ne 0) { throw 'Could not get credentials for the assignment cluster.' }
$gke = @('--context', "gke_${project}_${region}_mnist-hw4")
& $kubectl @gke get nodes,namespaces
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the assignment cluster.' }
& $kubectl @gke get storageclass standard-rwo
if ($LASTEXITCODE -ne 0) { throw 'Retry after GKE finishes installing the Persistent Disk CSI add-on.' }
```

After checking the context and StorageClass, apply the workloads in order.

```powershell
& $kubectl @gke apply -f k8s/namespace.yaml
if ($LASTEXITCODE -ne 0) { throw 'Could not apply the assignment namespace.' }
& $kubectl @gke apply --dry-run=server -f k8s/
if ($LASTEXITCODE -ne 0) { throw 'Manifest validation failed.' }
& $kubectl @gke apply -f k8s/pvc.yaml -f k8s/training-job.yaml
if ($LASTEXITCODE -ne 0) { throw 'Could not apply the training Job and claim.' }
& $kubectl @gke -n mnist-hw4 wait --for=condition=complete job/mnist-training --timeout=25m
if ($LASTEXITCODE -ne 0) { throw 'Training did not complete. Inspect the Job before starting inference.' }
$trainingPod = & $kubectl @gke -n mnist-hw4 get pods -l batch.kubernetes.io/job-name=mnist-training --field-selector=status.phase=Succeeded -o 'jsonpath={.items[0].metadata.name}'
if ($LASTEXITCODE -ne 0 -or -not $trainingPod) { throw 'Could not find the successful training Pod.' }
$trainingLog = 'artifacts/gke-training.log'
& $kubectl @gke -n mnist-hw4 logs $trainingPod | Set-Content -Encoding utf8 -LiteralPath $trainingLog -ErrorAction Stop
if ($LASTEXITCODE -ne 0) { throw 'Could not capture the successful training log.' }
& $kubectl @gke -n mnist-hw4 get job,pvc
& $kubectl @gke apply -f k8s/inference-deployment.yaml
if ($LASTEXITCODE -ne 0) { throw 'Could not apply the inference Deployment.' }
& $kubectl @gke -n mnist-hw4 rollout status deployment/mnist-inference --timeout=5m
if ($LASTEXITCODE -ne 0) { throw 'Inference did not become ready.' }
& $kubectl @gke apply -f k8s/inference-service.yaml
if ($LASTEXITCODE -ne 0) { throw 'Could not apply the public Service.' }
& $kubectl @gke -n mnist-hw4 wait '--for=jsonpath={.status.loadBalancer.ingress[0].ip}' service/mnist-inference --timeout=10m
if ($LASTEXITCODE -ne 0) { throw 'The Service did not receive an external IP.' }
$publicIP = & $kubectl @gke -n mnist-hw4 get service mnist-inference -o 'jsonpath={.status.loadBalancer.ingress[0].ip}'
if ($LASTEXITCODE -ne 0 -or -not $publicIP) { throw 'Could not read the public IP.' }
$publicURL = "http://$publicIP"
$deadline = [DateTime]::UtcNow.AddMinutes(5)
do {
    try { Invoke-RestMethod -Uri "$publicURL/readyz" -TimeoutSec 5; break }
    catch {
        if ([DateTime]::UtcNow -ge $deadline) { throw }
        Start-Sleep -Seconds 5
    }
} while ($true)
& .\.venv\Scripts\python.exe scripts/smoke_test.py $publicURL --reference-log $trainingLog
if ($LASTEXITCODE -ne 0) { throw 'The public smoke test failed.' }
```

Open `$publicURL` in a browser and submit an image ID. Newly allocated load balancers may take additional time to pass health checks.

To retrain, stop inference and wait for its Pod to terminate before recreating the Job. The claim stays in place, and the completed Job overwrites the artifact files.

```powershell
& $kubectl @gke -n mnist-hw4 scale deployment/mnist-inference --replicas=0
if ($LASTEXITCODE -ne 0) { throw 'Could not stop inference.' }
$inferencePods = & $kubectl @gke -n mnist-hw4 get pods -l app=mnist-inference -o name
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the inference Pods.' }
if ($inferencePods) {
    & $kubectl @gke -n mnist-hw4 wait --for=delete $inferencePods --timeout=5m
    if ($LASTEXITCODE -ne 0) { throw 'Inference did not stop.' }
}
& $kubectl @gke -n mnist-hw4 delete job mnist-training --ignore-not-found --wait=true
if ($LASTEXITCODE -ne 0) { throw 'Could not remove the previous training Job.' }
```

Repeat the ordered deploy block above to create the new Job, capture its training log, restore the Deployment, and verify the new model at the public URL.

## Verification

The smoke test checks predictions and PNG samples at IDs `0`, `42`, and `9999` and expects HTTP 422 for invalid requests. In a browser, enter `42` and confirm the preview, predicted digit, actual digit, and model version appear. Enter `10000` and confirm an error replaces the prediction. [GKE browser screenshot](evidence/gke-browser.jpg)

Run the missing-artifact startup check in the isolated local container. [Local missing-artifact check](#verify-missing-artifact-handling-locally)

### Reproduce the GKE Pod replacement

Run this during a planned interruption of the one-replica service. Reuse `$kubectl`, `$gke`, `$publicURL`, and `$trainingLog` from the cloud deployment steps. Confirm the Deployment has one ready Pod and the training Job is complete, then record resource identities and verify the public baseline.

```powershell
$scope = $gke + @('-n', 'mnist-hw4')
$resourceIdentityColumns = 'custom-columns=KIND:.kind,NAME:.metadata.name,UID:.metadata.uid,BOUND_VOLUME:.spec.volumeName,COMPLETED:.status.completionTime'
& $kubectl @scope get deployment/mnist-inference service/mnist-inference pvc/mnist-models job/mnist-training -o $resourceIdentityColumns
if ($LASTEXITCODE -ne 0) { throw 'Could not record the baseline resource identities.' }
& $kubectl @scope get pods -l app=mnist-inference -o 'custom-columns=NAME:.metadata.name,UID:.metadata.uid,READY:.status.containerStatuses[0].ready'
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the original inference Pod.' }
& .\.venv\Scripts\python.exe scripts/smoke_test.py $publicURL --reference-log $trainingLog
if ($LASTEXITCODE -ne 0) { throw 'The baseline smoke test failed.' }
```

In a second terminal, set the same `$env:KUBECONFIG`, `$kubectl`, and `$scope`. Watch for the new Pod with `& $kubectl @scope get pods -l app=mnist-inference --watch`. In the first terminal, set `$beforePod` to the ready Pod name you just recorded and run the following. Record when the new Pod first reports `1/1` Ready.

```powershell
& $kubectl @scope exec $beforePod -- sha256sum /models/model.pt
if ($LASTEXITCODE -ne 0) { throw 'Could not record the original model checksum.' }
[DateTime]::UtcNow.ToString('o')
& $kubectl @scope delete "pod/$beforePod" --wait=false
if ($LASTEXITCODE -ne 0) { throw 'Could not delete the original inference Pod.' }
```

Set `$afterPod` to the replacement Pod name shown in the watch. Wait for that Pod and compare its UID, model checksum, and public predictions to the baseline. Check that the same Deployment, Service, claim, and completed Job are present. If public `/readyz` is still unavailable when the replacement reports Ready, allow the load balancer health check to catch up, then rerun the smoke test.

```powershell
& $kubectl @scope wait --for=condition=Ready "pod/$afterPod" --timeout=10m
if ($LASTEXITCODE -ne 0) { throw 'The replacement did not become ready.' }
& $kubectl @scope get "pod/$afterPod" -o 'custom-columns=NAME:.metadata.name,UID:.metadata.uid'
if ($LASTEXITCODE -ne 0) { throw 'Could not record the replacement Pod identity.' }
& $kubectl @scope get deployment/mnist-inference service/mnist-inference pvc/mnist-models job/mnist-training -o $resourceIdentityColumns
if ($LASTEXITCODE -ne 0) { throw 'Could not record the resource identities after replacement.' }
& $kubectl @scope exec $afterPod -- sha256sum /models/model.pt
if ($LASTEXITCODE -ne 0) { throw 'Could not record the replacement model checksum.' }
& .\.venv\Scripts\python.exe scripts/smoke_test.py $publicURL --reference-log $trainingLog
if ($LASTEXITCODE -ne 0) { throw 'The post-replacement smoke test failed.' }
```

The ReplicaSet restores the replica count, readiness controls traffic, and the claim preserves the artifacts. The kubelet can restart a failed container or a container that fails its liveness probe. The GKE experiment verified Pod replacement and measured 16.90 seconds to observed readiness. [Kubernetes self-healing](https://kubernetes.io/docs/concepts/architecture/self-healing/) · [GKE measurements](evidence/measurements.md#gke-pod-replacement)

## Cleanup

Wait until the demo and grading period are over before removing resources. Reuse the explicit `$gke` context from Cloud deployment. Record the underlying disk handle and reclaim policy before releasing the claim, and preserve any artifacts you still need. The deployed `Delete` policy normally removes the underlying disk when the claim is released. A `Retain` policy leaves the volume and disk for separate review. [Persistent volume reclaim policies](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaiming)

```powershell
$scope = $gke + @('-n', 'mnist-hw4')
$boundVolume = & $kubectl @scope get pvc mnist-models -o 'jsonpath={.spec.volumeName}'
if ($LASTEXITCODE -ne 0 -or -not $boundVolume) { throw 'Could not identify the bound volume.' }
& $kubectl @gke get pv $boundVolume -o 'custom-columns=VOLUME:.metadata.name,POLICY:.spec.persistentVolumeReclaimPolicy,DISK:.spec.csi.volumeHandle'
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the reclaim policy and disk.' }
```

After reviewing the policy and preserving the artifacts, remove the public Service and workloads before releasing the claim.

```powershell
& $kubectl @scope delete service/mnist-inference deployment/mnist-inference job/mnist-training --wait=true --timeout=10m
if ($LASTEXITCODE -ne 0) { throw 'Could not remove the Service and workloads.' }
& $kubectl @scope delete pvc/mnist-models --wait=true --timeout=10m
if ($LASTEXITCODE -ne 0) { throw 'Could not release the model claim.' }
gcloud compute forwarding-rules list --project=$project
gcloud compute disks list --project=$project
```

Compare the remaining cloud resources with the demo's former public IP and recorded disk handle. If the cluster and registry are dedicated to this assignment and you have finished using them, remove them with `gcloud container clusters delete mnist-hw4 --project=$project --location=$region` and `gcloud artifacts repositories delete mnist-hw4 --project=$project --location=$region`. Preserve shared course infrastructure.

## Submission package

The submission includes the report PDF, the training and inference programs and Dockerfiles, the Kubernetes manifests, the smoke test, and the supporting evidence. From a Git checkout at the final revision, recreate the ZIP with the following. The paths select committed submission files and exclude local environments, credentials, kubeconfigs, datasets, and trained weights.

```powershell
New-Item -ItemType Directory -Force -Path artifacts | Out-Null
git archive --format=zip --output=artifacts/cloudhw4-source.zip --prefix=cloudhw4/ HEAD .dockerignore .gitignore README.md common training inference k8s scripts tests evidence report/build_report.py report/report.pdf
if ($LASTEXITCODE -ne 0) { throw 'Could not package the submission.' }
```

To rebuild the report, install `reportlab` in a Python environment and run `python report/build_report.py` from the repository root. The script uses the captured GKE browser image in `evidence/`.
