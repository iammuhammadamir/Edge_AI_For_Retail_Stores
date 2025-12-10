#!/usr/bin/env python3
"""
Configuration file for Visitor Counter System.
All hyperparameters and settings in one place.
"""

# =============================================================================
# CAMERA / STREAM SETTINGS
# =============================================================================

RTSP_URL: str = "rtsp://admin:SmoothFlow@10.0.0.227:554/h264Preview_01_main"

# Use 0 for Mac webcam during development
# RTSP_URL: int = 0

# =============================================================================
# PROCESSING SETTINGS
# =============================================================================

TARGET_WIDTH: int = 1280  # Resize frames to this width (maintains aspect ratio)
PROCESS_EVERY_N_FRAMES: int = 5  # Skip frames for performance (~3 FPS from 15 FPS)

# =============================================================================
# FRAME QUALITY CAPTURE SETTINGS
# =============================================================================

QUALITY_CAPTURE_DURATION_SEC: float = 5.0  # How long to capture after face detected
QUALITY_FRAME_SKIP: int = 3  # Keep every Nth frame during capture
QUALITY_TOP_N_FRAMES: int = 5  # Number of top frames to show in debug output

# Quality scoring - Multiplicative penalty system
# Each factor independently impacts the score via: score × factor^(importance/5)
# Importance scale: 0 = ignored, 5 = linear penalty, 10 = quadratic penalty
QUALITY_IMPORTANCE: dict = {
    'frontality': 8,    # Critical - angled faces match poorly
    'sharpness': 6,     # Important - blur hurts recognition
    'face_size': 3,     # Lower - don't penalize distant faces too harshly
    'brightness': 4,    # Some tolerance for lighting variation
    'contrast': 3,      # Lower priority - less critical
}

QUALITY_BASE_SCORE: float = 1000.0  # Starting score before penalties

# Face size scoring parameters (face width / frame width)
# Tune these based on your camera distance and setup
FACE_SIZE_MIN_RATIO: float = 0.02   # Below this = very small face (score ~0.4)
FACE_SIZE_GOOD_RATIO: float = 0.08  # Above this = perfect score (1.0)
FACE_SIZE_MIN_SCORE: float = 0.4    # Base score for faces at MIN_RATIO

# =============================================================================
# RECOGNITION SETTINGS
# =============================================================================

SIMILARITY_THRESHOLD: float = 0.45  # Cosine similarity threshold for matching
                                     # Lower = more matches (risk: merge different people)
                                     # Higher = fewer matches (risk: same person counted twice)

COOLDOWN_SECONDS: int = 10  # Wait time before processing next person

# =============================================================================
# QUALITY GATE THRESHOLDS (False Positive Prevention)
# =============================================================================

# Minimum quality score to proceed with recognition (out of 1000)
# Frames below this are skipped entirely (saves API calls)
MIN_QUALITY_SCORE: float = 350  # 50% of base score

# Minimum InsightFace detection confidence to send to API
# Lower confidence = less reliable embedding = potential false match
MIN_DETECTION_SCORE: float = 0.70

# =============================================================================
# MODEL SETTINGS
# =============================================================================

INSIGHTFACE_MODEL: str = "buffalo_s"  # "buffalo_s" (fast) or "buffalo_l" (accurate)

# Model cache directory (platform-specific)
import os
_HOME = os.path.expanduser("~")
if os.path.exists("/home/mafiq"):
    # Jetson
    MODEL_DIR: str = "/home/mafiq/zmisc/models/insightface"
else:
    # Mac / Development
    MODEL_DIR: str = os.path.join(_HOME, ".insightface/models")

# =============================================================================
# API SETTINGS (ClientBridge Website - Single Source of Truth)
# =============================================================================
# Server-side matching: Edge device sends embeddings, server does matching.
# No local database needed.

API_BASE_URL: str = "https://dashboard.smoothflow.ai"  # Production URL
API_KEY: str = "dev-edge-api-key"  # API key for authentication (must match EDGE_API_KEY on Vercel)
API_LOCATION_ID: int = 1  # Store location ID

# =============================================================================
# DEBUG SETTINGS
# =============================================================================

DEBUG_MODE: bool = False  # Enable debug output
DEBUG_OUTPUT_DIR: str = "debug_output"  # Directory for debug files
DEBUG_SAVE_ALL_FRAMES: bool = False  # Save all captured frames (disk intensive)
DEBUG_SAVE_TOP_FRAMES: bool = True  # Save top N frames with scores
DEBUG_GENERATE_REPORT: bool = True  # Generate debug.md report

# =============================================================================
# LOGGING
# =============================================================================

import logging
LOG_LEVEL: int = logging.DEBUG  # Set to logging.INFO for production
