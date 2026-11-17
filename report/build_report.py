"""Rebuild the four-page assignment report with ReportLab."""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph


REPORT_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = REPORT_DIR.parent / "evidence"
PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 48
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN
INK = HexColor("#18283B")
MUTED = HexColor("#486077")
ACCENT = HexColor("#086764")
PALE = HexColor("#EAF4F2")
RULE = HexColor("#CFDCE2")
DEMO = "http://35.254.41.86/"


def paragraph(pdf: Canvas, content: str, top: float, *,
              size: float = 11, leading: float = 15.5,
              x: float = MARGIN, width: float = TEXT_WIDTH) -> float:
    style = ParagraphStyle("report", fontName="Helvetica", fontSize=size,
                           leading=leading, textColor=INK)
    block = Paragraph(content, style)
    _, height = block.wrap(width, PAGE_HEIGHT)
    bottom = top - height
    if bottom < 60:
        raise ValueError(f"Text overlaps the footer on page {pdf.getPageNumber()}: {content[:60]}")
    block.drawOn(pdf, x, bottom)
    return bottom


def label(pdf: Canvas, content: str, x: float, y: float, size: float = 10) -> None:
    pdf.setFillColor(ACCENT)
    pdf.setFont("Helvetica-Bold", size)
    pdf.drawString(x, y, content)


def start_page(pdf: Canvas, title: str) -> None:
    pdf.bookmarkPage(title)
    pdf.addOutlineEntry(title, title)
    label(pdf, "HOMEWORK 4  /  CLOUD COMPUTING", MARGIN, 743)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 29)
    pdf.drawString(MARGIN, 697, title)
    pdf.setStrokeColor(RULE)
    pdf.line(MARGIN, 676, PAGE_WIDTH - MARGIN, 676)


def end_page(pdf: Canvas) -> None:
    pdf.setStrokeColor(RULE)
    pdf.line(MARGIN, 49, PAGE_WIDTH - MARGIN, 49)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(MARGIN, 33, "CPU MNIST on Google Kubernetes Engine")
    pdf.drawRightString(PAGE_WIDTH - MARGIN, 33, f"{pdf.getPageNumber()} / 4")
    pdf.showPage()


def architecture(pdf: Canvas) -> None:
    training_x, volume_x, inference_x = MARGIN, MARGIN + 184, MARGIN + 368
    top_row, bottom_row = 490, 389
    box_width, box_height = 148, 52
    for x, y, name, detail in (
        (training_x, top_row, "Training Job", "PyTorch on CPU"),
        (volume_x, top_row, "Persistent volume", "10 GiB disk via PVC"),
        (inference_x, top_row, "Inference Deployment", "FastAPI, one replica"),
        (training_x, bottom_row, "Browser", "Image ID and prediction"),
        (volume_x, bottom_row, "LoadBalancer Service", "Public HTTP on port 80"),
    ):
        pdf.setFillColor(PALE)
        pdf.roundRect(x, y, box_width, box_height, 5, stroke=0, fill=1)
        label(pdf, name, x + 11, y + 31, 11)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x + 11, y + 13, detail)

    pdf.setStrokeColor(ACCENT)
    left_edge, middle_edge = training_x + box_width, volume_x + box_width
    top_y, bottom_y = top_row + box_height / 2, bottom_row + box_height / 2
    for start, end, line_y in (
        (left_edge, volume_x, top_y),
        (middle_edge, inference_x, top_y),
        (left_edge, volume_x, bottom_y),
        (volume_x, left_edge, bottom_y - 9),
    ):
        tip_base = end - 5 if end > start else end + 5
        pdf.lines([(start, line_y, end, line_y),
                   (tip_base, line_y + 3, end, line_y), (tip_base, line_y - 3, end, line_y)])
    inference_center = inference_x + box_width / 2
    pdf.lines([(middle_edge, bottom_y, inference_center, bottom_y),
               (inference_center, bottom_y, inference_center, top_row),
               (inference_center - 4, top_row - 5, inference_center, top_row),
               (inference_center + 4, top_row - 5, inference_center, top_row)])
    label(pdf, "write", left_edge + 4, top_y + 9, 8)
    label(pdf, "load", middle_edge + 8, top_y + 9, 8)
    label(pdf, "port 8000", inference_center + 10, bottom_y + 28, 8)


def overview(pdf: Canvas) -> None:
    start_page(pdf, "CPU MNIST on GKE")
    bottom = paragraph(pdf, "This project trains a handwritten-digit classifier on Google Kubernetes "
                       "Engine (GKE) using CPUs. A visitor opens the public webpage, submits a test "
                       "image ID from 0 to 9,999, and sees the image, predicted digit, actual label "
                       "and model version.", 650, size=12, leading=17)
    paragraph(pdf, f'<b>Hosted demo</b> &nbsp; <link href="{DEMO}" color="#086764">{DEMO}</link>', bottom - 12)
    architecture(pdf)
    paragraph(pdf, "<b>Figure 1.</b> The Job writes artifacts to the disk. The Deployment loads them "
              "after training completes and serves browser traffic through the public Service.",
              374, size=10, leading=13)

    label(pdf, "How the architecture uses Kubernetes", MARGIN, 322, 14)
    bottom = paragraph(pdf, "<b>Batch and serving workloads.</b> The training Job has one completion and "
                       "exits when the artifacts and reference predictions are ready. The inference Deployment "
                       "maintains a running web server, and a Service gives clients a stable address across "
                       "Pod replacements. [1, 2]", 303)
    bottom = paragraph(pdf, "<b>Persistent storage.</b> The PersistentVolumeClaim (PVC) requests a 10 GiB "
                       "balanced disk through GKE's <font name='Courier'>standard-rwo</font> StorageClass. "
                       "The Job writes to <font name='Courier'>/models</font> and the inference Pod mounts "
                       "the same claim read-only. The disk's lifecycle is independent of either Pod. [3, 4]", bottom - 12)
    paragraph(pdf, "<b>Resource isolation.</b> The training and inference images carry separate entry points "
              "and dependencies. CPU and memory requests guide scheduling. Training is capped at two CPUs "
              "and 2 GiB, and inference at one CPU and 1 GiB.", bottom - 12)
    end_page(pdf)


def implementation(pdf: Canvas) -> None:
    start_page(pdf, "Training and serving")
    label(pdf, "Train and evaluate", MARGIN, 647, 14)
    bottom = paragraph(pdf, "TorchVision supplies the official MNIST training and test splits. "
                       "The shared preprocessing function converts 28 by 28 grayscale images to "
                       "floats, divides pixels by 255, and normalizes with mean 0.1307 and standard "
                       "deviation 0.3081. Two convolution, ReLU and pooling blocks feed a linear "
                       "layer that outputs ten logits. [5]", 628)
    bottom = paragraph(pdf, "Training uses Adam, cross-entropy, seed 42, three epochs, a batch size of 128 "
                       "and a learning rate of 0.001. Only the training split updates the weights. "
                       "Evaluation computes top-1 accuracy on 10,000 held-out test images.", bottom - 10)

    label(pdf, "Save and reload the model", MARGIN, bottom - 26, 14)
    bottom = paragraph(pdf, "The trainer writes the three artifacts below and reloads the saved weights on "
                       "CPU to generate reference predictions. FastAPI validates and loads the same bundle "
                       "once at process startup. Missing or incompatible artifacts stop startup. [6]", bottom - 43)
    for filename, explanation in (
        ("model.pt", "PyTorch state dictionary containing the learned weights"),
        ("metadata.json", "Run version, model and training configuration, accuracy and timing"),
        ("mnist-test.npz", "Raw test images and labels in original test-split order"),
    ):
        pdf.setStrokeColor(RULE)
        pdf.line(MARGIN, bottom - 9, PAGE_WIDTH - MARGIN, bottom - 9)
        paragraph(pdf, f"<font name='Courier'>{filename}</font>", bottom - 16, width=112)
        bottom = paragraph(pdf, explanation, bottom - 16, x=MARGIN + 120, width=TEXT_WIDTH - 120)

    label(pdf, "Connect the webpage and API", MARGIN, bottom - 30, 14)
    bottom = paragraph(pdf, "FastAPI serves the HTML, CSS and JavaScript from the same origin as the API. "
                       "The browser sends the selected ID as JSON to <font name='Courier'>POST /predict</font> "
                       "and fetches the corresponding PNG from <font name='Courier'>GET /sample/{id}</font>. "
                       "The API returns the highest-scoring digit, the stored label and the model version. "
                       "The label is used for display. Invalid IDs return HTTP 422. [7]", bottom - 47)

    label(pdf, "Implementation and attribution", MARGIN, bottom - 24, 14)
    paragraph(pdf, "The assignment implementation adds the CNN and artifact loader in <b>common/</b>, "
              "the trainer and its Dockerfile in <b>training/</b>, the API, webpage and inference Dockerfile "
              "in <b>inference/</b>, and the Job, Deployment, Service, PVC and namespace manifests in "
              "<b>k8s/</b>. It uses the libraries and dataset cited on page 4. The smoke test in <b>scripts/</b> "
              "compares the API with saved training references. Codex assisted with implementation, "
              "verification and report drafting.", bottom - 41)
    end_page(pdf)


def results(pdf: Canvas) -> None:
    start_page(pdf, "Deployment and results")
    paragraph(pdf, "After verification on Windows, Docker and Minikube, the two Linux images were "
              "pushed to Artifact Registry. On a regional GKE Autopilot cluster in <b>us-central1</b>, "
              "the namespace, claim and Job were applied first. The Deployment and public Service followed "
              "successful training. Measurements are from the November 17, 2026 run.", 651)
    for x, value, description in (
        (48, "98.37%", "Test accuracy (9,837 / 10,000)"),
        (220, "55.75 s", "CPU training and evaluation"),
        (392, "3m 41s", "Full Job duration"),
    ):
        pdf.setFillColor(PALE)
        pdf.roundRect(x, 522, 164, 51, 4, stroke=0, fill=1)
        label(pdf, value, x + 11, 549, 19)
        paragraph(pdf, description, 542, x=x + 11, width=143, size=9, leading=11)

    screenshot = ImageReader(str(EVIDENCE_DIR / "gke-browser.jpg"))
    pixel_width, pixel_height = screenshot.getSize()
    image_width = 490
    image_height = image_width * pixel_height / pixel_width
    image_bottom = 506 - image_height
    pdf.drawImage(screenshot, (PAGE_WIDTH - image_width) / 2, image_bottom,
                  width=image_width, height=image_height)
    bottom = paragraph(pdf, "<b>Figure 2.</b> Public browser demo. Input ID 42 returned a PNG of a handwritten "
                       "4, predicted digit 4 and actual digit 4. Model version f7d83241c8e1451ca7ef0e204ded30dd.",
                       image_bottom - 8, size=9.6, leading=12.2)
    paragraph(pdf, "The smoke test matched the saved predictions for IDs <b>0 (7), 42 (4) and 9999 (6)</b>, "
              "validated the PNG responses and received HTTP 422 for invalid inputs. See "
              "<b>evidence/gke-training.log</b> and <b>evidence/gke-smoke.log</b>.", bottom - 6, size=9.6, leading=12.2)
    end_page(pdf)


def recovery(pdf: Canvas) -> None:
    start_page(pdf, "Recovery and lessons")
    label(pdf, "Pod replacement on GKE", MARGIN, 646, 14)
    bottom = paragraph(pdf, "The ready inference Pod was deleted while the Deployment, Service and PVC "
                       "remained in place. The same ReplicaSet created a Pod with a different UID. "
                       "The client observed it ready <b>16.90 s</b> after requesting deletion. The first "
                       "verified public smoke test began about <b>20 s</b> after the request. The test "
                       "did not continuously measure public downtime. See <b>evidence/gke-recovery.log</b>.", 627)
    bottom = paragraph(pdf, "The replacement reloaded the same model version and the weights had the same "
                       "SHA-256. The original Job remained complete, and all three predictions passed "
                       "through the same public URL. The PVC and underlying volume retained their identities.", bottom - 9)
    bottom = paragraph(pdf, "<b>What Kubernetes handled.</b> The ReplicaSet restored the desired Pod count. "
                       "The startup probe gives the model time to load. The readiness probe uses "
                       "<font name='Courier'>/readyz</font> to determine whether the Pod can receive traffic. "
                       "A failing liveness probe on <font name='Courier'>/healthz</font> can trigger a "
                       "kubelet container restart. The experiment covered Pod replacement. "
                       "A single replica may be unavailable during recovery, and node failure, cross-zone "
                       "recovery and liveness-triggered restarts were outside the experiment. [8, 9]", bottom - 9)

    label(pdf, "Deployment issues and fixes", MARGIN, bottom - 25, 14)
    bottom = paragraph(pdf, "<b>Image tags.</b> An attestation occupied an immutable training tag. "
                       "Pushing the Linux/AMD64 runtime manifests under fresh tags resolved the conflict. "
                       "<b>Storage.</b> The StorageClass was briefly absent while GKE finished installing "
                       "the disk driver. The claim was applied after the class appeared. "
                       "<b>Public endpoint.</b> The first smoke test timed out shortly after IP allocation. "
                       "A full retry passed with the same Deployment. See <b>evidence/troubleshooting.md</b>.", bottom - 43)
    bottom = paragraph(pdf, "A separate local test mounted an empty <font name='Courier'>/models</font>. "
                       "Inference reported the missing metadata and exited with code 3. See "
                       "<b>evidence/missing-artifacts.log</b>.", bottom - 9)

    label(pdf, "References", MARGIN, bottom - 24, 14)
    references = (
        ("Kubernetes - Jobs", "https://kubernetes.io/docs/concepts/workloads/controllers/job/"),
        ("Kubernetes - Services", "https://kubernetes.io/docs/concepts/services-networking/service/"),
        ("Kubernetes - Persistent volumes", "https://kubernetes.io/docs/concepts/storage/persistent-volumes/"),
        ("Google Cloud - Persistent Disk CSI driver", "https://docs.cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/gce-pd-csi-driver"),
        ("TorchVision - MNIST dataset and splits", "https://docs.pytorch.org/vision/main/generated/torchvision.datasets.MNIST.html"),
        ("PyTorch - Saving and loading model weights", "https://docs.pytorch.org/tutorials/beginner/basics/saveloadrun_tutorial.html"),
        ("FastAPI - Static files", "https://fastapi.tiangolo.com/tutorial/static-files/"),
        ("Kubernetes - Self-healing", "https://kubernetes.io/docs/concepts/architecture/self-healing/"),
        ("Kubernetes - Startup, readiness and liveness probes", "https://kubernetes.io/docs/concepts/workloads/pods/probes/"),
    )
    for index, (name, url) in enumerate(references):
        column, row = divmod(index, 5)
        paragraph(pdf, f'[{index + 1}] <link href="{url}" color="#086764">{name}</link>',
                  bottom - 38 - row * 13, x=MARGIN + column * 253,
                  width=253 if column == 0 else TEXT_WIDTH - 253, size=9, leading=11)
    end_page(pdf)


if __name__ == "__main__":
    report = Canvas(str(REPORT_DIR / "report.pdf"), pagesize=letter)
    report.setTitle("CPU MNIST on Google Kubernetes Engine")
    report.setSubject("Homework 4 implementation, deployment and recovery verification")
    overview(report)
    implementation(report)
    results(report)
    recovery(report)
    report.save()
