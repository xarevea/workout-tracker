# core/db_operations.py
from typing import List, Dict, Optional
import sqlite3

from core.database import get_connection, get_db_connection

class WorkoutDatabaseManager:
    # --- UI DECOUPLED METHODS ---
    @staticmethod
    def get_all_exercises() -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, primary_muscle, secondary_muscles FROM exercises ORDER BY name ASC")
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return res

    @staticmethod
    def save_routine_exercises(template_id: int, exercises_data: list):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM routine_exercises WHERE template_id = ?", (template_id,))
        for ex in exercises_data:
            cursor.execute('''
                INSERT INTO routine_exercises 
                (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds, is_bodyweight)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (template_id, ex['name'], ex['sets'], ex['min_reps'], ex['max_reps'], ex['weight'], ex['rest']))
        conn.commit()
        conn.close()

    @staticmethod
    def update_routine_targets(template_id: int, adjustments: dict):
        conn = get_connection()
        cursor = conn.cursor()
        for ex_name, data in adjustments.items():
            cursor.execute('''
                UPDATE routine_exercises
                SET target_weight = ?, target_reps_min = ?, target_reps_max = ?
                WHERE template_id = ? AND exercise_name = ?
            ''', (data['weight'], data['min_reps'], data['max_reps'], template_id, ex_name))
        conn.commit()
        conn.close()

    @staticmethod
    def get_equipment_inventory(user_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM equipment WHERE user_id = ?", (user_id,))
        items = cursor.fetchall()
        conn.close()
        inventory = {'barbell': 45.0, 'plates': []}
        for item in items:
            if item['is_barbell']: inventory['barbell'] = item['weight_lbs']
            else: inventory['plates'].extend([item['weight_lbs']] * (item['quantity'] // 2))
        inventory['plates'].sort(reverse=True)
        return inventory

    @staticmethod
    def save_completed_workout(user_id: int, workout_name: str, duration_minutes: int, bodyweight: float, logs: list) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO workouts (user_id, name, duration_minutes, bodyweight_at_time) VALUES (?, ?, ?, ?)", 
                       (user_id, workout_name, duration_minutes, bodyweight))
        workout_id = cursor.lastrowid
        
        for log in logs:
            cursor.execute("SELECT id FROM exercises WHERE name = ?", (log['exercise'],))
            ex_row = cursor.fetchone()
            if not ex_row: continue
            
            cursor.execute('''
                INSERT INTO workout_logs (workout_id, exercise_id, set_number, reps, weight_lbs, rpe, is_warmup)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (workout_id, ex_row['id'], log['set'], log['reps'], log['weight'], log['rpe'], log.get('is_warmup', False)))
            
        conn.commit()
        conn.close()
        return workout_id
    
    @staticmethod
    def get_weekly_tonnage(user_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                strftime('%W', w.date) as week,
                SUM(
                    l.reps * CASE 
                        WHEN e.category = 'Bodyweight' THEN (w.bodyweight_at_time + l.weight_lbs)
                        ELSE l.weight_lbs
                    END
                ) as total_tonnage
            FROM workout_logs l
            JOIN workouts w ON l.workout_id = w.id
            JOIN exercises e ON l.exercise_id = e.id
            WHERE w.user_id = ?
            GROUP BY week
            ORDER BY week ASC
        ''', (user_id,))
        results = cursor.fetchall()
        conn.close()
        return {row['week']: row['total_tonnage'] for row in results}

    @staticmethod
    def get_1rm_trends(user_id: int, exercise_name: str) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.date, l.weight_lbs, l.reps
            FROM workout_logs l
            JOIN workouts w ON l.workout_id = w.id
            JOIN exercises e ON l.exercise_id = e.id
            WHERE e.name = ? AND w.user_id = ?
            ORDER BY w.date ASC
        ''', (exercise_name, user_id))
        
        results = cursor.fetchall()
        conn.close()
        
        trends = {}
        for row in results:
            date = row['date'].split(' ')[0] 
            estimated_1rm = row['weight_lbs'] * (1 + (row['reps'] / 30.0))
            if date not in trends or estimated_1rm > trends[date]:
                trends[date] = estimated_1rm
        return trends

    @staticmethod
    def get_all_workout_dates(user_id: int) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT date(date) as w_date FROM workouts WHERE user_id = ?", (user_id,))
        results = [row['w_date'] for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_tracked_exercises(user_id: int) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT e.name 
            FROM exercises e
            JOIN workout_logs l ON e.id = l.exercise_id
            JOIN workouts w ON l.workout_id = w.id
            WHERE w.user_id = ?
            ORDER BY e.name ASC
        ''', (user_id,))
        results = [row['name'] for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_active_program_volume(user_id: int) -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.primary_muscle, e.secondary_muscles, r.target_sets
            FROM program_days pd
            JOIN programs p ON pd.program_id = p.id
            JOIN routine_exercises r ON pd.template_id = r.template_id
            JOIN exercises e ON r.exercise_name = e.name
            WHERE p.user_id = ? AND p.is_active = 1 AND pd.is_deload = 0
        ''', (user_id,))
        exercises = cursor.fetchall()
        conn.close()

        volume_map = {}
        for ex in exercises:
            sets = ex['target_sets']
            pri = ex['primary_muscle']
            
            if pri:
                volume_map[pri] = volume_map.get(pri, 0) + sets
            if ex['secondary_muscles']:
                for sec in [s.strip() for s in ex['secondary_muscles'].split(',')]:
                    volume_map[sec] = volume_map.get(sec, 0) + (sets * 0.5)
        return volume_map

    @staticmethod
    def get_routine_exercises(template_id: int) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.exercise_name as name, r.target_sets, r.target_reps_min, r.target_reps_max, 
                   r.target_weight, r.rest_seconds, e.primary_muscle, e.secondary_muscles, e.cues
            FROM routine_exercises r
            JOIN exercises e ON r.exercise_name = e.name
            WHERE r.template_id = ?
        ''', (template_id,))
        exercises = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return exercises

    # --- BODYWEIGHT HUB METHODS ---
    @staticmethod
    def log_bodyweight(user_id: int, date_str: str, weight: float):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO bodyweight_log (user_id, date, weight_lbs) VALUES (?, ?, ?)", (user_id, date_str, weight))
        conn.commit()
        conn.close()
        
    @staticmethod
    def delete_bodyweight_log(user_id: int, date_str: str):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bodyweight_log WHERE user_id = ? AND date = ?", (user_id, date_str))
        conn.commit()
        conn.close()

    @staticmethod
    def get_bodyweight_history(user_id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT date, weight_lbs FROM bodyweight_log WHERE user_id = ? ORDER BY date ASC", (user_id,))
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return res

    @staticmethod
    def get_latest_bodyweight(user_id: int) -> float:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT weight_lbs FROM bodyweight_log WHERE user_id = ? ORDER BY date DESC LIMIT 1", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return row['weight_lbs'] if row else 185.0

    @staticmethod
    def get_calisthenics_volume_trend(user_id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date(w.date) as date_val, SUM(l.reps * (w.bodyweight_at_time + l.weight_lbs)) as tonnage
            FROM workout_logs l
            JOIN workouts w ON l.workout_id = w.id
            JOIN exercises e ON l.exercise_id = e.id
            WHERE e.category = 'Bodyweight' AND l.is_warmup = 0 AND w.user_id = ?
            GROUP BY date_val ORDER BY date_val ASC
        ''', (user_id,))
        res = {row['date_val']: row['tonnage'] for row in cursor.fetchall()}
        conn.close()
        return res

    # --- PROGRAM BUILDER METHODS ---
    @staticmethod
    def get_all_templates():
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM routine_templates ORDER BY name ASC")
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return res

    @staticmethod
    def save_program(name: str, cycle_length: int, days_data: list):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR REPLACE INTO programs (name, cycle_length_days) VALUES (?, ?)", (name, cycle_length))
            cursor.execute("SELECT id FROM programs WHERE name=?", (name,))
            program_id = cursor.fetchone()['id']
            
            cursor.execute("DELETE FROM program_days WHERE program_id=?", (program_id,))
            for day in days_data:
                cursor.execute('''
                    INSERT INTO program_days (program_id, day_number, template_id, is_deload)
                    VALUES (?, ?, ?, ?)
                ''', (program_id, day['day_number'], day['template_id'], day['is_deload']))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    @staticmethod
    def get_program_volume_map(program_name: str):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.primary_muscle, e.secondary_muscles, SUM(r.target_sets * r.target_reps_max) as total_reps
            FROM program_days pd
            JOIN programs p ON pd.program_id = p.id
            JOIN routine_exercises r ON pd.template_id = r.template_id
            JOIN exercises e ON r.exercise_name = e.name
            WHERE p.name = ? AND pd.is_deload = 0
        ''', (program_name,))
        rows = cursor.fetchall()
        conn.close()
        
        volume_map = {}
        for row in rows:
            if not row['primary_muscle']: continue
            pri = row['primary_muscle']
            vol = row['total_reps'] or 0
            volume_map[pri] = volume_map.get(pri, 0) + vol
            if row['secondary_muscles']:
                for sec in [s.strip() for s in row['secondary_muscles'].split(',')]:
                    volume_map[sec] = volume_map.get(sec, 0) + (vol * 0.5)
        return volume_map

    @staticmethod
    def calculate_muscle_volume(exercises_data: list) -> dict:
        if not exercises_data:
            return {}
        conn = get_connection()
        cursor = conn.cursor()
        volume_map = {}
        for ex in exercises_data:
            name = ex.get('name')
            sets = ex.get('sets', 0)
            cursor.execute("SELECT primary_muscle, secondary_muscles FROM exercises WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                primary = row['primary_muscle']
                if primary:
                    volume_map[primary] = volume_map.get(primary, 0) + sets
                secondary_str = row['secondary_muscles']
                if secondary_str:
                    secondaries = [s.strip() for s in secondary_str.split(',') if s.strip()]
                    for sec in secondaries:
                        volume_map[sec] = volume_map.get(sec, 0) + (sets * 0.5)
        conn.close()
        return volume_map

    @staticmethod
    def get_all_users() -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username FROM users ORDER BY id")
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_programs_for_user(user_id: int) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, is_active FROM programs WHERE user_id = ?", (user_id,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def set_active_program(user_id: int, program_id: int):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE programs SET is_active = 0 WHERE user_id = ?", (user_id,))
            if program_id is not None:
                cursor.execute("UPDATE programs SET is_active = 1 WHERE id = ?", (program_id,))


   # --- ADD TO: core/db_operations.py ---

    @staticmethod
    def get_program_templates(program_id: int) -> list:
        """Fetches only the routine templates associated with a specific program."""
        if not program_id: return []
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.id, t.name, pd.day_number
            FROM program_days pd
            JOIN routine_templates t ON pd.template_id = t.id
            WHERE pd.program_id = ?
            ORDER BY pd.day_number ASC
        ''', (program_id,))
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return res

    @staticmethod
    def save_sandbox_program(user_id: int, program_id: int, program_name: str, pool_data: list):
        """Creates or overwrites a program and auto-generates daily templates based on the Sandbox UI."""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # 1. Upsert Program
            if program_id:
                cursor.execute("UPDATE programs SET name = ? WHERE id = ?", (program_name, program_id))
            else:
                cursor.execute("INSERT INTO programs (user_id, name) VALUES (?, ?)", (user_id, program_name))
                program_id = cursor.lastrowid
            
            cursor.execute("DELETE FROM program_days WHERE program_id = ?", (program_id,))
            
            from collections import defaultdict
            days = defaultdict(list)
            for item in pool_data: days[item['day']].append(item)
            
            day_map = {"Day 1": 1, "Day 2": 2, "Day 3": 3, "Day 4": 4, "Day 5": 5, "Day 6": 6, "Day 7": 7}
            for day_str, ex_list in days.items():
                if day_str == "Unassigned": continue
                day_num = day_map.get(day_str, 1)
                t_name = f"{program_name} - {day_str}"
                
                # 2. Upsert Template for this day
                cursor.execute("INSERT OR IGNORE INTO routine_templates (name, is_active) VALUES (?, 1)", (t_name,))
                cursor.execute("SELECT id FROM routine_templates WHERE name = ?", (t_name,))
                t_id = cursor.fetchone()['id']
                
                cursor.execute("DELETE FROM routine_exercises WHERE template_id = ?", (t_id,))
                
                # 3. Insert Exercises (Using detailed data from the Finalize GUI)
                for ex in ex_list:
                    cursor.execute('''INSERT INTO routine_exercises 
                                      (template_id, exercise_name, target_sets, target_reps_min, target_reps_max, target_weight, rest_seconds) 
                                      VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                                      (t_id, ex['exercise'], ex.get('sets', 3), 
                                       ex.get('min_reps', 8), ex.get('max_reps', 12), 
                                       ex.get('weight', 0.0), ex.get('rest', 90)))
                    
                # 4. Map Day to Program
                cursor.execute("INSERT INTO program_days (program_id, day_number, template_id) VALUES (?, ?, ?)", (program_id, day_num, t_id))
                
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_sandbox_program_data(program_id: int) -> list:
        """Loads a program back into the Sandbox editor format."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pd.day_number, re.exercise_name, re.target_sets
            FROM program_days pd
            JOIN routine_templates t ON pd.template_id = t.id
            JOIN routine_exercises re ON t.id = re.template_id
            WHERE pd.program_id = ?
            ORDER BY pd.day_number ASC
        ''', (program_id,))
        rows = cursor.fetchall()
        conn.close()
        return [{'day': f"Day {r['day_number']}", 'exercise': r['exercise_name'], 'sets': r['target_sets']} for r in rows]

    @staticmethod
    def get_workout_history(user_id: int) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, name, duration_minutes FROM workouts WHERE user_id = ? ORDER BY date DESC", (user_id,))
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return res

    @staticmethod
    def get_workout_logs(workout_id: int) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT l.id, e.name as exercise, l.set_number, l.reps, l.weight_lbs, l.rpe, l.is_warmup
            FROM workout_logs l
            JOIN exercises e ON l.exercise_id = e.id
            WHERE l.workout_id = ?
            ORDER BY l.id ASC
        ''', (workout_id,))
        res = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return res

    @staticmethod
    def delete_workout(workout_id: int):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workout_logs WHERE workout_id = ?", (workout_id,))
        cursor.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
        conn.commit()
        conn.close() 

    @staticmethod
    def create_user(username: str) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id