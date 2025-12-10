#!/usr/bin/env python3
"""
Frame Quality Scoring Module
Scores frames based on face quality metrics for optimal recognition.

Metrics:
1. Face Size - Larger faces are better for recognition
2. Sharpness - Detect blur using Laplacian variance
3. Brightness - Avoid too dark or too bright faces
4. Contrast - Good contrast improves feature extraction
5. Frontality - Face should be front-facing (yaw/pitch near 0)
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass


@dataclass
class QualityScore:
    """Container for frame quality metrics."""
    total: float
    face_size: float
    sharpness: float
    brightness: float
    contrast: float
    frontality: float
    yaw: float  # Left/right rotation in degrees
    pitch: float  # Up/down rotation in degrees
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    
    def to_dict(self) -> Dict:
        return {
            'total': round(self.total, 3),
            'face_size': round(self.face_size, 3),
            'sharpness': round(self.sharpness, 3),
            'brightness': round(self.brightness, 3),
            'contrast': round(self.contrast, 3),
            'frontality': round(self.frontality, 3),
            'yaw': round(self.yaw, 1),
            'pitch': round(self.pitch, 1),
            'bbox': self.bbox
        }


# =============================================================================
# FACE DETECTION (Simple Haar Cascade for standalone testing)
# =============================================================================

_face_cascade = None
_eye_cascade = None

def get_face_detector():
    """Get or initialize face detector (Haar Cascade for simplicity)."""
    global _face_cascade
    if _face_cascade is None:
        _face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    return _face_cascade


def get_eye_detector():
    """Get or initialize eye detector for frontality estimation."""
    global _eye_cascade
    if _eye_cascade is None:
        _eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
    return _eye_cascade


def detect_face(frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """
    Detect the largest face in frame.
    
    Returns:
        (x1, y1, x2, y2) bounding box or None if no face found
    """
    detector = get_face_detector()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60)
    )
    
    if len(faces) == 0:
        return None
    
    # Return largest face
    largest = max(faces, key=lambda f: f[2] * f[3])
    x, y, w, h = largest
    return (x, y, x + w, y + h)


# =============================================================================
# QUALITY METRICS
# =============================================================================

def score_face_size(bbox: Tuple[int, int, int, int], frame_shape: Tuple[int, int]) -> float:
    """
    Score based on face size relative to frame.
    Larger faces are better for recognition.
    
    Returns:
        Score in [0, 1] range
    """
    x1, y1, x2, y2 = bbox
    face_area = (x2 - x1) * (y2 - y1)
    frame_area = frame_shape[0] * frame_shape[1]
    
    # Face should ideally be 5-30% of frame
    ratio = face_area / frame_area
    
    # Normalize: 0% -> 0, 15% -> 1, >30% -> 1
    if ratio < 0.01:
        return 0.0
    elif ratio < 0.15:
        return ratio / 0.15
    else:
        return 1.0


def score_sharpness(face_roi: np.ndarray) -> float:
    """
    Score based on image sharpness using Laplacian variance.
    Higher variance = sharper image.
    
    Returns:
        Score in [0, 1] range
    """
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    variance = laplacian.var()
    
    # Normalize: <50 is blurry, >500 is very sharp
    # Typical good face: 100-300
    score = min(variance / 300.0, 1.0)
    return score


def score_brightness(face_roi: np.ndarray) -> float:
    """
    Score based on brightness - penalize too dark or too bright.
    Optimal brightness is around 100-150 (out of 255).
    
    Returns:
        Score in [0, 1] range
    """
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
    mean_brightness = np.mean(gray)
    
    # Optimal range: 80-180
    # Score drops off outside this range
    if mean_brightness < 40:
        return mean_brightness / 40.0
    elif mean_brightness < 80:
        return 0.5 + 0.5 * (mean_brightness - 40) / 40.0
    elif mean_brightness <= 180:
        return 1.0
    elif mean_brightness <= 220:
        return 1.0 - 0.5 * (mean_brightness - 180) / 40.0
    else:
        return 0.5 - 0.5 * (mean_brightness - 220) / 35.0


def score_contrast(face_roi: np.ndarray) -> float:
    """
    Score based on contrast using standard deviation.
    Good contrast helps with feature extraction.
    
    Returns:
        Score in [0, 1] range
    """
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
    std_dev = np.std(gray)
    
    # Normalize: <20 is low contrast, >60 is good
    score = min(std_dev / 60.0, 1.0)
    return score


def estimate_head_pose(frame: np.ndarray, face_bbox: Tuple[int, int, int, int]) -> Optional[Tuple[float, float]]:
    """
    Estimate head pose (yaw, pitch) using eye detection and face geometry.
    
    This is a lightweight approach using OpenCV's Haar cascades:
    - Yaw: Estimated from eye positions relative to face center
    - Pitch: Estimated from eye vertical position in face bbox
    
    Returns:
        (yaw, pitch) in degrees, or None if eyes not detected
    """
    x1, y1, x2, y2 = face_bbox
    face_roi = frame[y1:y2, x1:x2]
    
    if face_roi.size == 0:
        return None
    
    gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
    face_w = x2 - x1
    face_h = y2 - y1
    
    # Detect eyes within face region
    eye_detector = get_eye_detector()
    eyes = eye_detector.detectMultiScale(
        gray_roi,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(int(face_w * 0.1), int(face_h * 0.05)),
        maxSize=(int(face_w * 0.5), int(face_h * 0.4))
    )
    
    # Filter eyes to only those in upper half of face
    upper_eyes = [e for e in eyes if e[1] < face_h * 0.5]
    
    if len(upper_eyes) < 2:
        # Can't estimate pose without both eyes
        # But we can still give a score based on face symmetry
        return estimate_pose_from_symmetry(gray_roi)
    
    # Sort eyes by x position (left to right)
    upper_eyes = sorted(upper_eyes, key=lambda e: e[0])
    
    # Take the two most separated eyes (likely left and right)
    if len(upper_eyes) > 2:
        # Find pair with maximum horizontal separation
        max_sep = 0
        best_pair = (upper_eyes[0], upper_eyes[1])
        for i in range(len(upper_eyes)):
            for j in range(i+1, len(upper_eyes)):
                sep = abs(upper_eyes[j][0] - upper_eyes[i][0])
                if sep > max_sep:
                    max_sep = sep
                    best_pair = (upper_eyes[i], upper_eyes[j])
        left_eye, right_eye = best_pair
    else:
        left_eye, right_eye = upper_eyes[0], upper_eyes[1]
    
    # Eye centers
    left_center_x = left_eye[0] + left_eye[2] / 2
    left_center_y = left_eye[1] + left_eye[3] / 2
    right_center_x = right_eye[0] + right_eye[2] / 2
    right_center_y = right_eye[1] + right_eye[3] / 2
    
    # Compute yaw from eye positions
    # If face is frontal, eyes should be symmetric around face center
    eye_center_x = (left_center_x + right_center_x) / 2
    face_center_x = face_w / 2
    
    # Yaw: deviation of eye center from face center
    # Normalized by face width, scaled to degrees
    yaw = ((eye_center_x - face_center_x) / face_w) * 60
    
    # Compute pitch from eye vertical position
    # Eyes should be at ~30-35% from top of face bbox for frontal
    eye_center_y = (left_center_y + right_center_y) / 2
    expected_eye_y = face_h * 0.32  # Expected position for frontal face
    
    # Pitch: deviation from expected eye position
    pitch = ((eye_center_y - expected_eye_y) / face_h) * 50
    
    # Also check eye level (roll indicator, but affects frontality)
    eye_slope = (right_center_y - left_center_y) / max(right_center_x - left_center_x, 1)
    roll_penalty = abs(eye_slope) * 20  # Add to pitch as penalty
    
    return (yaw, pitch + roll_penalty * 0.3)


def estimate_pose_from_symmetry(gray_face: np.ndarray) -> Tuple[float, float]:
    """
    Fallback pose estimation using face symmetry.
    A frontal face should be roughly symmetric left-to-right.
    
    Returns:
        (yaw, pitch) estimates in degrees
    """
    h, w = gray_face.shape
    
    # Split face into left and right halves
    left_half = gray_face[:, :w//2]
    right_half = gray_face[:, w//2:]
    right_half_flipped = cv2.flip(right_half, 1)
    
    # Resize to same size if needed
    min_w = min(left_half.shape[1], right_half_flipped.shape[1])
    left_half = left_half[:, :min_w]
    right_half_flipped = right_half_flipped[:, :min_w]
    
    # Compute difference (asymmetry)
    diff = cv2.absdiff(left_half, right_half_flipped)
    asymmetry = np.mean(diff) / 255.0  # Normalize to 0-1
    
    # Higher asymmetry suggests turned face
    # Map to approximate yaw (very rough estimate)
    yaw = asymmetry * 45  # Max ~45 degrees for high asymmetry
    
    # Can't estimate pitch from symmetry alone
    pitch = 0
    
    return (yaw, pitch)


def score_frontality(yaw: float, pitch: float) -> float:
    """
    Score based on how frontal the face is.
    
    Args:
        yaw: Left/right rotation in degrees
        pitch: Up/down rotation in degrees
    
    Returns:
        Score in [0, 1] range. 1.0 = perfectly frontal
    """
    # Penalize deviation from frontal
    # Allow some tolerance: ±10° is still good
    # Beyond ±30° is poor
    
    yaw_penalty = min(abs(yaw) / 30.0, 1.0)
    pitch_penalty = min(abs(pitch) / 30.0, 1.0)
    
    # Combined score (both need to be good)
    score = 1.0 - (0.6 * yaw_penalty + 0.4 * pitch_penalty)
    
    return max(0.0, score)


# =============================================================================
# MAIN SCORING FUNCTION
# =============================================================================

def compute_quality_score(
    frame: np.ndarray,
    bbox: Optional[Tuple[int, int, int, int]] = None,
    weights: Dict[str, float] = None
) -> Optional[QualityScore]:
    """
    Compute overall quality score for a frame.
    
    Args:
        frame: BGR image
        bbox: Optional face bounding box. If None, will detect face.
        weights: Optional custom weights for each metric
    
    Returns:
        QualityScore object or None if no face found
    """
    if weights is None:
        weights = {
            'face_size': 0.15,
            'sharpness': 0.30,  # Important for recognition
            'brightness': 0.15,
            'contrast': 0.15,
            'frontality': 0.25  # Very important - frontal faces match better
        }
    
    # Detect face if bbox not provided
    if bbox is None:
        bbox = detect_face(frame)
        if bbox is None:
            return None
    
    x1, y1, x2, y2 = bbox
    
    # Add padding to face ROI (10% on each side)
    h, w = frame.shape[:2]
    pad_x = int((x2 - x1) * 0.1)
    pad_y = int((y2 - y1) * 0.1)
    x1_pad = max(0, x1 - pad_x)
    y1_pad = max(0, y1 - pad_y)
    x2_pad = min(w, x2 + pad_x)
    y2_pad = min(h, y2 + pad_y)
    
    face_roi = frame[y1_pad:y2_pad, x1_pad:x2_pad]
    
    if face_roi.size == 0:
        return None
    
    # Compute individual scores
    size_score = score_face_size(bbox, frame.shape[:2])
    sharp_score = score_sharpness(face_roi)
    bright_score = score_brightness(face_roi)
    contrast_score = score_contrast(face_roi)
    
    # Compute head pose for frontality
    pose = estimate_head_pose(frame, bbox)
    if pose is not None:
        yaw, pitch = pose
        frontal_score = score_frontality(yaw, pitch)
    else:
        # If pose estimation fails, assume neutral
        yaw, pitch = 0.0, 0.0
        frontal_score = 0.5  # Uncertain, give middle score
    
    # Weighted total
    total = (
        weights['face_size'] * size_score +
        weights['sharpness'] * sharp_score +
        weights['brightness'] * bright_score +
        weights['contrast'] * contrast_score +
        weights['frontality'] * frontal_score
    )
    
    return QualityScore(
        total=total,
        face_size=size_score,
        sharpness=sharp_score,
        brightness=bright_score,
        contrast=contrast_score,
        frontality=frontal_score,
        yaw=yaw,
        pitch=pitch,
        bbox=bbox
    )


def score_frames(frames: List[np.ndarray]) -> List[Tuple[int, np.ndarray, QualityScore]]:
    """
    Score multiple frames and return sorted by quality.
    
    Args:
        frames: List of BGR images
    
    Returns:
        List of (frame_index, frame, score) tuples, sorted by total score descending
    """
    results = []
    
    for i, frame in enumerate(frames):
        score = compute_quality_score(frame)
        if score is not None:
            results.append((i, frame, score))
    
    # Sort by total score descending
    results.sort(key=lambda x: x[2].total, reverse=True)
    
    return results


def get_best_frame(frames: List[np.ndarray]) -> Optional[Tuple[np.ndarray, QualityScore]]:
    """
    Get the best quality frame from a list.
    
    Returns:
        (best_frame, score) or None if no faces found
    """
    scored = score_frames(frames)
    if not scored:
        return None
    return (scored[0][1], scored[0][2])
