# Mac to Jetson Transfer Guide

## Overview

Develop on Mac with webcam, deploy to Jetson with RTSP camera.

---

## Prerequisites

### Jetson Setup
```bash
# SSH into Jetson
ssh mafiq@<jetson-ip>

# Create project directory
mkdir -p ~/zmisc/visitor_counter
mkdir -p ~/zmisc/models/insightface
mkdir -p ~/zmisc/visitor_images

# Create venv (Python 3.9-3.12 required)
python3 -m venv ~/zmisc/visitor_counter/venv
source ~/zmisc/visitor_counter/venv/bin/activate
pip install opencv-python numpy insightface onnxruntime
```

---

## Transfer Files

### Option 1: SCP (Simple)
```bash
# From Mac, transfer project files
scp -r *.py requirements.txt mafiq@<jetson-ip>:~/zmisc/visitor_counter/
```

### Option 2: Git (Recommended)
```bash
# On Mac - commit changes
git add .
git commit -m "Ready for Jetson deployment"
git push

# On Jetson - pull changes
cd ~/zmisc/visitor_counter
git pull
```

---

## Configuration Changes

The `config.py` auto-detects platform:

```python
# Automatic path detection
if os.path.exists("/home/mafiq"):
    # Jetson paths
    MODEL_DIR = "/home/mafiq/zmisc/models/insightface"
    OUTPUT_DIR = "/home/mafiq/zmisc/visitor_images"
    DB_PATH = "/home/mafiq/zmisc/visitors.db"
else:
    # Mac paths (development)
    MODEL_DIR = "~/.insightface/models"
    OUTPUT_DIR = "visitor_images"
    DB_PATH = "visitors.db"
```

**No manual changes needed** - just run without `--webcam` flag.

---

## Running on Jetson

```bash
# Activate venv
source ~/zmisc/visitor_counter/venv/bin/activate

# Run with RTSP camera (production)
python visitor_counter.py

# Run with debug output
python visitor_counter.py --debug

# Run in background (production)
nohup python visitor_counter.py > visitor.log 2>&1 &
```

---

## Verify RTSP Connection

```bash
# Test camera stream
ffprobe rtsp://admin:SmoothFlow@10.0.0.227:554/h264Preview_01_main

# Or with OpenCV
python -c "import cv2; cap=cv2.VideoCapture('rtsp://admin:SmoothFlow@10.0.0.227:554/h264Preview_01_main'); print('OK' if cap.isOpened() else 'FAIL')"
```

---

## Reset Database

```bash
# Mac
rm visitors.db

# Jetson
rm /home/mafiq/zmisc/visitors.db
```

---

## Troubleshooting

### "Cannot connect to camera"
- Check RTSP URL in `config.py`
- Verify camera is on same network
- Test with `ffprobe` command above

### "No module named 'insightface'"
- Activate venv: `source venv/bin/activate`
- Reinstall: `pip install insightface onnxruntime`

### "Model download fails"
- Check internet connection
- Manually download model to `MODEL_DIR`

### Slow performance on Jetson
- Reduce `TARGET_WIDTH` (e.g., 960)
- Increase `PROCESS_EVERY_N_FRAMES` (e.g., 10)
- Reduce `QUALITY_CAPTURE_DURATION_SEC` (e.g., 3.0)

---

## Quick Reference

| Task | Mac | Jetson |
|------|-----|--------|
| Run | `python visitor_counter.py --webcam` | `python visitor_counter.py` |
| Debug | `--debug` flag | `--debug` flag |
| Reset DB | `rm visitors.db` | `rm /home/mafiq/zmisc/visitors.db` |
| Logs | Terminal output | `tail -f visitor.log` |
