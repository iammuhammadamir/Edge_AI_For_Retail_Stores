# Retail Store Visitor Counter

## Project Overview

Client is building a customer loyalty solution for large retail stores. The system counts and identifies unique visitors using a camera at the store entrance.

---

## Hardware Setup

- **Edge Device**: NVIDIA Jetson Orin Nano
- **Camera**: Tapo C212 (Wi-Fi, 4K, pan/tilt)
- **Connection**: RTSP stream at `rtsp://admin:SmoothFlow@10.0.0.227:554/h264Preview_01_main`
- **Resolution**: 3840x2160 (4K), resized to 1280x720 for processing

---

## Current System (Working on Jetson)

### Architecture
```
RTSP Stream (4K @ 15fps)
    ↓
Resize to 1280x720
    ↓
Process every 5th frame (~3 FPS effective)
    ↓
InsightFace (buffalo_s model)
    - Face detection
    - 512-dim embedding extraction
    ↓
Cosine similarity matching against SQLite DB
    ↓
If similarity ≥ 0.45 → Returning visitor (increment count)
If similarity < 0.45 → New visitor (enroll)
```

### Files
| File | Purpose |
|------|---------|
| `visitor_counter.py` | Main application - continuous visitor counting |
| `face_recognition.py` | InsightFace wrapper - embedding extraction & matching |
| `database.py` | SQLite storage for visitor embeddings |
| `test_matching.py` | Interactive testing script for demos |
| `requirements.txt` | Python dependencies |

### Key Parameters
- **Similarity threshold**: 0.45 (cosine similarity)
- **Cooldown**: 10 seconds between captures
- **Model**: InsightFace `buffalo_s` (fast, ~80ms per frame on CPU)

### Performance (Jetson Orin Nano, CPU)
- Resize: ~5ms
- Face detection + embedding: ~80-100ms
- Total: ~85-105ms per processed frame

---

## Problem: Frame Quality

**Issue**: The frame captured for recognition may not be optimal:
- Face at angle (not frontal)
- Motion blur
- Poor lighting
- Face too small/far

**Current behavior**: Uses whatever frame triggered detection, which may be suboptimal for matching or enrollment.

---

## Next Task: Frame Quality Selection (Mac Development)

### Goal
Build a frame quality scoring system to select the best frame for:
1. **Matching**: Compare against stored embeddings using best-quality frame
2. **Enrollment**: Store the best-quality frame as reference for new visitors

### Approach
1. When face detected, capture 2-3 seconds of frames (or N frames at intervals)
2. Score each frame on quality metrics:
   - **Face frontality** (yaw/pitch angles via MediaPipe or InsightFace landmarks)
   - **Face size** (bounding box area - larger is better)
   - **Sharpness** (Laplacian variance - detect blur)
   - **Brightness** (avoid too dark/bright)
3. Select highest-scoring frame for recognition/enrollment

### Why Mac First?
- Faster iteration with local webcam
- No network latency to remote Jetson
- Once algorithm works, transfer to Jetson

### Files to Create on Mac
```
frame_quality.py      # Quality scoring functions
quality_test.py       # Interactive test with Mac webcam
```

### Transfer Back to Jetson
Once quality scoring works on Mac:
1. Copy `frame_quality.py` to Jetson
2. Integrate into `visitor_counter.py`
3. Modify detection loop to:
   - Capture N frames on face detection
   - Score frames
   - Use best frame for matching/enrollment

---

## Setup Instructions (Mac)

### 1. Extract and Setup
```bash
unzip visitor_counter.zip -d visitor_counter
cd visitor_counter
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Test Face Recognition (Mac Webcam)
The `test_matching.py` script needs modification to use Mac webcam instead of RTSP.
Change `RTSP_URL` to `0` (default webcam):
```python
# In test_matching.py, change:
RTSP_URL = 0  # Use Mac webcam
```

### 3. Develop Quality Scoring
Create `frame_quality.py` with scoring functions, then integrate into test script.

---

## Database Schema
```sql
visitors (
    id INTEGER PRIMARY KEY,
    embedding BLOB,           -- 512-dim float32 vector
    visit_count INTEGER,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    sample_image_path TEXT
)
```

---

## Dependencies
```
opencv-python>=4.8.0
numpy>=1.24.0
insightface>=0.7.0
onnxruntime>=1.15.0
```

Optional for quality scoring:
```
mediapipe  # For face mesh / head pose
```

---

## Summary for Next LLM

**What exists**: Working visitor counter on Jetson with face detection, embedding extraction, and similarity matching.

**Current problem**: Frame quality is not considered - using whatever frame triggers detection.

**Your task**: 
1. Build frame quality scoring (`frame_quality.py`)
2. Test with Mac webcam
3. Score frames on: frontality, size, sharpness, brightness
4. Select best frame for matching/enrollment

**End goal**: Integrate quality scoring into `visitor_counter.py` on Jetson for more accurate visitor recognition.
