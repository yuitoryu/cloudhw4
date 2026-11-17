# Troubleshooting

## Initial environment check, 2026-11-17

| Check | Outcome |
|---|---|
| Python | WSL python3 reports 3.14.4. The Windows python alias failed to launch. Training dependency compatibility remains to be tested. |
| Docker | Client 28.1.1. The Docker Desktop Linux engine pipe was unavailable. Cloud Build is the planned fallback. |
| Kubernetes client | Windows kubectl v1.27.4. Cluster compatibility remains to be checked against the selected GKE version. |
| Cloud CLI | Windows Google Cloud SDK 541.0.0. A project and active account are configured. Project and billing queries both required interactive reauthentication. |
| GKE authentication plugin | Missing from the Windows and WSL command paths checked. Install and verify before cluster access. |
| Cloud feasibility | Pending interactive gcloud auth login, then confirmation of project eligibility, billing/credits, relevant permissions and quotas for the selected region. |

## Step 01 follow-up, 2026-11-17

| Check | Outcome |
|---|---|
| Local Linux image builds | Started Docker Desktop. Client and Linux engine both report 28.1.1. Buildx 0.23.0-desktop.1 successfully ran a minimal build from `scratch`. Use local Docker for image builds. |
| GKE client tools | Installed GKE authentication plugin 0.5.10 and verified that it runs. The SDK's `kubectl.exe` reports v1.33.5-dispatcher. Windows still resolves an older `kubectl` first on PATH. Use the SDK copy when configuring cluster access and verify client compatibility with the selected cluster. |
| Project and billing | `summer-bond-475605-r6` is active and billing is enabled. Use it as the candidate project. Course-specific project restrictions and credit arrangements remain open. |
| Project permissions | The signed-in account passed project-level IAM checks for enabling and using services, reading quotas, creating and reading GKE clusters, and creating Artifact Registry repositories. It also passed the Cloud Build creation check for the fallback workflow. |
| Compute quota limits | Used `us-central1` as a preliminary region because no default region was configured. Its effective limits include 200 vCPUs, 24 VM instances, 4,096 GB of standard persistent disk, 500 GB of SSD persistent disk, 8 in-use IP addresses, and 50 regional external passthrough Network Load Balancer forwarding rules. |
| Service activation and deployment | Compute Engine, GKE, Artifact Registry, and Cloud Build are disabled. The Service Usage API returned effective quota limits. Check remaining quota after enabling Compute Engine, then verify cluster version, node service account permissions, and registry access in Step 07. |

[GKE client setup](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/cluster-access-for-kubectl) · [Project IAM permission checks](https://docs.cloud.google.com/iam/docs/testing-permissions) · [Service Usage quota limits](https://docs.cloud.google.com/service-usage/docs/reference/rest/v1beta1/services.consumerQuotaMetrics/list)
