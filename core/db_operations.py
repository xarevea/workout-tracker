import csv
from typing import List, Dict
from sqlalchemy import func
from datetime import datetime

from core.database import get_db_session
from core.models import (
    User, Exercise, RoutineTemplate, RoutineExercise, Equipment, Workout,
    WorkoutLog, BodyweightLog, Program, ProgramDay, ApiIntegration, ExerciseMode
)

class WorkoutDatabaseManager:
    @staticmethod
    def get_all_exercises() -> list:
        with get_db_session() as session:
            exercises = session.query(Exercise).order_by(Exercise.name.asc()).all()
            return [{'id': e.id, 'name': e.name, 'category': e.category, 'primary_muscle': e.primary_muscle,
                     'secondary_muscles': e.secondary_muscles, 'cues': e.cues,
                     'media_path': e.media_path, 'tracks_time': e.tracks_time} for e in exercises]

    @staticmethod
    def add_exercise(name: str, primary: str, secondary: str, cues: str = "", media_path: str = "", tracks_time: bool = False):
        with get_db_session() as session:
            if not session.query(Exercise).filter_by(name=name).first():
                session.add(Exercise(name=name, category='Hybrid', primary_muscle=primary,
                                     secondary_muscles=secondary, cues=cues, media_path=media_path, tracks_time=tracks_time))

    @staticmethod
    def save_routine_exercises(template_id: int, exercises_data: list):
        with get_db_session() as session:
            session.query(RoutineExercise).filter_by(template_id=template_id).delete()
            for ex in exercises_data:
                new_ex = RoutineExercise(
                    template_id=template_id, exercise_name=ex['name'],
                    target_sets=ex['sets'], target_reps_min=ex['min_reps'],
                    target_reps_max=ex['max_reps'], target_weight=ex['weight'],
                    rest_seconds=ex['rest']
                )
                session.add(new_ex)

    @staticmethod
    def update_routine_targets(template_id: int, adjustments: dict):
        with get_db_session() as session:
            for ex_name, data in adjustments.items():
                record = session.query(RoutineExercise).filter_by(template_id=template_id, exercise_name=ex_name).first()
                if record:
                    record.target_weight = data['weight']
                    record.target_reps_min = data['min_reps']
                    record.target_reps_max = data['max_reps']

    @staticmethod
    def add_equipment(user_id: int, name: str, weight: float, qty: int, is_barbell: bool):
        with get_db_session() as session:
            if not session.query(Equipment).filter_by(user_id=user_id, name=name).first():
                session.add(Equipment(user_id=user_id, name=name, weight_lbs=weight, quantity=qty, is_barbell=is_barbell))

    @staticmethod
    def get_equipment_inventory(user_id: int) -> dict:
        with get_db_session() as session:
            items = session.query(Equipment).filter_by(user_id=user_id).all()
            inventory = {'barbell': 45.0, 'plates': [], 'raw_items': []}
            for item in items:
                inventory['raw_items'].append({'name': item.name, 'weight_lbs': item.weight_lbs, 'quantity': item.quantity, 'is_barbell': item.is_barbell})
                if item.is_barbell:
                    inventory['barbell'] = item.weight_lbs
                else:
                    inventory['plates'].extend([item.weight_lbs] * (item.quantity // 2))
            inventory['plates'].sort(reverse=True)
            return inventory

    @staticmethod
    def save_completed_workout(user_id: int, workout_name: str, duration_minutes: int, bodyweight: float, logs: list, date_str: str = None) -> int:
        with get_db_session() as session:
            dt = date_str if date_str else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            workout = Workout(user_id=user_id, name=workout_name, duration_minutes=duration_minutes, bodyweight_at_time=bodyweight, date=dt)
            session.add(workout)
            session.flush() # Get the new ID

            for log in logs:
                ex = session.query(Exercise).filter_by(name=log['exercise']).first()
                if not ex: continue
                set_num = 0 if log.get('is_warmup', False) else log['set']
                session.add(WorkoutLog(
                    workout_id=workout.id, exercise_id=ex.id, set_number=set_num,
                    reps=log['reps'], weight_lbs=log['weight'], rpe=log['rpe'], is_warmup=log.get('is_warmup', False)
                ))
            return workout.id

    @staticmethod
    def get_weekly_tonnage(user_id: int) -> dict:
        with get_db_session() as session:
            results = session.query(
                func.strftime('%W', Workout.date).label('week'),
                func.sum(WorkoutLog.reps * WorkoutLog.weight_lbs).label('tonnage')
            ).join(WorkoutLog, Workout.id == WorkoutLog.workout_id)\
             .filter(Workout.user_id == user_id, WorkoutLog.is_warmup == False)\
             .group_by('week').order_by('week').all()
            return {r.week: r.tonnage for r in results}

    @staticmethod
    def get_1rm_trends(user_id: int, exercise_name: str) -> dict:
        with get_db_session() as session:
            results = session.query(Workout.date, WorkoutLog.weight_lbs, WorkoutLog.reps)\
                .join(WorkoutLog, Workout.id == WorkoutLog.workout_id)\
                .join(Exercise, Exercise.id == WorkoutLog.exercise_id)\
                .filter(Exercise.name == exercise_name, Workout.user_id == user_id)\
                .order_by(Workout.date.asc()).all()

            trends = {}
            for date_val, weight, reps in results:
                date = date_val.split(' ')[0]
                estimated_1rm = weight * (1 + (reps / 30.0))
                if date not in trends or estimated_1rm > trends[date]:
                    trends[date] = estimated_1rm
            return trends

    @staticmethod
    def get_all_workout_dates(user_id: int) -> list:
        with get_db_session() as session:
            workouts = session.query(Workout.date).filter_by(user_id=user_id).all()
            return list(set([w.date.split(' ')[0] for w in workouts]))

    @staticmethod
    def get_tracked_exercises(user_id: int) -> list:
        with get_db_session() as session:
            results = session.query(Exercise.name).distinct()\
                .join(WorkoutLog, Exercise.id == WorkoutLog.exercise_id)\
                .join(Workout, Workout.id == WorkoutLog.workout_id)\
                .filter(Workout.user_id == user_id).order_by(Exercise.name.asc()).all()
            return [r.name for r in results]

    @staticmethod
    def get_active_program_volume(user_id: int) -> dict:
        with get_db_session() as session:
            results = session.query(Exercise.primary_muscle, Exercise.secondary_muscles, RoutineExercise.target_sets)\
                .join(RoutineExercise, RoutineExercise.exercise_name == Exercise.name)\
                .join(ProgramDay, ProgramDay.template_id == RoutineExercise.template_id)\
                .join(Program, Program.id == ProgramDay.program_id)\
                .filter(Program.user_id == user_id, Program.is_active == True, ProgramDay.is_deload == False).all()

            volume_map = {}
            for pri, sec, sets in results:
                if pri: volume_map[pri] = volume_map.get(pri, 0) + sets
                if sec:
                    for s in [s.strip() for s in sec.split(',')]:
                        volume_map[s] = volume_map.get(s, 0) + (sets * 0.5)
            return volume_map

    @staticmethod
    def get_routine_exercises(template_id: int) -> list:
        with get_db_session() as session:
            results = session.query(RoutineExercise, Exercise)\
                .join(Exercise, RoutineExercise.exercise_name == Exercise.name)\
                .filter(RoutineExercise.template_id == template_id).order_by(RoutineExercise.id.asc()).all()

            return [{
                'name': r.RoutineExercise.exercise_name,
                'target_sets': r.RoutineExercise.target_sets,
                'target_reps_min': r.RoutineExercise.target_reps_min,
                'target_reps_max': r.RoutineExercise.target_reps_max,
                'target_weight': r.RoutineExercise.target_weight,
                'rest_seconds': r.RoutineExercise.rest_seconds,
                'mode': r.RoutineExercise.mode or ExerciseMode.STANDARD,
                'circuit_group': r.RoutineExercise.circuit_group,
                'primary_muscle': r.Exercise.primary_muscle,
                'secondary_muscles': r.Exercise.secondary_muscles,
                'cues': r.Exercise.cues,
                'tracks_time': r.Exercise.tracks_time
            } for r in results]

    @staticmethod
    def log_bodyweight(user_id: int, date_str: str, weight: float):
        with get_db_session() as session:
            session.add(BodyweightLog(user_id=user_id, date=date_str, weight_lbs=weight))

    @staticmethod
    def delete_bodyweight_log(user_id: int, date_str: str):
        with get_db_session() as session:
            session.query(BodyweightLog).filter_by(user_id=user_id, date=date_str).delete()

    @staticmethod
    def get_bodyweight_history(user_id: int) -> list:
        with get_db_session() as session:
            logs = session.query(BodyweightLog).filter_by(user_id=user_id).order_by(BodyweightLog.date.asc()).all()
            return [{'date': l.date, 'weight_lbs': l.weight_lbs} for l in logs]

    @staticmethod
    def get_latest_bodyweight(user_id: int) -> float:
        with get_db_session() as session:
            log = session.query(BodyweightLog).filter_by(user_id=user_id).order_by(BodyweightLog.date.desc()).first()
            return log.weight_lbs if log else 185.0

    @staticmethod
    def get_calisthenics_volume_trend(user_id: int):
        with get_db_session() as session:
            results = session.query(
                func.date(Workout.date).label('date_val'),
                func.sum(WorkoutLog.reps * (Workout.bodyweight_at_time + WorkoutLog.weight_lbs)).label('tonnage')
            ).join(WorkoutLog, Workout.id == WorkoutLog.workout_id)\
             .join(Exercise, Exercise.id == WorkoutLog.exercise_id)\
             .filter(Exercise.category == 'Bodyweight', WorkoutLog.is_warmup == False, Workout.user_id == user_id)\
             .group_by('date_val').order_by('date_val').all()
            return {r.date_val: r.tonnage for r in results}

    @staticmethod
    def get_all_templates() -> list:
        with get_db_session() as session:
            templates = session.query(RoutineTemplate).order_by(RoutineTemplate.name.asc()).all()
            return [{'id': t.id, 'name': t.name, 'is_active': t.is_active} for t in templates]

    @staticmethod
    def get_program_templates(program_id: int) -> list:
        if not program_id: return []
        with get_db_session() as session:
            results = session.query(RoutineTemplate.id, RoutineTemplate.name, ProgramDay.day_number)\
                .join(ProgramDay, ProgramDay.template_id == RoutineTemplate.id)\
                .filter(ProgramDay.program_id == program_id)\
                .order_by(ProgramDay.day_number.asc()).all()
            return [{'id': r.id, 'name': r.name, 'day_number': r.day_number} for r in results]

    @staticmethod
    def save_sandbox_program(user_id: int, program_id: int, program_name: str, pool_data: list):
        with get_db_session() as session:
            if program_id:
                prog = session.query(Program).filter_by(id=program_id).first()
                prog.name = program_name
            else:
                prog = Program(user_id=user_id, name=program_name)
                session.add(prog)
                session.flush()
                program_id = prog.id

            session.query(ProgramDay).filter_by(program_id=program_id).delete()

            from collections import defaultdict
            days = defaultdict(list)
            for item in pool_data: days[item['day']].append(item)

            day_map = {"Day 1": 1, "Day 2": 2, "Day 3": 3, "Day 4": 4, "Day 5": 5, "Day 6": 6, "Day 7": 7}
            for day_str, ex_list in days.items():
                if day_str == "Unassigned": continue
                day_num = day_map.get(day_str, 1)
                t_name = f"{program_name} - {day_str}"

                template = session.query(RoutineTemplate).filter_by(name=t_name).first()
                if not template:
                    template = RoutineTemplate(name=t_name, is_active=True)
                    session.add(template)
                    session.flush()

                session.query(RoutineExercise).filter_by(template_id=template.id).delete()

                for ex in ex_list:
                    session.add(RoutineExercise(
                        template_id=template.id,
                        exercise_name=ex['exercise'],
                        target_sets=ex.get('sets', 3),
                        target_reps_min=ex.get('min_reps', 8),
                        target_reps_max=ex.get('max_reps', 12),
                        target_weight=ex.get('weight', 0.0),
                        rest_seconds=ex.get('rest', 90),
                        mode=ex.get('mode', ExerciseMode.STANDARD),
                        circuit_group=ex.get('circuit_group', 0)
                    ))

                session.add(ProgramDay(program_id=program_id, day_number=day_num, template_id=template.id))

    @staticmethod
    def get_sandbox_program_data(program_id: int) -> list:
        with get_db_session() as session:
            results = session.query(ProgramDay.day_number, RoutineExercise.exercise_name, RoutineExercise.target_sets)\
                .join(RoutineTemplate, RoutineTemplate.id == ProgramDay.template_id)\
                .join(RoutineExercise, RoutineExercise.template_id == RoutineTemplate.id)\
                .filter(ProgramDay.program_id == program_id).order_by(ProgramDay.day_number.asc()).all()
            return [{'day': f"Day {r.day_number}", 'exercise': r.exercise_name, 'sets': r.target_sets} for r in results]

    @staticmethod
    def get_workout_history(user_id: int) -> list:
        with get_db_session() as session:
            workouts = session.query(Workout).filter_by(user_id=user_id).order_by(Workout.date.desc()).all()
            return [{'id': w.id, 'date': w.date, 'name': w.name, 'duration_minutes': w.duration_minutes} for w in workouts]

    @staticmethod
    def get_workout_logs(workout_id: int) -> list:
        with get_db_session() as session:
            results = session.query(WorkoutLog, Exercise.name)\
                .join(Exercise, Exercise.id == WorkoutLog.exercise_id)\
                .filter(WorkoutLog.workout_id == workout_id).order_by(WorkoutLog.id.asc()).all()
            return [{'id': r.WorkoutLog.id, 'exercise': r.name, 'set_number': r.WorkoutLog.set_number,
                     'reps': r.WorkoutLog.reps, 'weight_lbs': r.WorkoutLog.weight_lbs, 'rpe': r.WorkoutLog.rpe,
                     'is_warmup': r.WorkoutLog.is_warmup} for r in results]

    @staticmethod
    def delete_workout(workout_id: int):
        with get_db_session() as session:
            session.query(Workout).filter_by(id=workout_id).delete() # Cascade delete handles logs

    @staticmethod
    def get_all_users() -> list:
        with get_db_session() as session:
            users = session.query(User).order_by(User.id.asc()).all()
            return [{'id': u.id, 'username': u.username} for u in users]

    @staticmethod
    def create_user(username: str) -> int:
        with get_db_session() as session:
            user = User(username=username)
            session.add(user)
            session.flush()
            return user.id

    @staticmethod
    def get_programs_for_user(user_id: int) -> list:
        with get_db_session() as session:
            progs = session.query(Program).filter_by(user_id=user_id).all()
            return [{'id': p.id, 'name': p.name, 'is_active': p.is_active} for p in progs]

    @staticmethod
    def set_active_program(user_id: int, program_id: int):
        with get_db_session() as session:
            session.query(Program).filter_by(user_id=user_id).update({"is_active": False})
            if program_id:
                session.query(Program).filter_by(id=program_id).update({"is_active": True})

    @staticmethod
    def calculate_muscle_volume(exercises_data: list) -> dict:
        if not exercises_data: return {}
        volume_map = {}
        with get_db_session() as session:
            for ex in exercises_data:
                record = session.query(Exercise).filter_by(name=ex.get('name')).first()
                if record:
                    sets = ex.get('sets', 0)
                    if record.primary_muscle:
                        volume_map[record.primary_muscle] = volume_map.get(record.primary_muscle, 0) + sets
                    if record.secondary_muscles:
                        for sec in [s.strip() for s in record.secondary_muscles.split(',') if s.strip()]:
                            volume_map[sec] = volume_map.get(sec, 0) + (sets * 0.5)
        return volume_map

    @staticmethod
    def get_api_credentials(provider: str) -> dict:
        with get_db_session() as session:
            rec = session.query(ApiIntegration).filter_by(provider_name=provider).first()
            return {'access_token': rec.access_token, 'refresh_token': rec.refresh_token} if rec else None

    @staticmethod
    def save_api_credentials(provider: str, access: str, refresh: str):
        with get_db_session() as session:
            rec = session.query(ApiIntegration).filter_by(provider_name=provider).first()
            if rec:
                rec.access_token = access
                rec.refresh_token = refresh
            else:
                session.add(ApiIntegration(provider_name=provider, access_token=access, refresh_token=refresh))

    @staticmethod
    def get_user_equipment(user_id: int) -> list:
        """Returns all equipment raw objects with IDs for the UI table."""
        with get_db_session() as session:
            items = session.query(Equipment).filter_by(user_id=user_id).order_by(Equipment.weight_lbs.desc()).all()
            return [{'id': e.id, 'name': e.name, 'weight_lbs': e.weight_lbs, 'quantity': e.quantity, 'is_barbell': e.is_barbell} for e in items]

    @staticmethod
    def delete_equipment(equipment_id: int):
        with get_db_session() as session:
            session.query(Equipment).filter_by(id=equipment_id).delete()

    @staticmethod
    def update_exercise(ex_id: int, name: str, category: str, primary: str, secondary: str, cues: str, media_path: str = "", tracks_time: bool = False):
        with get_db_session() as session:
            ex = session.query(Exercise).filter_by(id=ex_id).first()
            if ex:
                ex.name = name
                ex.category = category
                ex.primary_muscle = primary
                ex.secondary_muscles = secondary
                ex.cues = cues
                ex.media_path = media_path
                ex.tracks_time = tracks_time

    @staticmethod
    def delete_exercise(ex_id: int):
        with get_db_session() as session:
            session.query(Exercise).filter_by(id=ex_id).delete()

    @staticmethod
    def export_workouts_to_csv(user_id: int, file_path: str):
        with get_db_session() as session:
            # Join the tables to flatten the relational data
            results = session.query(Workout, WorkoutLog, Exercise)\
                .join(WorkoutLog, Workout.id == WorkoutLog.workout_id)\
                .join(Exercise, Exercise.id == WorkoutLog.exercise_id)\
                .filter(Workout.user_id == user_id)\
                .order_by(Workout.date.desc(), WorkoutLog.id.asc()).all()

            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write the Headers
                writer.writerow([
                    "Date", "Workout Name", "Duration (min)", "Bodyweight (lbs)",
                    "Exercise", "Set", "Reps", "Weight (lbs)", "RPE", "Is Warmup"
                ])

                # Write Rows
                for w, log, ex in results:
                    writer.writerow([
                        w.date, w.name, w.duration_minutes, w.bodyweight_at_time,
                        ex.name, log.set_number, log.reps, log.weight_lbs, log.rpe, log.is_warmup
                    ])

    @staticmethod
    def get_daily_tonnage(user_id: int) -> dict:
        """Returns a dict of { 'YYYY-MM-DD': total_tonnage } for ACWR calculation."""
        from sqlalchemy import func
        with get_db_session() as session:
            results = session.query(
                func.date(Workout.date).label('date_val'),
                func.sum(WorkoutLog.reps * WorkoutLog.weight_lbs).label('tonnage')
            ).join(WorkoutLog, Workout.id == WorkoutLog.workout_id)\
             .filter(Workout.user_id == user_id, WorkoutLog.is_warmup == False)\
             .group_by('date_val').order_by('date_val').all()
            return {r.date_val: r.tonnage for r in results}

