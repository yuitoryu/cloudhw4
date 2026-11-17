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
