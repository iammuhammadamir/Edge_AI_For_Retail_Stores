# Edge Device - Visitor Counter (Facial Recognition)

> **Last Updated**: December 11, 2025  
> **Status**: ✅ Production Ready - Server-Side Matching  
> **Backend**: https://dashboard.smoothflow.ai

---

## Quick Summary

This is the **edge device component** of the ClientBridge facial recognition system. It runs on a Jetson Nano (or Mac for development), captures faces from a camera, and sends embeddings to the cloud server for identification.

**Key Point**: No local database. The server is the single source of truth for all customer data.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     JETSON NANO (Edge Device)                    │
│                                                                  │
│  ┌──────────────┐                                               │
│  │   Camera     │  RTSP Stream (4K @ 15fps)                     │
│  │  (Tapo C212) │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  visitor_counter.py                                       │   │
│  │                                                           │   │
│  │  1. DETECT: Haar cascade (fast, triggers capture)        │   │
│  │  2. CAPTURE: 5 seconds of frames (~50 frames)            │   │
│  │  3. SCORE: Quality scoring (sharpness, frontality)       │   │
│  │  4. EXTRACT: InsightFace → 512-dim embedding             │   │
│  │  5. SEND: POST to server with embedding + photo          │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         │ HTTPS POST /api/edge/identify                         │
│         │ { embedding: [512 floats], imageBase64, locationId }  │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CLOUD (Vercel + Supabase)                    │
│                                                                  │
│  Server compares embedding against all customers:               │
│  - similarity > 0.45 → RETURNING (increment visits)             │
│  - similarity < 0.45 → NEW (create customer, save photo)        │
│                                                                  │
│  Response: { status: "new"|"returning", customerId, visitCount } │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Hardware

| Component | Details |
|-----------|---------|
| **Edge Device** | NVIDIA Jetson Orin Nano |
| **Camera** | Tapo C212 (Wi-Fi, 4K, pan/tilt) |
| **Stream URL** | `rtsp://admin:SmoothFlow@10.0.0.227:554/h264Preview_01_main` |
| **Processing** | 4K → resized to 1280x720 |

---

## Project Files

| File | Purpose |
|------|---------|
| `config.py` | **All configuration** - camera URL, API settings, thresholds |
| `visitor_counter.py` | **Main entry point** - detection loop, quality scoring, API calls |
| `api_client.py` | HTTP client for server communication |
| `face_recognition.py` | InsightFace wrapper - embedding extraction |
| `frame_quality.py` | Quality scoring (sharpness, frontality, brightness, contrast) |
| `requirements.txt` | Python dependencies |

---

## Configuration (`config.py`)

### Camera Settings
```python
RTSP_URL = "rtsp://admin:SmoothFlow@10.0.0.227:554/h264Preview_01_main"
TARGET_WIDTH = 1280              # Resize frames for processing
PROCESS_EVERY_N_FRAMES = 5       # Skip frames (~3 FPS effective)
```

### API Settings (Server Connection)
```python
API_BASE_URL = "https://dashboard.smoothflow.ai"  # Production server
API_KEY = "dev-edge-api-key"                       # Must match server's EDGE_API_KEY
API_LOCATION_ID = 1                                # Store location ID (from database)
```

### Recognition Settings
```python
SIMILARITY_THRESHOLD = 0.45      # Match threshold (server-side, but good to know)
COOLDOWN_SECONDS = 10            # Wait between captures (same person)
QUALITY_CAPTURE_DURATION_SEC = 5.0  # How long to capture frames
```

### Model Settings
```python
INSIGHTFACE_MODEL = "buffalo_s"  # "buffalo_s" (fast) or "buffalo_l" (accurate)

# Model directory (auto-detected)
# Jetson: /home/mafiq/zmisc/models/insightface
# Mac: ~/.insightface/models
```

---

## Quick Start

### On Jetson Nano
```bash
# 1. Copy this folder to Jetson
scp -r Edge_AI_For_Retail_Stores/ mafiq@jetson:/home/mafiq/

# 2. SSH into Jetson
ssh mafiq@jetson

# 3. Create virtual environment
cd Edge_AI_For_Retail_Stores
python3 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Edit config.py if needed (camera URL, location ID)
nano config.py

# 6. Run
python visitor_counter.py
```

### On Mac (Development)
```bash
# Use webcam instead of RTSP
python visitor_counter.py --webcam

# With debug output (saves reports to debug_output/)
python visitor_counter.py --webcam --debug
```

---

## Processing Flow (Detailed)

### Phase 1: Face Detection (~5-10ms)
- Uses **Haar Cascade** for fast initial detection
- Only triggers when face is present
- Runs on every 5th frame (~3 FPS)

### Phase 2: Frame Capture (~5000ms)
- Captures frames for 5 seconds after detection
- Keeps every 3rd frame (~50 frames total)
- Gives time for person to look at camera

### Phase 3: Quality Scoring (~300-500ms)
- Scores each frame on multiple metrics:
  - **Sharpness (30%)**: Laplacian variance
  - **Frontality (25%)**: Yaw/pitch angles
  - **Face Size (15%)**: Larger = better
  - **Brightness (15%)**: Not too dark/bright
  - **Contrast (15%)**: Good feature visibility
- Selects best frame for recognition

### Phase 4: Embedding Extraction (~50-100ms)
- Uses **InsightFace buffalo_s** model
- Extracts 512-dimensional face embedding
- Normalized vector for cosine similarity

### Phase 5: Server Identification (~500-1000ms)
- POST to `/api/edge/identify`
- Server compares against all customers
- Returns: new/returning, customer ID, visit count

### Cooldown (10 seconds)
- Prevents same person being counted multiple times
- Resumes scanning after cooldown

---

## API Communication

### Health Check
```bash
curl https://dashboard.smoothflow.ai/api/edge/health \
  -H "X-API-Key: dev-edge-api-key"

# Response: { "success": true, "message": "Edge API is healthy" }
```

### Identify (Main Endpoint)
```bash
curl -X POST https://dashboard.smoothflow.ai/api/edge/identify \
  -H "X-API-Key: dev-edge-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "embedding": [0.1, 0.2, ... 512 floats],
    "imageBase64": "base64-encoded-jpeg",
    "locationId": 1
  }'

# Response (new customer):
{ "success": true, "status": "new", "customerId": 5, "visitCount": 1 }

# Response (returning customer):
{ "success": true, "status": "returning", "customerId": 3, "visitCount": 7, "similarity": 0.82 }
```

---

## Multi-Store Setup

Each store has a unique `location_id` in the database. To set up a new store:

1. **Create location** in dashboard (owner login)
2. **Note the location ID** (e.g., 2)
3. **Update config.py** on that store's Jetson:
   ```python
   API_LOCATION_ID = 2  # This store's ID
   ```

Customers are scoped to locations - Store A's customers won't appear in Store B's dashboard.

---

## Multi-Camera Setup (Same Store)

**Current limitation**: One camera per process.

**Workaround**: Run multiple processes with different camera URLs:

```bash
# Terminal 1 - Entrance camera
RTSP_URL="rtsp://camera1..." python visitor_counter.py

# Terminal 2 - Exit camera  
RTSP_URL="rtsp://camera2..." python visitor_counter.py
```

Both will use the same `API_LOCATION_ID` and contribute to the same customer database.

---

## Known Issues / TODO

### Detection Accuracy
- **Haar Cascade** is old and misses some faces
- **Recommendation**: Replace with InsightFace's built-in detector (already loaded, better accuracy, similar speed)
- The detector is only used as a "wake up" trigger, not for final recognition

### Performance on Jetson
- First run downloads ~100MB model
- Model loading takes ~10-20 seconds
- After that, detection is fast (~5ms per frame)

### Network Dependency
- Requires internet connection to server
- If server unreachable, detection stops
- Could add offline queue for resilience (not implemented)

---

## Debug Mode

```bash
python visitor_counter.py --debug
```

Creates reports in `debug_output/`:
- `debug_YYYYMMDD_HHMMSS.md` - Quality scores for all frames
- `best_YYYYMMDD_HHMMSS.jpg` - Best frame with bounding box

Useful for tuning quality thresholds.

---

## Troubleshooting

### "API not reachable"
- Check internet connection
- Verify `API_BASE_URL` in config.py
- Verify `API_KEY` matches server's `EDGE_API_KEY`

### "Cannot connect to camera"
- Check camera is on same network
- Verify RTSP URL is correct
- Try opening stream in VLC first

### "No face found in best frame"
- Person may have moved too fast
- Try increasing `QUALITY_CAPTURE_DURATION_SEC`
- Check lighting conditions

### Low similarity scores
- Poor lighting or camera angle
- Try adjusting `SIMILARITY_THRESHOLD` (lower = more matches)
- Check if face is too small in frame

---

## Dependencies

```
opencv-python>=4.8.0
numpy>=1.24.0
insightface>=0.7.0
onnxruntime>=1.15.0
requests  # For API client
```

For Jetson with GPU acceleration, use `onnxruntime-gpu` instead of `onnxruntime`.
