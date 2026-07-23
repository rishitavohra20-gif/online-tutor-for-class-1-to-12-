"""
db.py - Handles student progress tracking using SQLite.
Stores: which topics a student has studied, quiz scores, and chat history count.
"""

import sqlite3
from datetime import datetime

DB_PATH = "tutor_progress.db"


def init_db():
    """Create tables if they don't already exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            class_level TEXT,
            subject TEXT,
            question TEXT,
            timestamp TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            class_level TEXT,
            subject TEXT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()


def log_question(student_name, class_level, subject, question):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (student_name, class_level, subject, question, timestamp) VALUES (?, ?, ?, ?, ?)",
        (student_name, class_level, subject, question, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def log_quiz_result(student_name, class_level, subject, topic, score, total):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO quiz_results (student_name, class_level, subject, topic, score, total, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (student_name, class_level, subject, topic, score, total, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_student_progress(student_name):
    """Returns a summary: topics covered, questions asked, average quiz score."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        "SELECT subject, COUNT(*) FROM sessions WHERE student_name=? GROUP BY subject",
        (student_name,)
    )
    questions_per_subject = c.fetchall()

    c.execute(
        "SELECT subject, topic, score, total, timestamp FROM quiz_results WHERE student_name=? ORDER BY timestamp DESC",
        (student_name,)
    )
    quiz_history = c.fetchall()

    conn.close()
    return {
        "questions_per_subject": questions_per_subject,
        "quiz_history": quiz_history
    }
