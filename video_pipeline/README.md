# COBRA-WATCH — Video AI Detection Pipeline

## Overview

This is the video AI processing service for COBRA-WATCH. It is a **completely separate service** from the FastAPI backend — they communicate only via HTTP (`POST /api/detection-event`). They share no Python imports, no database connection, and no Docker image.

## Hard Ethical/Legal Boundary

> **This pipeline only processes footage from `sample_footage/` or explicitly whitelisted test feed URLs in `config.py`.**
>
> It **never** connects to, pulls frames from, or records any live stream from a device discovered via the Shodan/OSINT pipeline. Those are real third-party devices. Passive knowledge that an IP is exposed (OSINT research) is categorically different from actually viewing or recording that device's video feed (unauthorized access). `detector.py` enforces this by construction via `_assert_source_is_authorized()` — it raises `ValueError` if a source is not registered in `config.FOOTAGE_CAMERA_MAP`.

## Directory Structure

```
video_pipeline/
├── config.py            # All configuration — backend URL, model path, zones, footage map
├── detector.py          # YOLOv8 inference wrapper (with source authorization enforcement)
├── tracker.py           # ByteTrack object tracking on top of detector.py
├── rules.py             # Rule engine (loitering + perimeter breach) — no ML deps
├── main.py              # Orchestrator: reads footage → detects → tracks → fires events
├── Dockerfile           # Separate image (CPU-only torch; see note below on GPU)
├── requirements.txt     # Separate requirements (ultralytics/torch NOT in backend/)
├── sample_footage/      # Place demo video clips here (see "Demo Footage" below)
└── tests/
    └── test_rules.py    # Unit tests — zero ML/video deps, runs without any model files
```

## Demo Footage — Source & Licensing

The demo/evaluation footage used for this project falls into the following categories:

### Self-recorded test clips (`demo_loitering.mp4`, `demo_perimeter.mp4`)
- **Source:** Self-recorded by the team in a public/semi-public area with no identifiable individuals in frame.
- **License:** Team-owned. May be freely used for academic research purposes.
- **Privacy:** No faces or identifying features retained in clips used for evaluation.

### Public Research Datasets (used for evaluation/benchmarking)
The following **publicly available** surveillance research datasets are suitable for use:

| Dataset | Source | License |
|---|---|---|
| VIRAT Ground Dataset | https://viratdata.org/ | Research use permitted (see VIRAT license) |
| UCSD Anomaly Detection | http://www.svcl.ucsd.edu/projects/anomaly/dataset.htm | Research use |
| AVSS 2007 | IEEE AVSS Challenge dataset | Research use |
| MOT Challenge (pedestrian) | https://motchallenge.net/ | Research/academic |

> **Important for the report:** State explicitly which dataset your evaluation runs were performed against, its license, and that no footage from any discovered device was used. This section is where that documentation lives.

### Mapping footage to camera IDs
In `config.py`, `FOOTAGE_CAMERA_MAP` maps each video file to a `camera_id` from the seeded devices table. This mapping is the mechanism that makes the end-to-end trust score demo meaningful:
- The video footage triggers a detection event on a specific `camera_id`
- That `camera_id` has real `auth_required`, `known_cve_count`, `owner_type`, and `last_patch_date` fields in the database (populated by Phases 1 and 2)
- The trust score computed is therefore a real, data-driven score — not a hardcoded demo value

To set up the mapping:
1. Run `python scripts/seed_demo_data.py` from the project root to populate devices
2. Run `sqlite3 backend/data/surveillancewatch.db "SELECT id, city, manufacturer FROM devices LIMIT 10;"` to get real IDs
3. Update `FOOTAGE_CAMERA_MAP` in `config.py` with those IDs

## Running Locally

```bash
# 1. Install dependencies (separate from backend — do NOT run from backend/)
cd video_pipeline
pip install -r requirements.txt

# 2. Place sample footage in video_pipeline/sample_footage/

# 3. Start the backend first (from backend/)
cd ../backend
uvicorn main:app --reload

# 4. Run the pipeline (from video_pipeline/)
cd ../video_pipeline
python main.py
```

## Running with Docker Compose

Uncomment the `video-pipeline` service in the project root `docker-compose.yml` (added in Phase 4), then:

```bash
# From project root
docker-compose up
```

The video pipeline container will:
1. Wait up to 30 seconds for the backend container to become healthy
2. Process each footage entry in `FOOTAGE_CAMERA_MAP`
3. POST detection events to `http://backend:8000/api/detection-event`
4. Exit cleanly when all footage is processed

## Docker: CPU vs GPU

The `Dockerfile` uses **CPU-only PyTorch** by default:
- Suitable for: demo/eval on standard laptops, CI, cloud VMs without GPU
- Suitable for: processing pre-recorded footage (no real-time constraint)
- Image size: ~2.5 GB (torch CPU + ultralytics + opencv)

To switch to GPU:
1. Change `FROM python:3.12-slim` to `FROM nvcr.io/nvidia/pytorch:24.01-py3`
2. Remove the `--index-url https://download.pytorch.org/whl/cpu` pip install line
3. Uncomment the CUDA-capable runtime in `docker-compose.yml`

## Running Tests (no GPU/model needed)

```bash
# From project root:
python -m pytest video_pipeline/tests/test_rules.py -v

# Or from video_pipeline/:
cd video_pipeline
python -m pytest tests/test_rules.py -v
```

The rule tests use only synthetic track histories — no model weights, no video files, no ultralytics import required.
