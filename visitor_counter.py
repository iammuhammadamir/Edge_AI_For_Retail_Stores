#!/usr/bin/env python3
"""
Visitor Counter - Main Application
Detects faces, extracts embeddings, matches against known visitors, and counts visits.
"""

import cv2
import time
import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Optional

import database as db
from face_recognition import (
    extract_embeddings,
    find_best_match,
    get_face_analyzer,
    SIMILARITY_THRESHOLD
)

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_LEVEL = logging.DEBUG  # Set to logging.INFO for production

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

RTSP_URL = "rtsp://admin:SmoothFlow@10.0.0.227:554/h264Preview_01_main"

# Processing settings
TARGET_WIDTH = 1280  # Resize to this width for processing
PROCESS_EVERY_N_FRAMES = 5  # Process every Nth frame

# Cooldown to avoid counting same person multiple times
COOLDOWN_SECONDS = 10  # Increased for recognition (person needs to leave frame)

# Output settings
OUTPUT_DIR = "/home/mafiq/zmisc/visitor_images"
DEBUG_DIR = "/home/mafiq/zmisc/debug/visitor_counter"

# =============================================================================
# HELPERS
# =============================================================================

def resize_frame(frame, target_width):
    """Resize frame maintaining aspect ratio."""
    h, w = frame.shape[:2]
    scale = target_width / w
    new_h = int(h * scale)
    return cv2.resize(frame, (target_width, new_h))

def save_visitor_image(frame, visitor_id: int, session_id: str) -> str:
    """Save a sample image for a visitor."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{OUTPUT_DIR}/visitor_{visitor_id}_{session_id}_{timestamp}.jpg"
    cv2.imwrite(filename, frame)
    return filename

def save_debug_image(frame, face_results, detection_num, debug_mode):
    """Save debug image with face boxes if debug mode is enabled."""
    if not debug_mode:
        return
    
    os.makedirs(DEBUG_DIR, exist_ok=True)
    debug_frame = frame.copy()
    
    for embedding, bbox, det_score in face_results:
        x1, y1, x2, y2 = bbox.astype(int)
        cv2.rectangle(debug_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(debug_frame, f"{det_score:.2f}", (x1, y1-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{DEBUG_DIR}/detection_{detection_num:04d}_{timestamp}.jpg"
    cv2.imwrite(filename, debug_frame)
    logger.debug(f"Debug image saved: {filename}")

# =============================================================================
# MAIN LOOP
# =============================================================================

def run_visitor_counter(debug_mode=False):
    """Main visitor counting loop."""
    
    # Initialize database
    db.init_db()
    
    logger.info("=" * 70)
    logger.info("VISITOR COUNTER")
    logger.info("=" * 70)
    logger.info(f"RTSP: {RTSP_URL.split('@')[1]}")
    logger.info(f"Similarity threshold: {SIMILARITY_THRESHOLD}")
    logger.info(f"Cooldown: {COOLDOWN_SECONDS}s")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 70)
    
    # Load face recognition model (downloads on first run)
    logger.info("Loading face recognition model...")
    get_face_analyzer()
    
    # Load existing visitor embeddings into memory
    logger.info("Loading known visitors from database...")
    known_embeddings = db.get_all_embeddings()
    logger.info(f"Loaded {len(known_embeddings)} known visitor(s)")
    
    # Connect to camera
    logger.info("Connecting to camera...")
    cap = cv2.VideoCapture(RTSP_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    if not cap.isOpened():
        logger.error("Cannot connect to camera")
        return
    
    ret, frame = cap.read()
    if not ret:
        logger.error("Cannot read from camera")
        return
    
    frame_resized = resize_frame(frame, TARGET_WIDTH)
    h, w = frame_resized.shape[:2]
    logger.info(f"Original resolution: {frame.shape[1]}x{frame.shape[0]}")
    logger.info(f"Processing resolution: {w}x{h}")
    
    logger.info("\nVisitor counting started. Waiting for faces...")
    
    frame_count = 0
    last_capture_time = 0
    
    # Timing stats
    timing_stats = {'resize': [], 'recognition': [], 'total': []}
    stats_window = 100
    
    # Session stats
    session_stats = {
        'new_visitors': 0,
        'returning_visitors': 0,
        'total_detections': 0
    }
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Lost connection. Reconnecting...")
                cap.release()
                time.sleep(2)
                cap = cv2.VideoCapture(RTSP_URL)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            
            frame_count += 1
            
            # Skip frames for performance
            if frame_count % PROCESS_EVERY_N_FRAMES != 0:
                continue
            
            # Check cooldown BEFORE processing
            current_time = time.time()
            if current_time - last_capture_time < COOLDOWN_SECONDS:
                continue
            
            loop_start = time.perf_counter()
            
            # Resize for processing
            t0 = time.perf_counter()
            frame_resized = resize_frame(frame, TARGET_WIDTH)
            resize_time = (time.perf_counter() - t0) * 1000
            
            # Extract face embeddings (detection + recognition in one step)
            t0 = time.perf_counter()
            face_results = extract_embeddings(frame_resized)
            recognition_time = (time.perf_counter() - t0) * 1000
            
            total_time = (time.perf_counter() - loop_start) * 1000
            
            # Store timing stats
            timing_stats['resize'].append(resize_time)
            timing_stats['recognition'].append(recognition_time)
            timing_stats['total'].append(total_time)
            for key in timing_stats:
                if len(timing_stats[key]) > stats_window:
                    timing_stats[key] = timing_stats[key][-stats_window:]
            
            # Process each detected face
            if face_results:
                session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Save debug image if enabled
                save_debug_image(frame_resized, face_results, session_stats['total_detections'] + 1, debug_mode)
                
                for i, (embedding, bbox, det_score) in enumerate(face_results):
                    session_stats['total_detections'] += 1
                    
                    logger.info(f"Face detected (confidence: {det_score:.2f})")
                    
                    # Try to match against known visitors
                    match = find_best_match(embedding, known_embeddings)
                    
                    if match:
                        visitor_id, similarity = match
                        logger.info(f"  → RETURNING visitor #{visitor_id} (similarity: {similarity:.3f})")
                        
                        # Record the visit
                        db.record_visit(visitor_id, session_id, similarity)
                        session_stats['returning_visitors'] += 1
                        
                    else:
                        # New visitor - add to database
                        image_path = save_visitor_image(frame_resized, 0, session_id)  # temp id
                        visitor_id = db.add_visitor(embedding, image_path)
                        
                        # Rename image with correct visitor ID
                        new_path = image_path.replace("visitor_0_", f"visitor_{visitor_id}_")
                        os.rename(image_path, new_path)
                        
                        # Add to in-memory cache
                        known_embeddings.append((visitor_id, embedding))
                        
                        logger.info(f"  → NEW visitor #{visitor_id} enrolled")
                        session_stats['new_visitors'] += 1
                    
                    # Update cooldown
                    last_capture_time = time.time()
                
                # Log current stats
                logger.debug(f"  DB: {db.get_visitor_count()} unique visitors")
            
            # Progress indicator with timing stats
            if (frame_count // PROCESS_EVERY_N_FRAMES) % 100 == 0:
                avg_resize = sum(timing_stats['resize']) / len(timing_stats['resize'])
                avg_recog = sum(timing_stats['recognition']) / len(timing_stats['recognition'])
                avg_total = sum(timing_stats['total']) / len(timing_stats['total'])
                
                logger.debug(f"[PERF] Resize: {avg_resize:.1f}ms | Recognition: {avg_recog:.1f}ms | Total: {avg_total:.1f}ms")
                
    except KeyboardInterrupt:
        logger.info("\nStopping visitor counter...")
    finally:
        cap.release()
        
        # Final summary
        logger.info("\n" + "=" * 70)
        logger.info("SESSION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total face detections: {session_stats['total_detections']}")
        logger.info(f"New visitors enrolled: {session_stats['new_visitors']}")
        logger.info(f"Returning visitors:    {session_stats['returning_visitors']}")
        
        logger.info(f"\nUnique visitors in DB: {db.get_visitor_count()}")
        
        if timing_stats['recognition']:
            logger.info("\nTIMING (averages):")
            logger.info(f"  Resize:      {sum(timing_stats['resize'])/len(timing_stats['resize']):.1f} ms")
            logger.info(f"  Recognition: {sum(timing_stats['recognition'])/len(timing_stats['recognition']):.1f} ms")
            logger.info(f"  Total:       {sum(timing_stats['total'])/len(timing_stats['total']):.1f} ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visitor Counter")
    parser.add_argument("--debug", action="store_true", help="Save debug images with face boxes")
    args = parser.parse_args()
    
    if args.debug:
        logger.info(f"Debug mode: saving images to {DEBUG_DIR}")
    
    run_visitor_counter(debug_mode=args.debug)
