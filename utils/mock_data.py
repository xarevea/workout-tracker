# utils/mock_data.py
import random
from datetime import datetime, timedelta
from core.database import get_connection

def seed_database():
    """Populates the isolated test database with historical data, templates, and programs."""
    print("Seeding database with testing mock data...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Seed Multiple Users
        cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (1, 'User_Alpha_Main')")
        cursor.execute("INSERT OR IGNORE INTO users (id, username) VALUES (2, 'User_Beta_Guest')")
        
        # 2. Seed Equipment (Forces logic to snap to available plate combinations)
        # BUG FIX: Added user_id (1) to match the new schema upgrades
        equipment_list = [
            (1, "Standard Barbell", 45.0, 1, 1),
            (1, "45lb Plate", 45.0, 6, 0), (1, "25lb Plate", 25.0, 2, 0),
            (1, "10lb Plate", 10.0, 4, 0), (1, "5lb Plate", 5.0, 2, 0), (1, "2.5lb Plate", 2.5, 2, 0)
        ]
        for eq in equipment_list:
            cursor.execute("INSERT OR IGNORE INTO equipment (user_id, name, weight_lbs, quantity, is_barbell) VALUES (?, ?, ?, ?, ?)", eq)

        # 3. Seed Default Exercises
        try:
            from core.default_data import get_default_exercises
            exercises = get_default_exercises()
            for ex in exercises:
                cursor.execute('''INSERT OR IGNORE INTO exercises (name, category, primary_muscle, secondary_muscles, cues) 
                                  VALUES (?, ?, ?, ?, ?)''', 
                                  (ex['name'], ex.get('category', 'Strength'), ex['primary_muscle'], ex['secondary_muscles'], ex.get('cues', '')))
        except ImportError:
            print("Warning: Could not load default exercises. Skipping.")
        
        # 4. Seed Programs
        cursor.execute("INSERT OR IGNORE INTO programs (id, user_id, name, cycle_length_days, total_cycles, is_active) VALUES (1, 1, 'Hypertrophy Phase 1', 7, 4, 1)")
        cursor.execute("INSERT OR IGNORE INTO programs (id, user_id, name, cycle_length_days, total_cycles, is_active) VALUES (2, 2, 'Guest Calisthenics', 3, 8, 1)")
        
        # 5. Seed Routine Templates & Exercises
        cursor.execute("INSERT OR IGNORE INTO routine_templates (id, name, is_active) VALUES (1, 'Push Day Alpha', 1)")
        cursor.execute("INSERT OR IGNORE INTO routine_templates (id, name, is_active) VALUES (2, 'Pull Day Alpha', 1)")
        cursor.execute("INSERT OR IGNORE INTO routine_templates (id, name, is_active) VALUES (3, 'Full Body Beta', 1)")

        # BUG FIX: Replaced target_reps string ('8-10') with target_reps_min and target_reps_max integers
        # Push Day Alpha Exercises
        cursor.execute("INSERT INTO routine_exercises (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds) VALUES (1, 'Barbell Bench Press', 3, 8, 10, 135.0, 90)")
        cursor.execute("INSERT INTO routine_exercises (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds) VALUES (1, 'Barbell Overhead Press', 3, 8, 10, 95.0, 90)")

        # Pull Day Alpha Exercises
        cursor.execute("INSERT INTO routine_exercises (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds, is_bodyweight) VALUES (2, 'Pull-ups', 3, 8, 15, 0, 90, 1)")
        cursor.execute("INSERT INTO routine_exercises (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds) VALUES (2, 'Barbell Deadlift', 3, 5, 5, 225.0, 180)")

        # Full Body Beta Exercises
        cursor.execute("INSERT INTO routine_exercises (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds) VALUES (3, 'Barbell Back Squats', 3, 8, 8, 135.0, 120)")

        # 6. Seed Program Days (Mapping templates to programs)
        # Alpha's Program: Day 1 Push, Day 3 Pull
        cursor.execute("INSERT INTO program_days (program_id, day_number, template_id, is_deload) VALUES (1, 1, 1, 0)")
        cursor.execute("INSERT INTO program_days (program_id, day_number, template_id, is_deload) VALUES (1, 3, 2, 0)")
        # Beta's Program: Day 1 Full Body
        cursor.execute("INSERT INTO program_days (program_id, day_number, template_id, is_deload) VALUES (2, 1, 3, 0)")

        # 7. Seed Bodyweight Log
        base_date = datetime.now() - timedelta(days=30)
        for i in range(30):
            log_date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute("INSERT INTO bodyweight_log (user_id, date, weight_lbs) VALUES (?, ?, ?)", (1, log_date, 180.0 + random.uniform(-1.5, 1.5)))
            cursor.execute("INSERT INTO bodyweight_log (user_id, date, weight_lbs) VALUES (?, ?, ?)", (2, log_date, 150.0 + random.uniform(-1.0, 1.0)))
        
        # 8. Seed Workouts and Logs for User Alpha
        for i in range(10):
            workout_date = (base_date + timedelta(days=i*3)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("INSERT INTO workouts (user_id, date, name, duration_minutes, bodyweight_at_time) VALUES (?, ?, ?, ?, ?)", 
                          (1, workout_date, f"Mock Workout Alpha {i+1}", random.randint(45, 90), 180.0))
            workout_id = cursor.lastrowid
            
            for set_num in range(1, 4):
                cursor.execute('''INSERT INTO workout_logs 
                                  (workout_id, exercise_id, set_number, reps, weight_lbs, rpe, target_hit, is_warmup) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                              (workout_id, 1, set_num, 8, 135.0 + (i*5), 7.5, 1, 0))

        conn.commit()
        print("Mock data seeding complete. Your test environment is ready.")
    except Exception as e:
        conn.rollback()
        print(f"Error seeding mock data: {e}")
    finally:
        conn.close()
    
if __name__ == "__main__":
    seed_database()