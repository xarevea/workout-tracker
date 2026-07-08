# ========================================
# FILE PATH: utils/mock_data.py
# ========================================
import random
from datetime import datetime, timedelta
from core.database import get_db_session
from core.models import (
    User, Equipment, Exercise, Program, RoutineTemplate, RoutineExercise,
    ProgramDay, BodyweightLog, Workout, WorkoutLog
)

def seed_database():
    """Populates the isolated test database with historical data, templates, and programs via ORM."""
    print("Seeding database with testing mock data...")
    
    with get_db_session() as session:
        try:
            # 1. Seed Multiple Users (User 1 might already be created by initialize_database)
            user1 = session.query(User).filter_by(id=1).first()
            if not user1:
                session.add(User(id=1, username='User_Alpha_Main'))
            else:
                user1.username = 'User_Alpha_Main'
                
            if not session.query(User).filter_by(id=2).first():
                session.add(User(id=2, username='User_Beta_Guest'))
            
            # 2. Seed Equipment (Forces logic to snap to available plate combinations)
            equipment_list = [
                (1, "Standard Barbell", 45.0, 1, True),
                (1, "45lb Plate", 45.0, 6, False), (1, "25lb Plate", 25.0, 2, False),
                (1, "10lb Plate", 10.0, 4, False), (1, "5lb Plate", 5.0, 2, False), (1, "2.5lb Plate", 2.5, 2, False)
            ]
            for u_id, name, wt, qty, is_bb in equipment_list:
                if not session.query(Equipment).filter_by(user_id=u_id, name=name).first():
                    session.add(Equipment(user_id=u_id, name=name, weight_lbs=wt, quantity=qty, is_barbell=is_bb))

            # 3. Seed Default Exercises (Usually done by initialize_database, but double checking)
            try:
                from core.default_data import get_default_exercises
                for ex in get_default_exercises():
                    if not session.query(Exercise).filter_by(name=ex['name']).first():
                        session.add(Exercise(
                            name=ex['name'], 
                            category=ex.get('category', 'Strength'), 
                            primary_muscle=ex['primary_muscle'], 
                            secondary_muscles=ex['secondary_muscles'], 
                            cues=ex.get('cues', '')
                        ))
            except ImportError:
                print("Warning: Could not load default exercises. Skipping.")
            
            session.flush() # Ensure exercises have IDs assigned before we reference them in logs

            # 4. Seed Programs
            if not session.query(Program).filter_by(id=1).first():
                session.add(Program(id=1, user_id=1, name='Hypertrophy Phase 1', cycle_length_days=7, total_cycles=4, is_active=True))
            if not session.query(Program).filter_by(id=2).first():
                session.add(Program(id=2, user_id=2, name='Guest Calisthenics', cycle_length_days=3, total_cycles=8, is_active=True))

            # 5. Seed Routine Templates & Exercises
            templates = [
                (1, 'Push Day Alpha', True),
                (2, 'Pull Day Alpha', True),
                (3, 'Full Body Beta', True)
            ]
            for t_id, name, active in templates:
                if not session.query(RoutineTemplate).filter_by(id=t_id).first():
                    session.add(RoutineTemplate(id=t_id, name=name, is_active=active))

            # Push Day Alpha Exercises
            if not session.query(RoutineExercise).filter_by(template_id=1).first():
                session.add(RoutineExercise(template_id=1, exercise_name='Barbell Bench Press', target_sets=3, target_reps_min=8, target_reps_max=10, target_weight=135.0, rest_seconds=90))
                session.add(RoutineExercise(template_id=1, exercise_name='Barbell Overhead Press', target_sets=3, target_reps_min=8, target_reps_max=10, target_weight=95.0, rest_seconds=90))

            # Pull Day Alpha Exercises
            if not session.query(RoutineExercise).filter_by(template_id=2).first():
                session.add(RoutineExercise(template_id=2, exercise_name='Pull-ups', target_sets=3, target_reps_min=8, target_reps_max=15, target_weight=0, rest_seconds=90, is_bodyweight=True))
                session.add(RoutineExercise(template_id=2, exercise_name='Barbell Deadlift', target_sets=3, target_reps_min=5, target_reps_max=5, target_weight=225.0, rest_seconds=180))

            # Full Body Beta Exercises
            if not session.query(RoutineExercise).filter_by(template_id=3).first():
                session.add(RoutineExercise(template_id=3, exercise_name='Barbell Back Squats', target_sets=3, target_reps_min=8, target_reps_max=8, target_weight=135.0, rest_seconds=120))

            # 6. Seed Program Days (Mapping templates to programs)
            if not session.query(ProgramDay).filter_by(program_id=1).first():
                session.add(ProgramDay(program_id=1, day_number=1, template_id=1, is_deload=False))
                session.add(ProgramDay(program_id=1, day_number=3, template_id=2, is_deload=False))
            if not session.query(ProgramDay).filter_by(program_id=2).first():
                session.add(ProgramDay(program_id=2, day_number=1, template_id=3, is_deload=False))

            # 7. Seed Bodyweight Log
            base_date = datetime.now() - timedelta(days=30)
            if session.query(BodyweightLog).count() == 0:
                for i in range(30):
                    log_date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
                    session.add(BodyweightLog(user_id=1, date=log_date, weight_lbs=180.0 + random.uniform(-1.5, 1.5)))
                    session.add(BodyweightLog(user_id=2, date=log_date, weight_lbs=150.0 + random.uniform(-1.0, 1.0)))
            
            # 8. Seed Workouts and Logs for User Alpha
            bench_ex = session.query(Exercise).filter_by(name='Barbell Bench Press').first()
            if session.query(Workout).count() == 0 and bench_ex:
                for i in range(10):
                    workout_date = (base_date + timedelta(days=i*3)).strftime('%Y-%m-%d %H:%M:%S')
                    w = Workout(
                        user_id=1, date=workout_date, name=f"Mock Workout Alpha {i+1}", 
                        duration_minutes=random.randint(45, 90), bodyweight_at_time=180.0
                    )
                    session.add(w)
                    session.flush() # Get the auto-incremented workout ID immediately
                    
                    for set_num in range(1, 4):
                        session.add(WorkoutLog(
                            workout_id=w.id, exercise_id=bench_ex.id, set_number=set_num, 
                            reps=8, weight_lbs=135.0 + (i*5), rpe=7.5, target_hit=True, is_warmup=False
                        ))

            print("Mock data seeding complete. Your test environment is ready.")
            
        except Exception as e:
            print(f"Error seeding mock data: {e}")
            raise # Re-raise to ensure we see the traceback if something goes wrong
            
if __name__ == "__main__":
    seed_database()