FROM python:3.12-slim

WORKDIR /app
ENV MODEL_DIR=/models \
    OMP_NUM_THREADS=1 \
    PYTHONUNBUFFERED=1

COPY common/requirements.txt common/requirements.txt
COPY inference/requirements.txt inference/requirements.txt
RUN python -m pip install --no-cache-dir -r inference/requirements.txt

COPY common/ common/
COPY inference/ inference/
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "inference.app:app", "--host", "0.0.0.0", "--port", "8000"]
