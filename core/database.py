# core/database.py
import sqlite3
import os
from contextlib import contextmanager

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

        # --- MULTI-USER SUPPORT ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL)''')

        # --- BASE TABLES (Retained & Updated) ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS bodyweight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT DEFAULT CURRENT_DATE, weight_lbs REAL NOT NULL, notes TEXT, FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS equipment (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, weight_lbs REAL NOT NULL, quantity INTEGER NOT NULL, is_barbell BOOLEAN DEFAULT 0)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL, primary_muscle TEXT, secondary_muscles TEXT, tracks_weight BOOLEAN DEFAULT 1, tracks_time BOOLEAN DEFAULT 0, cues TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, date TEXT DEFAULT CURRENT_TIMESTAMP, name TEXT NOT NULL, duration_minutes INTEGER, bodyweight_at_time REAL, FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS workout_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER, exercise_id INTEGER, set_number INTEGER, reps INTEGER, weight_lbs REAL, rpe REAL, target_hit BOOLEAN DEFAULT 0, is_warmup BOOLEAN DEFAULT 0, FOREIGN KEY(workout_id) REFERENCES workouts(id), FOREIGN KEY(exercise_id) REFERENCES exercises(id))''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS api_integrations (id INTEGER PRIMARY KEY AUTOINCREMENT, provider_name TEXT NOT NULL UNIQUE, access_token TEXT, refresh_token TEXT, token_expires_at REAL)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS health_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT DEFAULT CURRENT_DATE, resting_heart_rate INTEGER, sleep_score INTEGER, readiness_score INTEGER, notes TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS routine_templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, is_active BOOLEAN DEFAULT 0)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS routine_exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, template_id INTEGER, exercise_name TEXT NOT NULL, target_sets INTEGER, target_reps TEXT, target_weight REAL, rest_seconds INTEGER DEFAULT 90, is_bodyweight BOOLEAN DEFAULT 0, target_reps_min INTEGER DEFAULT 8, target_reps_max INTEGER DEFAULT 10, FOREIGN KEY(template_id) REFERENCES routine_templates(id))''')

        # --- PROGRAM BUILDER & PERIODIZATION TABLES ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER,
            name TEXT NOT NULL UNIQUE, 
            cycle_length_days INTEGER DEFAULT 7,
            total_cycles INTEGER DEFAULT 4,
            is_active BOOLEAN DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS program_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            program_id INTEGER, 
            day_number INTEGER, 
            template_id INTEGER, 
            is_deload BOOLEAN DEFAULT 0,
            FOREIGN KEY(program_id) REFERENCES programs(id),
            FOREIGN KEY(template_id) REFERENCES routine_templates(id)
        )''')

        # --- ENSURE DEFAULT USER EXISTS ---
        cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, 'Default User')")


        # =========================================================
        # SCHEMA MIGRATIONS (Safely patching existing tracker.db)
        # =========================================================

        # 1. routine_exercises
        cursor.execute("PRAGMA table_info(routine_exercises)")
        columns = [col['name'] for col in cursor.fetchall()]
        if "target_reps_min" not in columns:
            print("Migration: Adding target_reps_min to routine_exercises...")
            cursor.execute("ALTER TABLE routine_exercises ADD COLUMN target_reps_min INTEGER DEFAULT 8")
        if "target_reps_max" not in columns:
            print("Migration: Adding target_reps_max to routine_exercises...")
            cursor.execute("ALTER TABLE routine_exercises ADD COLUMN target_reps_max INTEGER DEFAULT 10")

        # 2. exercises (Adding Cues)
        cursor.execute("PRAGMA table_info(exercises)")
        ex_cols = [col['name'] for col in cursor.fetchall()]
        if "cues" not in ex_cols:
            print("Migration: Adding cues to exercises...")
            cursor.execute("ALTER TABLE exercises ADD COLUMN cues TEXT")

        # 3. bodyweight_log (Adding Multi-User Tracking)
        cursor.execute("PRAGMA table_info(bodyweight_log)")
        bw_cols = [col['name'] for col in cursor.fetchall()]
        if "user_id" not in bw_cols:
            print("Migration: Adding user_id to bodyweight_log...")
            cursor.execute("ALTER TABLE bodyweight_log ADD COLUMN user_id INTEGER DEFAULT 1 REFERENCES users(id)")

        # 4. workouts (Adding Multi-User Tracking)
        cursor.execute("PRAGMA table_info(workouts)")
        wk_cols = [col['name'] for col in cursor.fetchall()]
        if "user_id" not in wk_cols:
            print("Migration: Adding user_id to workouts...")
            cursor.execute("ALTER TABLE workouts ADD COLUMN user_id INTEGER DEFAULT 1 REFERENCES users(id)")

        # 5. programs (Adding Multi-User Tracking)
        cursor.execute("PRAGMA table_info(programs)")
        pg_cols = [col['name'] for col in cursor.fetchall()]
        if "user_id" not in pg_cols:
            print("Migration: Adding user_id to programs...")
            cursor.execute("ALTER TABLE programs ADD COLUMN user_id INTEGER DEFAULT 1 REFERENCES users(id)")


        # # --- AUTO-LOAD MOCK EXERCISES ON FIRST RUN ---
        # cursor.execute("SELECT COUNT(*) FROM exercises")
        # if cursor.fetchone()[0] == 0:
        #     print("Initial setup detected: Populating mock exercises...")
        #     try:
        #         from utils.mock_data import get_mock_exercises
        #         exercises = get_mock_exercises()
        #         for ex in exercises:
        #             default_cues = get_default_cues_for(ex['name'])
        #             category = ex.get('category', 'Strength') # Fallback if category is missing in mock data
                    
        #             cursor.execute('''INSERT INTO exercises (name, category, primary_muscle, secondary_muscles, cues) 
        #                               VALUES (?, ?, ?, ?, ?)''', 
        #                               (ex['name'], category, ex['primary_muscle'], ex['secondary_muscles'], default_cues))
        #     except ImportError:
        #         print("Warning: Could not import mock_data. Skipping auto-population.")

        # --- AUTO-LOAD DEFAULT EXERCISES ON FIRST RUN ---
        cursor.execute("SELECT COUNT(*) FROM exercises")
        if cursor.fetchone()[0] == 0:
            print("Initial setup detected: Populating default exercises...")
            try:
                from core.default_data import get_default_exercises
                exercises = get_default_exercises()
                for ex in exercises:
                    # Allow fallback defaults if cues or category aren't present in future lists
                    cues = ex.get('cues', "1. Focus on form\n2. Maintain tension")
                    category = ex.get('category', 'Strength')
                    
                    cursor.execute('''INSERT INTO exercises (name, category, primary_muscle, secondary_muscles, cues) 
                                      VALUES (?, ?, ?, ?, ?)''', 
                                      (ex['name'], category, ex['primary_muscle'], ex['secondary_muscles'], cues))
            except ImportError:
                print("Warning: Could not import core.default_data. Skipping auto-population.")

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