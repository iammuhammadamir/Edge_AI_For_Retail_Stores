# Face Detector - Internal Logic

## Overview

The system connects to an RTSP camera stream, detects faces, and saves frames when a face is detected.

---

## Frame Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MAIN LOOP                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   1. Read frame from RTSP stream (4K: 3840x2160)                            │
│                     │                                                        │
│                     ▼                                                        │
│   2. Skip frame? (process every 5th frame for performance)                  │
│         │                                                                    │
│         ├── YES → discard, go to step 1                                     │
│         │                                                                    │
│         └── NO ↓                                                            │
│                                                                              │
│   3. Resize frame to 1280x720 for processing                                │
│                     │                                                        │
│                     ▼                                                        │
│   4. Run YuNet face detection (~78ms)                                       │
│                     │                                                        │
│                     ▼                                                        │
│   5. Face detected?                                                          │
│         │                                                                    │
│         ├── NO → go to step 1                                               │
│         │                                                                    │
│         └── YES ↓                                                           │
│                                                                              │
│   6. Cooldown active? (5 seconds since last capture)                        │
│         │                                                                    │
│         ├── YES → go to step 1 (skip to avoid duplicate captures)           │
│         │                                                                    │
│         └── NO ↓                                                            │
│                                                                              │
│   7. CAPTURE SESSION:                                                        │
│      ┌──────────────────────────────────────────────────────────────────┐   │
│      │  Frame 1: The detection frame itself (GUARANTEED to have face)   │   │
│      │  Frame 2: Read new frame, wait 300ms                             │   │
│      │  Frame 3: Read new frame, wait 300ms                             │   │
│      │  Frame 4: Read new frame, wait 300ms                             │   │
│      │  Frame 5: Read new frame                                         │   │
│      └──────────────────────────────────────────────────────────────────┘   │
│                     │                                                        │
│                     ▼                                                        │
│   8. Set cooldown timer, go to step 1                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Behaviors

### Frame Skipping
- Camera streams at ~15 FPS
- We process every 5th frame → ~3 FPS effective detection rate
- Skipped frames are discarded (not buffered)

### Face Detection
- Uses YuNet model (OpenCV built-in)
- Input: 1280x720 resized frame
- Output: List of detected face bounding boxes
- Confidence threshold: 0.7 (70%)
- Processing time: ~78ms per frame on Jetson Orin Nano

### Capture Session
- **Frame 1**: The exact frame that triggered detection (guaranteed to contain face)
- **Frames 2-5**: Subsequent frames read from stream at 300ms intervals
- All frames resized to 1280x720 before saving
- Saved as JPEG to `/home/mafiq/zmisc/captures/`

### Cooldown
- After a capture session, 5-second cooldown before next capture
- Prevents capturing the same person multiple times as they walk past
- During cooldown, faces are still detected but no frames are saved

---

## Timing Breakdown

| Operation | Time | Notes |
|-----------|------|-------|
| Frame read | ~10-50ms | Depends on network/stream |
| Resize (4K→720p) | ~5.5ms | CPU-bound |
| Face detection | ~78ms | YuNet on CPU |
| **Total per processed frame** | ~85ms | |
| Effective processing FPS | ~12 FPS | But we only process every 5th frame |

### Response Time (face enters → detection triggers)

Worst case: `stream_latency + frame_skip_wait + detection_time`
- Stream latency: ~200-500ms (RTSP buffering)
- Frame skip wait: up to 333ms (5 frames at 15 FPS)
- Detection time: ~78ms

**Total worst case: ~900ms** from person entering frame to detection trigger.

---

## File Naming Convention

```
session_{YYYYMMDD_HHMMSS}_{session_number}_frame_{N}_{timestamp}.jpg

Example:
session_20251204_143314_0001_frame_1_20251204_143314_482.jpg
        └─────────┬────────┘    └─┬─┘ └─────────┬──────────┘
          session start time   frame#    actual capture time
```

---

## Configuration (top of face_detector.py)

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_WIDTH` | 1280 | Resize width for processing |
| `PROCESS_EVERY_N_FRAMES` | 5 | Skip N-1 frames between detections |
| `DETECTION_CONFIDENCE` | 0.7 | Minimum face detection confidence |
| `FRAMES_TO_CAPTURE` | 5 | Frames to save per session |
| `CAPTURE_INTERVAL_MS` | 300 | Delay between captured frames |
| `COOLDOWN_SECONDS` | 5 | Cooldown between capture sessions |
| `LOG_LEVEL` | DEBUG | Set to INFO for production |
