# utils/mock_data.py
import random
from datetime import datetime, timedelta
from core.database import get_connection

def get_mock_exercises():
    return [
        # --- CALISTHENICS & RINGS ---
        {"name": "Ring Dips", "primary_muscle": "chest", "secondary_muscles": "triceps, shoulders, core"},
        {"name": "Ring Push-ups", "primary_muscle": "chest", "secondary_muscles": "triceps, shoulders, core"},
        {"name": "Pull-ups", "primary_muscle": "latissimus", "secondary_muscles": "upper-back, biceps, forearms, core"},
        {"name": "Chin-ups", "primary_muscle": "latissimus", "secondary_muscles": "biceps, upper-back, core"},
        {"name": "Ring Muscle-ups", "primary_muscle": "latissimus", "secondary_muscles": "upper-back, chest, triceps, shoulders, core"},
        {"name": "Front Lever Holds", "primary_muscle": "latissimus", "secondary_muscles": "upper-back, core"},
        {"name": "Planche Progressions", "primary_muscle": "shoulders", "secondary_muscles": "chest, triceps, core"},
        {"name": "Wall Handstand Holds", "primary_muscle": "shoulders", "secondary_muscles": "triceps, upper-back, core"},
        {"name": "Handstand Push-ups", "primary_muscle": "shoulders", "secondary_muscles": "triceps, upper-back, core"},
        {"name": "Pistol Squats", "primary_muscle": "quadriceps", "secondary_muscles": "glutes, calves, core"},
        {"name": "Nordic Curls", "primary_muscle": "hamstrings", "secondary_muscles": "glutes, calves"},
        {"name": "L-Sit", "primary_muscle": "core", "secondary_muscles": "triceps, shoulders, quadriceps"},
        {"name": "Human Flag", "primary_muscle": "core", "secondary_muscles": "latissimus, shoulders, obliques"},
        
        # --- POWER RACK / BARBELL ---
        {"name": "Barbell Back Squats", "primary_muscle": "quadriceps", "secondary_muscles": "glutes, hamstrings, lower-back, core"},
        {"name": "Barbell Front Squats", "primary_muscle": "quadriceps", "secondary_muscles": "glutes, lower-back, core"},
        {"name": "Barbell Bench Press", "primary_muscle": "chest", "secondary_muscles": "triceps, shoulders"},
        {"name": "Incline Bench Press", "primary_muscle": "chest", "secondary_muscles": "shoulders, triceps"},
        {"name": "Barbell Overhead Press", "primary_muscle": "shoulders", "secondary_muscles": "triceps, core, upper-back"},
        {"name": "Barbell Deadlift", "primary_muscle": "glutes", "secondary_muscles": "hamstrings, lower-back, quadriceps, upper-back"},
        {"name": "Romanian Deadlift (RDL)", "primary_muscle": "hamstrings", "secondary_muscles": "glutes, lower-back"},
        {"name": "Barbell Rows", "primary_muscle": "upper-back", "secondary_muscles": "latissimus, biceps, lower-back"},
        {"name": "Good Mornings", "primary_muscle": "hamstrings", "secondary_muscles": "glutes, lower-back"},
        
        # --- DUMBBELL / ACCESSORY ---
        {"name": "Dumbbell Bicep Curls", "primary_muscle": "biceps", "secondary_muscles": "forearms"},
        {"name": "Hammer Curls", "primary_muscle": "biceps", "secondary_muscles": "forearms"},
        {"name": "Overhead Tricep Extensions", "primary_muscle": "triceps", "secondary_muscles": ""},
        {"name": "Tricep Pushdowns", "primary_muscle": "triceps", "secondary_muscles": ""},
        {"name": "Lateral Raises", "primary_muscle": "shoulders", "secondary_muscles": ""},
        {"name": "Calf Raises", "primary_muscle": "calves", "secondary_muscles": ""},
        {"name": "Hanging Leg Raises", "primary_muscle": "core", "secondary_muscles": "forearms, quadriceps"},
        {"name": "Farmer's Walk", "primary_muscle": "forearms", "secondary_muscles": "core, upper-back, calves"}
    ]

def generate_test_data():
    conn = get_connection()
    cursor = conn.cursor()
    print("Initializing test data seed...")

    # 1. Seed Exercises (Granular SVG Mapping)
    exercises = [
        # --- CALISTHENICS / BODYWEIGHT ---
        ("Pull-Ups", "Bodyweight", "latissimus", "biceps, trapezius, forearm"),
        ("Push-Ups", "Bodyweight", "chest", "triceps, deltoids, abs"),
        ("Dips", "Bodyweight", "triceps", "chest, deltoids"),
        ("Pistol Squats", "Bodyweight", "quadriceps", "gluteal, calves, abs"),
        ("Hanging Leg Raises", "Bodyweight", "abs", "obliques, forearm"),
        ("Front Lever", "Bodyweight", "latissimus", "abs, triceps, deltoids"),
        ("Muscle-Ups", "Bodyweight", "latissimus", "chest, triceps, biceps, abs"),
        ("Plank", "Bodyweight", "abs", "obliques, deltoids"),
        ("Inverted Rows", "Bodyweight", "latissimus", "biceps, trapezius"),
        ("Handstand Push-Ups", "Bodyweight", "deltoids", "triceps, trapezius, abs"),
        
        # --- BARBELL / DUMBBELL (Home Gym) ---
        ("Bench Press", "Barbell", "chest", "triceps, deltoids"),
        ("Barbell Squat", "Barbell", "quadriceps", "gluteal, hamstring, lower-back, calves"),
        ("Deadlift", "Barbell", "hamstring", "gluteal, lower-back, trapezius, latissimus, forearm"),
        ("Overhead Press", "Barbell", "deltoids", "triceps, trapezius, abs"),
        ("Barbell Row", "Barbell", "latissimus", "trapezius, biceps, lower-back"),
        ("Romanian Deadlift", "Barbell", "hamstring", "gluteal, lower-back"),
        ("Bicep Curls", "Dumbbell", "biceps", "forearm"),
        ("Tricep Extensions", "Dumbbell", "triceps", ""),
        ("Calf Raises", "Dumbbell", "calves", ""),
        ("Lunges", "Dumbbell", "quadriceps", "gluteal, hamstring")
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