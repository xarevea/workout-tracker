# utils/mock_data.py
import random
from datetime import datetime, timedelta
from core.database import get_connection

def generate_test_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Initializing test data seed...")

    # 1. Seed Exercises
    exercises = [
        ("Bench Press", "Barbell", "Chest", "Triceps, Shoulders"),
        ("Barbell Back Squats", "Barbell", "Quads", "Glutes, Core, Hamstrings"),
        ("Weighted Pull-Ups", "Bodyweight", "Back", "Biceps, Core"),
        ("Barbell Overhead Press", "Barbell", "Shoulders", "Triceps, Core"),
        ("Romanian Deadlifts (RDL)", "Barbell", "Hamstrings", "Glutes, Back"),
        ("Calf Raises", "Dumbbell", "Calves", ""),
        ("Hanging Leg Raises", "Bodyweight", "Core", "")
    ]
    for name, cat, pri, sec in exercises:
        cursor.execute('''
            INSERT INTO exercises (name, category, primary_muscle, secondary_muscles) 
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET primary_muscle=excluded.primary_muscle, secondary_muscles=excluded.secondary_muscles
        ''', (name, cat, pri, sec))

    cursor.execute("SELECT id, name FROM exercises")
    ex_map = {row['name']: row['id'] for row in cursor.fetchall()}

    # 2. Seed Active Templates
    templates = [("Day 1 - Upper (Test)", 1), ("Day 2 - Lower (Test)", 1)]
    template_ids = {}
    for t_name, is_active in templates:
        cursor.execute("INSERT INTO routine_templates (name, is_active) VALUES (?, ?) ON CONFLICT(name) DO UPDATE SET is_active=excluded.is_active", (t_name, is_active))
        cursor.execute("SELECT id FROM routine_templates WHERE name=?", (t_name,))
        template_ids[t_name] = cursor.fetchone()['id']

    # Clear old routine exercises
    for t_id in template_ids.values(): cursor.execute("DELETE FROM routine_exercises WHERE template_id=?", (t_id,))

    # 3. Seed Routine Exercises (USING NEW SCHEMA: sets, min, max, weight, rest, is_bw)
    upper_exs = [
        ("Bench Press", 4, 4, 6, 225.0, 120, 0),
        ("Weighted Pull-Ups", 4, 4, 6, 45.0, 90, 1),
        ("Barbell Overhead Press", 3, 6, 8, 135.0, 90, 0)
    ]
    for ex_name, sets, min_r, max_r, weight, rest, is_bw in upper_exs:
        cursor.execute('''
            INSERT INTO routine_exercises (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds, is_bodyweight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (template_ids["Day 1 - Upper (Test)"], ex_name, sets, min_r, max_r, weight, rest, is_bw))

    lower_exs = [
        ("Barbell Back Squats", 4, 4, 6, 315.0, 180, 0),
        ("Romanian Deadlifts (RDL)", 3, 8, 10, 225.0, 120, 0),
        ("Calf Raises", 4, 15, 20, 50.0, 60, 0),
        ("Hanging Leg Raises", 3, 10, 15, 0.0, 60, 1)
    ]
    for ex_name, sets, min_r, max_r, weight, rest, is_bw in lower_exs:
        cursor.execute('''
            INSERT INTO routine_exercises (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds, is_bodyweight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (template_ids["Day 2 - Lower (Test)"], ex_name, sets, min_r, max_r, weight, rest, is_bw))

    # 4. Generate History
    cursor.execute("SELECT COUNT(*) FROM workouts WHERE name='Day 1 - Upper (Test)'")
    if cursor.fetchone()[0] == 0:
        base_date = datetime.now() - timedelta(days=28)
        for week in range(4):
            bench_wt = 205 + (week * 5)
            squat_wt = 275 + (week * 10)
            
            date_str = (base_date + timedelta(days=(week*7))).strftime("%Y-%m-%d 12:00:00")
            cursor.execute("INSERT INTO workouts (date, name, duration_minutes, bodyweight_at_time) VALUES (?, ?, ?, ?)", (date_str, "Day 1 - Upper (Test)", 60, 185.0))
            w_id = cursor.lastrowid
            for s in range(1, 4):
                cursor.execute("INSERT INTO workout_logs (workout_id, exercise_id, set_number, reps, weight_lbs, rpe) VALUES (?, ?, ?, ?, ?, ?)", (w_id, ex_map["Bench Press"], s, random.randint(4,6), bench_wt, 8))
                cursor.execute("INSERT INTO workout_logs (workout_id, exercise_id, set_number, reps, weight_lbs, rpe) VALUES (?, ?, ?, ?, ?, ?)", (w_id, ex_map["Weighted Pull-Ups"], s, random.randint(4,6), 45.0, 8))

            date_str = (base_date + timedelta(days=(week*7)+2)).strftime("%Y-%m-%d 12:00:00")
            cursor.execute("INSERT INTO workouts (date, name, duration_minutes, bodyweight_at_time) VALUES (?, ?, ?, ?)", (date_str, "Day 2 - Lower (Test)", 60, 185.0))
            w_id = cursor.lastrowid
            for s in range(1, 5):
                cursor.execute("INSERT INTO workout_logs (workout_id, exercise_id, set_number, reps, weight_lbs, rpe) VALUES (?, ?, ?, ?, ?, ?)", (w_id, ex_map["Barbell Back Squats"], s, random.randint(4,6), squat_wt, 8.5))
        print("Mock historical logs successfully seeded.")
    else:
        print("Historical logs already exist. Skipping history generation.")

    # Seed Bodyweight logs
    cursor.execute("SELECT COUNT(*) FROM bodyweight_log")
    if cursor.fetchone()[0] == 0:
        base_date = datetime.now() - timedelta(days=28)
        bw = 195.0
        for i in range(28):
            date_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            bw -= random.uniform(0.0, 0.4) # Simulating progressive weight loss
            if random.random() > 0.2: 
                cursor.execute("INSERT INTO bodyweight_log (date, weight_lbs) VALUES (?, ?)", (date_str, round(bw, 1)))

    conn.commit()
    conn.close()
    print("Test database update complete.")