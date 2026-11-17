FROM python:3.12-slim

WORKDIR /app
ENV MODEL_DIR=/models \
    OMP_NUM_THREADS=2 \
    PYTHONUNBUFFERED=1

COPY common/requirements.txt common/requirements.txt
COPY training/requirements.txt training/requirements.txt
RUN python -m pip install --no-cache-dir -r training/requirements.txt

COPY common/ common/
COPY training/ training/
CMD ["python", "-m", "training.train"]
