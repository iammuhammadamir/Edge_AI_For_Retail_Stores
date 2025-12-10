# Technical Design & Logic

## Frame Quality Scoring System

### Why Quality Scoring?

The original system used whatever frame triggered detection, which could be:
- Face at an angle (not frontal)
- Motion blur
- Poor lighting
- Face too small/far

**Solution**: Capture multiple frames after detection, score them, and use the best one.

---

## Quality Metrics

### 1. Sharpness (30% weight)
```python
# Laplacian variance - higher = sharper
gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
laplacian = cv2.Laplacian(gray, cv2.CV_64F)
variance = laplacian.var()

# Score: normalized to 0-1, optimal around variance=500
score = min(variance / 500, 1.0)
```

### 2. Frontality (25% weight)
```python
# Eye detection + symmetry analysis
# Uses Haar cascade for eye detection
# Estimates yaw from eye positions relative to face center
# Estimates pitch from eye vertical position

# Fallback: face symmetry (left-right comparison)
yaw = ((eye_center_x - face_center_x) / face_w) * 60  # degrees
pitch = ((eye_center_y - expected_eye_y) / face_h) * 50  # degrees

# Score: 1.0 for frontal (yaw=0, pitch=0), decreases with angle
score = max(0, 1.0 - (abs(yaw)/45 + abs(pitch)/30) / 2)
```

### 3. Face Size (15% weight)
```python
# Larger faces = better recognition
face_area = (x2 - x1) * (y2 - y1)
frame_area = frame_h * frame_w
ratio = face_area / frame_area

# Score: 1.0 if face is 10%+ of frame
score = min(ratio / 0.10, 1.0)
```

### 4. Brightness (15% weight)
```python
# Optimal brightness around 127 (middle of 0-255)
mean_brightness = np.mean(gray_face)
deviation = abs(mean_brightness - 127) / 127

# Score: 1.0 at optimal, 0.0 at extremes
score = 1.0 - deviation
```

### 5. Contrast (15% weight)
```python
# Standard deviation of pixel values
std_dev = np.std(gray_face)

# Score: normalized, optimal around std=50
score = min(std_dev / 50, 1.0)
```

---

## Design Decisions

### Why Haar Cascade for Detection?
- **Fast**: ~7ms vs ~80ms for InsightFace
- **Sufficient**: Only need to know IF a face exists, not precise landmarks
- **Lightweight**: No GPU needed for initial detection

### Why OpenCV for Frontality (not MediaPipe)?
- **Python 3.13+ compatibility**: MediaPipe doesn't support Python 3.13+
- **Simpler**: Eye detection + symmetry is sufficient for quality scoring
- **No extra dependencies**: Uses built-in Haar cascades

### Why 5 Seconds Capture Duration?
- **Enough variation**: Person likely moves, blinks, changes expression
- **Not too long**: Don't want to miss next person
- **Configurable**: `QUALITY_CAPTURE_DURATION_SEC` in `config.py`

### Why Every 3rd Frame?
- **Reduces processing**: ~50 frames instead of ~150
- **Still captures variation**: 3 frames apart at 30fps = 100ms apart
- **Configurable**: `QUALITY_FRAME_SKIP` in `config.py`

---

## Timing Breakdown (Mac M-series)

| Phase | Time | Notes |
|-------|------|-------|
| Detection (Haar) | ~7ms | Fast initial check |
| Frame Capture | ~5000ms | Configurable duration |
| Quality Scoring | ~260ms | All captured frames |
| Embedding (InsightFace) | ~40ms | Best frame only |
| **Total** | ~5.3s | Per person |

---

## Configuration Reference (`config.py`)

### Frame Quality
| Variable | Default | Description |
|----------|---------|-------------|
| `QUALITY_CAPTURE_DURATION_SEC` | 5.0 | Capture duration after detection |
| `QUALITY_FRAME_SKIP` | 3 | Keep every Nth frame |
| `QUALITY_TOP_N_FRAMES` | 5 | Frames to show in debug report |
| `QUALITY_WEIGHTS` | dict | Weight for each metric |

### Recognition
| Variable | Default | Description |
|----------|---------|-------------|
| `SIMILARITY_THRESHOLD` | 0.45 | Cosine similarity for matching |
| `COOLDOWN_SECONDS` | 10 | Wait between captures |
| `INSIGHTFACE_MODEL` | "buffalo_s" | Model name (buffalo_s or buffalo_l) |

### Processing
| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_WIDTH` | 1280 | Resize width for processing |
| `PROCESS_EVERY_N_FRAMES` | 5 | Skip frames for performance |

### Debug
| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_MODE` | False | Enable debug output |
| `DEBUG_OUTPUT_DIR` | "debug_output" | Where to save reports |
| `DEBUG_SAVE_TOP_FRAMES` | True | Save annotated best frames |
| `DEBUG_GENERATE_REPORT` | True | Generate markdown reports |

---

## Debug Output

When `--debug` flag is used, generates:

```
debug_output/
├── debug_20251206_020905.md    # Full report with embedded images
├── best_20251206_020905.jpg    # Best frame with face box
├── debug_20251206_020922.md    # Next detection...
└── best_20251206_020922.jpg
```

Each report includes:
- Session metadata (frames captured, faces detected)
- Best frame score breakdown
- Top N frames with scores and embedded images

---

## Future Improvements

1. **Multi-person handling**: Queue system for concurrent detections
2. **GPU acceleration**: Use CUDA on Jetson for faster inference
3. **Adaptive thresholds**: Adjust based on lighting conditions
4. **Embedding averaging**: Use multiple frames to create robust embedding
