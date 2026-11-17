# Measurements

Local verification on 2026-11-17 used three epochs and the official 10,000-image MNIST test split. Each training log contains reference predictions from independently reloaded weights.

| Run | Model version | Test accuracy | CPU training and evaluation | Pod replacement to Ready |
|---|---|---:|---:|---:|
| [Windows Python](local-training.log) | `bea4f27f87ee4f90852ea3f3d97d0107` | 98.36% (9836/10000) | 23.98 s | — |
| [Docker](docker-training.log) | `46667634a50449ccaf5ca2a635d963fb` | 98.39% (9839/10000) | 21.92 s | — |
| [Minikube training Job](minikube-training.log) | `f9ad9dea80a44d1cbe65082a46d3e946` | 98.39% (9839/10000) | 17.92 s | 2.73 s |

- A fresh Windows Uvicorn process produced matching predictions, labels, and versions for IDs `0`, `42`, and `9999`. The smoke test also verified PNG responses and HTTP 422 for invalid payloads. [Native smoke test](native-smoke.log)
- The Docker test recreated the inference container and reused the named volume read-only. The replacement served the same model version and predictions at the same loopback address. [Before](docker-before.log) · [After](docker-after.log)
- Chrome verified real prediction and PNG requests, rejected an invalid ID, recovered from a stalled image request, and rendered a 360 px viewport without horizontal overflow. [Local browser screenshot](local-browser.png)
- All five GKE manifests passed a server-side dry run on Minikube 1.37.0. The live local run used locally loaded images and the `standard` host-path StorageClass. The Job completed, the PVC bound, and the Deployment became ready. Training stayed within the tested two-CPU and 2 GiB limits. Inference used about 175 MiB in a Docker snapshot after the smoke test.
- Deleting the Minikube inference Pod produced a new Pod UID. The original Job remained complete and the Service and PVC kept their UIDs. The same three predictions and model version passed through the same Service tunnel before and after the replacement. The elapsed time measures Pod readiness from the delete request. [Recovery run](minikube-recovery.log)
- Inference started with an empty `/models` mount exited with code 3 and identified the missing metadata file. [Startup error](missing-artifacts.log)

## GKE deployment

The assignment resources are in project `summer-bond-475605-r6`. Keep the Service and disk in place through the required grading period.

| Resource | Configuration |
|---|---|
| GKE cluster | `mnist-hw4`, regional Autopilot in `us-central1`, Regular release channel |
| Artifact Registry | Private Docker repository `us-central1-docker.pkg.dev/summer-bond-475605-r6/mnist-hw4` with immutable tags |
| `training:v2` | `sha256:cd0d7d82dbc16b5a539ee707d14cc47bbb5b3fdeadd1376ec852d83fcfddfb68` |
| `inference:v2` | `sha256:8957abf84a424576aa47e4abb81c661baaaa97d0479b2eb6a3a7743732613b20` |
| GKE node identity | `mnist-hw4-node` service account with the default GKE node role in the project and read access to the assignment repository |
| Kubernetes resources | Namespace `mnist-hw4`, Job `mnist-training`, claim `mnist-models`, Deployment and Service `mnist-inference` |
| Budget alert | `mnist-hw4-assignment`, US$30/month for this project, with actual-spend thresholds at 50%, 90%, and 100% |

The `standard-rwo` class uses the Persistent Disk CSI driver with `WaitForFirstConsumer` and a `Delete` reclaim policy. The claim began in `Pending` and bound to a balanced Persistent Disk after Autopilot provisioned a node for the training Pod. The requested 10 GiB is the minimum for a zonal balanced disk. [GKE resource log](gke-resources.log) · [Persistent Disk size limits](https://docs.cloud.google.com/compute/docs/disks/add-persistent-disk#pd-size-limits)

| Measurement | Result |
|---|---|
| Training Job completions | 1/1 |
| Job duration, including scheduling, volume provisioning, and image pull | 3m 41s |
| CPU training and evaluation | 55.75 s |
| Test accuracy | 98.37% (9837/10000) |
| Model version | `f7d83241c8e1451ca7ef0e204ded30dd` |
| Predictions from reloaded weights | ID `0` → 7, ID `42` → 4, ID `9999` → 6 |

[GKE training log](gke-training.log)

The inference Deployment loaded version `f7d83241c8e1451ca7ef0e204ded30dd` from the bound claim. The public page served the checked-in HTML, JavaScript, and stylesheet. The smoke test matched all three saved predictions, labels, and the model version, verified the PNG responses, and received HTTP 422 for invalid payloads. Browser screenshot capture is pending. [Public inference page](http://35.254.41.86/) · [GKE resource log](gke-resources.log) · [Public smoke test](gke-smoke.log)
