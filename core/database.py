import sqlite3
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tracker.db')

# TASK 2: Safe Database Connections via Context Manager
@contextmanager
def get_db_connection():
    """Use this with 'with' statements for auto commit/rollback and close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Retained to ensure legacy code in db_operations.py doesn't break until updated
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def initialize_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version")
        version = cursor.fetchone()[0]

        # --- MULTI-USER SUPPORT ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL)''')

        # --- BASE TABLES ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS bodyweight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER DEFAULT 1 REFERENCES users(id), date TEXT DEFAULT CURRENT_DATE, weight_lbs REAL NOT NULL, notes TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS equipment (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER DEFAULT 1 REFERENCES users(id), name TEXT NOT NULL, weight_lbs REAL NOT NULL, quantity INTEGER NOT NULL, is_barbell BOOLEAN DEFAULT 0, UNIQUE(user_id, name))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL, primary_muscle TEXT, secondary_muscles TEXT, cues TEXT, tracks_weight BOOLEAN DEFAULT 1, tracks_time BOOLEAN DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER DEFAULT 1 REFERENCES users(id), date TEXT DEFAULT CURRENT_TIMESTAMP, name TEXT NOT NULL, duration_minutes INTEGER, bodyweight_at_time REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS workout_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER, exercise_id INTEGER, set_number INTEGER, reps INTEGER, weight_lbs REAL, rpe REAL, target_hit BOOLEAN DEFAULT 0, is_warmup BOOLEAN DEFAULT 0, FOREIGN KEY(workout_id) REFERENCES workouts(id), FOREIGN KEY(exercise_id) REFERENCES exercises(id))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS api_integrations (id INTEGER PRIMARY KEY AUTOINCREMENT, provider_name TEXT NOT NULL UNIQUE, access_token TEXT, refresh_token TEXT, token_expires_at REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS health_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT DEFAULT CURRENT_DATE, resting_heart_rate INTEGER, sleep_score INTEGER, readiness_score INTEGER, notes TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS routine_templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, is_active BOOLEAN DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS routine_exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, template_id INTEGER, exercise_name TEXT NOT NULL, target_sets INTEGER, target_reps_min INTEGER DEFAULT 8, target_reps_max INTEGER DEFAULT 10, target_weight REAL, rest_seconds INTEGER DEFAULT 90, is_bodyweight BOOLEAN DEFAULT 0, FOREIGN KEY(template_id) REFERENCES routine_templates(id))''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS programs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER DEFAULT 1 REFERENCES users(id), name TEXT NOT NULL, cycle_length_days INTEGER DEFAULT 7, total_cycles INTEGER DEFAULT 4, is_active BOOLEAN DEFAULT 0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS program_days (id INTEGER PRIMARY KEY AUTOINCREMENT, program_id INTEGER, day_number INTEGER, template_id INTEGER, is_deload BOOLEAN DEFAULT 0, FOREIGN KEY(program_id) REFERENCES programs(id), FOREIGN KEY(template_id) REFERENCES routine_templates(id))''')

        cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, 'Default User')")

        # SCHEMA MIGRATIONS
        if version < 2:
            print("Applying DB Migration to v2 (Equipment User ID)...")
            cursor.execute("PRAGMA table_info(equipment)")
            if "user_id" not in [c['name'] for c in cursor.fetchall()]:
                cursor.execute("ALTER TABLE equipment ADD COLUMN user_id INTEGER DEFAULT 1 REFERENCES users(id)")
            cursor.execute("PRAGMA user_version = 2")

        # Auto Load Defaults
        cursor.execute("SELECT COUNT(*) FROM exercises")
        if cursor.fetchone()[0] == 0:
            try:
                from core.default_data import get_default_exercises
                exercises = get_default_exercises()
                for ex in exercises:
                    cues = ex.get('cues', "1. Focus on form\n2. Maintain tension")
                    cursor.execute('''INSERT INTO exercises (name, category, primary_muscle, secondary_muscles, cues) VALUES (?, ?, ?, ?, ?)''', (ex['name'], ex.get('category', 'Strength'), ex['primary_muscle'], ex['secondary_muscles'], cues))
            except ImportError: pass

    print(f"Database successfully verified/initialized at {DB_PATH}")
    
def get_default_cues_for(exercise_name):
    """Helper method to populate initial cues based on name"""
    if "Bench" in exercise_name:
        return "1. Pin scapulae\n2. Drive feet\n3. Bend the bar\n4. Push yourself into the bench"
    if "Squat" in exercise_name:
        return "1. Brace core\n2. Break at hips and knees\n3. Drive chest up"
    return "1. Maintain tension\n2. Full range of motion"

if __name__ == "__main__":
    initialize_database()