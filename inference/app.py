"""Read-only MNIST inference over HTTP."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import BytesIO
import logging
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path as PathParam, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel, Field

from common.artifacts import TEST_SAMPLE_COUNT, ModelArtifacts, Prediction, load_artifacts, model_directory


LOGGER = logging.getLogger("uvicorn.error")
STATIC_DIR = Path(__file__).resolve().parent / "static"


class PredictionRequest(BaseModel):
    image_id: Annotated[int, Field(strict=True, ge=0, lt=TEST_SAMPLE_COUNT)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    directory = model_directory().resolve()
    try:
        artifacts = load_artifacts(directory)
    except Exception as error:
        raise RuntimeError(f"Cannot load model artifacts from {directory}: {error}") from error

    app.state.artifacts = artifacts
    LOGGER.info("Loaded model %s from %s", artifacts.model_version, directory)
    yield


app = FastAPI(title="MNIST Digit Classifier", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readiness(request: Request) -> dict[str, str]:
    artifacts: ModelArtifacts | None = getattr(request.app.state, "artifacts", None)
    if artifacts is None:
        raise HTTPException(503, "Model artifacts are unavailable")
    return {"status": "ready", "model_version": artifacts.model_version}


@app.post("/predict")
def predict(body: PredictionRequest, request: Request) -> Prediction:
    artifacts: ModelArtifacts = request.app.state.artifacts
    return artifacts.predict(body.image_id)


@app.get("/sample/{image_id}", response_class=Response, responses={200: {"content": {"image/png": {}}}})
def sample(image_id: Annotated[int, PathParam(ge=0, lt=TEST_SAMPLE_COUNT)], request: Request) -> Response:
    artifacts: ModelArtifacts = request.app.state.artifacts
    output = BytesIO()
    Image.fromarray(artifacts.images[image_id]).save(output, format="PNG")
    return Response(output.getvalue(), media_type="image/png")
