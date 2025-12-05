#!/usr/bin/env python3
"""
SQLite database for storing visitor embeddings and visit counts.
"""

import sqlite3
import numpy as np
import os
from typing import List, Tuple, Optional

DB_PATH = "/home/mafiq/zmisc/visitors.db"

def get_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initialize database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            embedding BLOB NOT NULL,
            visit_count INTEGER DEFAULT 1,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sample_image_path TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def embedding_to_blob(embedding: np.ndarray) -> bytes:
    """Convert numpy embedding to bytes for storage."""
    return embedding.astype(np.float32).tobytes()

def blob_to_embedding(blob: bytes) -> np.ndarray:
    """Convert stored bytes back to numpy embedding."""
    return np.frombuffer(blob, dtype=np.float32)

def add_visitor(embedding: np.ndarray, sample_image_path: Optional[str] = None) -> int:
    """Add a new visitor and return their ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO visitors (embedding, sample_image_path)
        VALUES (?, ?)
    ''', (embedding_to_blob(embedding), sample_image_path))
    
    visitor_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return visitor_id

def record_visit(visitor_id: int, session_id: str, confidence: float):
    """Record a visit for an existing visitor."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE visitors 
        SET visit_count = visit_count + 1, last_seen = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (visitor_id,))
    
    conn.commit()
    conn.close()

def get_all_embeddings() -> List[Tuple[int, np.ndarray]]:
    """Get all visitor IDs and embeddings for matching."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, embedding FROM visitors')
    rows = cursor.fetchall()
    conn.close()
    
    return [(row[0], blob_to_embedding(row[1])) for row in rows]

def get_visitor_count() -> int:
    """Get total number of unique visitors."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM visitors')
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Initialize database on import
if not os.path.exists(DB_PATH):
    init_db()
