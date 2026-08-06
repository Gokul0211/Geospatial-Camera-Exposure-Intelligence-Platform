FROM python:3.12-slim

# ─── Why separate from backend/Dockerfile ─────────────────────────────────
# ultralytics pulls in torch (~1-2 GB depending on CPU/GPU build).
# Keeping this as a separate image prevents the main API image from becoming
# huge and slow to rebuild during normal backend development.
# ──────────────────────────────────────────────────────────────────────────

# CPU-only torch build chosen here. If you have a GPU-enabled host:
#   Change FROM to: nvcr.io/nvidia/pytorch:24.01-py3
#   and remove the --extra-index-url line (GPU torch is bundled in that image).
#
# CPU-only is fine for demo/eval purposes on standard hardware.
# The pipeline processes pre-recorded footage, not live streams —
# so real-time GPU throughput is not a hard requirement.

WORKDIR /app

# Install system dependencies needed by OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch first (smaller, faster to build; avoids 2GB CUDA wheel)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Then install the rest (ultralytics, opencv-python-headless, httpx, python-dotenv)
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline source
COPY . .

# Create directory for sample footage (mount a volume here for real footage)
RUN mkdir -p sample_footage

# YOLOv8 model weights are downloaded on first run if not present.
# To pre-bake weights into the image (faster cold start):
#   RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
# Commented out to keep the image smaller for CI; uncomment for production.

ENV BACKEND_URL=http://backend:8000
ENV YOLO_MODEL=yolov8n.pt
ENV VIDEO_PIPELINE_LOG=INFO

# Run the orchestrator
CMD ["python", "main.py"]
