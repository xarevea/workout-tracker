# core/database.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tracker.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row 
    return conn

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS bodyweight_log (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT DEFAULT CURRENT_DATE, weight_lbs REAL NOT NULL, notes TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipment (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, weight_lbs REAL NOT NULL, quantity INTEGER NOT NULL, is_barbell BOOLEAN DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL, primary_muscle TEXT, secondary_muscles TEXT, tracks_weight BOOLEAN DEFAULT 1, tracks_time BOOLEAN DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT DEFAULT CURRENT_TIMESTAMP, name TEXT NOT NULL, duration_minutes INTEGER, bodyweight_at_time REAL)''')
    
    # NEW: is_warmup column
    cursor.execute('''CREATE TABLE IF NOT EXISTS workout_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER, exercise_id INTEGER, set_number INTEGER, reps INTEGER, weight_lbs REAL, rpe REAL, target_hit BOOLEAN DEFAULT 0, is_warmup BOOLEAN DEFAULT 0, FOREIGN KEY(workout_id) REFERENCES workouts(id), FOREIGN KEY(exercise_id) REFERENCES exercises(id))''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS api_integrations (id INTEGER PRIMARY KEY AUTOINCREMENT, provider_name TEXT NOT NULL UNIQUE, access_token TEXT, refresh_token TEXT, token_expires_at REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS health_metrics (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT DEFAULT CURRENT_DATE, resting_heart_rate INTEGER, sleep_score INTEGER, readiness_score INTEGER, notes TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS routine_templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, is_active BOOLEAN DEFAULT 0)''')
    
    # NEW: target_reps_min and target_reps_max replacing the target_reps string
    cursor.execute('''CREATE TABLE IF NOT EXISTS routine_exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, template_id INTEGER, exercise_name TEXT NOT NULL, target_sets INTEGER, target_reps_min INTEGER, target_reps_max INTEGER, target_weight REAL, rest_seconds INTEGER DEFAULT 90, is_bodyweight BOOLEAN DEFAULT 0, FOREIGN KEY(template_id) REFERENCES routine_templates(id))''')

    conn.commit()
    conn.close()
    print(f"Database successfully verified/initialized at {DB_PATH}")

if __name__ == "__main__":
    initialize_database()