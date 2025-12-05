# Facial Matching - Design Decisions

## Overview

This document captures the design decisions for the facial recognition and visitor matching system.

---

## Current Scope (Pilot Project)

- **Duration**: 1 month pilot
- **Expected visitors**: 500-1000 unique individuals
- **Priority**: Quality over scalability
- **Data growth**: Not a concern for pilot

---

## Design Decisions

### 1. Matching Threshold

**Decision**: Use balanced threshold of **0.45** (cosine similarity)

| Threshold | Behavior |
|-----------|----------|
| < 0.40 | Aggressive matching - risks merging different people |
| 0.40-0.50 | Balanced - our choice |
| > 0.50 | Conservative - risks counting same person twice |

**Rationale**: For a loyalty program, it's better to slightly under-match (miss some returning visitors) than over-match (merge two different people into one profile).

### 2. Enrollment Strategy

**Decision**: Auto-enrollment on first sighting

- When a face is detected with no match above threshold → create new visitor
- No manual enrollment required
- First captured image saved as reference

**Future**: Human-in-the-loop for near-misses (similarity 0.35-0.45), similar to Google Photos "Are these the same person?" prompts.

### 3. Multiple Faces in Frame

**Decision**: Sequential processing of all faces

- If multiple faces detected, process each one independently
- Each face gets matched/enrolled separately
- Acceptable latency since not time-sensitive

### 4. Same Person, Different Appearances

**Decision**: Let the algorithm handle naturally

- No special handling for hats, glasses, lighting changes
- ArcFace model is reasonably robust to these variations
- Accept some misses as part of "mediocre accuracy acceptable" requirement

### 5. Privacy/PII

**Decision**: Not addressed in pilot

- Face embeddings stored in plain SQLite
- No encryption at rest
- No consent flow
- **Must revisit before production deployment**

### 6. Storage

**Decision**: Local SQLite database

- Simple, no server dependencies
- Sufficient for 500-1000 visitors
- Schema:
  ```sql
  visitors (id, embedding, visit_count, first_seen, last_seen, sample_image_path)
  visits (id, visitor_id, timestamp, session_id, confidence)
  ```

### 7. Embedding Model

**Decision**: InsightFace with `buffalo_s` model

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| buffalo_s | ~30MB | Fast | Good |
| buffalo_l | ~100MB | Slower | Better |

**Rationale**: `buffalo_s` provides good balance for edge deployment on Jetson Orin Nano. Can upgrade to `buffalo_l` if accuracy issues arise.

### 8. Cooldown Period

**Decision**: 10 seconds between captures

- Prevents counting same person multiple times as they walk past
- Longer than detection-only cooldown (was 5s) because recognition is more expensive
- Person should have time to leave frame before next detection

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VISITOR COUNTER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   RTSP Stream (4K) ──► Resize (1280x720) ──► InsightFace                    │
│                                                    │                         │
│                                    ┌───────────────┴───────────────┐        │
│                                    │                               │        │
│                              Face Detected?                   No Face       │
│                                    │                          (skip)        │
│                                    ▼                                        │
│                           Extract Embedding                                  │
│                           (512-dim vector)                                  │
│                                    │                                        │
│                                    ▼                                        │
│                    ┌─────── Match Against DB ───────┐                       │
│                    │                                │                       │
│              Match Found                      No Match                      │
│           (similarity ≥ 0.45)             (similarity < 0.45)              │
│                    │                                │                       │
│                    ▼                                ▼                       │
│           Increment Visit Count           Create New Visitor                │
│           Update last_seen                Store embedding                   │
│                                           Save sample image                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Files

| File | Purpose |
|------|---------|
| `visitor_counter.py` | Main application - detection + recognition + counting |
| `face_recognition.py` | InsightFace wrapper - embedding extraction & matching |
| `database.py` | SQLite operations - visitor storage & queries |
| `visitors.db` | SQLite database file |
| `visitor_images/` | Sample images of enrolled visitors |

---

## Performance Expectations

Based on Jetson Orin Nano with CPU inference:

| Operation | Expected Time |
|-----------|---------------|
| Frame resize | ~5-6 ms |
| Face detection + embedding | ~150-300 ms |
| Database lookup (1000 visitors) | ~1-2 ms |
| **Total per frame** | ~160-310 ms |

Effective throughput: ~3-6 processed frames per second (but we only process every 5th frame from 15 FPS stream).

---

## Usage

```bash
# Activate environment
source /home/mafiq/zmisc/venv/bin/activate

# Run visitor counter
python /home/mafiq/zmisc/visitor_counter.py

# Test face recognition on an image
python /home/mafiq/zmisc/face_recognition.py /path/to/image.jpg
```

---

## Future Improvements (Post-Pilot)

1. **Human-in-the-loop**: Review near-miss matches (0.35-0.45 similarity)
2. **Multiple embeddings per person**: Handle appearance variations
3. **GPU acceleration**: Use onnxruntime-gpu for faster inference
4. **Privacy**: Encrypt embeddings, add consent flow
5. **API integration**: Send visit data to client's backend
6. **Dashboard**: Web UI for viewing visitor stats
