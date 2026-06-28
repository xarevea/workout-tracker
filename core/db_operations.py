from core.database import get_connection

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
    def get_equipment_inventory() -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM equipment")
        items = cursor.fetchall()
        conn.close()
        inventory = {'barbell': 45.0, 'plates': []}
        for item in items:
            if item['is_barbell']: inventory['barbell'] = item['weight_lbs']
            else: inventory['plates'].extend([item['weight_lbs']] * (item['quantity'] // 2))
        inventory['plates'].sort(reverse=True)
        return inventory

    @staticmethod
    def save_completed_workout(workout_name: str, duration_minutes: int, bodyweight: float, logs: list) -> int:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO workouts (name, duration_minutes, bodyweight_at_time) VALUES (?, ?, ?)", 
                       (workout_name, duration_minutes, bodyweight))
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
    def get_weekly_tonnage() -> dict:
        """
        Calculates total tonnage per week. 
        CALISTHENICS MATH: If an exercise is bodyweight, it factors the user's 
        logged bodyweight into the total resistance moved.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # We use SQLite's strftime('%W', date) to group by week number
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
            GROUP BY week
            ORDER BY week ASC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return {row['week']: row['total_tonnage'] for row in results}

    @staticmethod
    def get_1rm_trends(exercise_name: str) -> dict:
        """
        Uses the Epley formula: 1RM = Weight * (1 + Reps/30) to estimate maxes over time.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT w.date, l.weight_lbs, l.reps
            FROM workout_logs l
            JOIN workouts w ON l.workout_id = w.id
            JOIN exercises e ON l.exercise_id = e.id
            WHERE e.name = ?
            ORDER BY w.date ASC
        ''', (exercise_name,))
        
        results = cursor.fetchall()
        conn.close()
        
        trends = {}
        for row in results:
            date = row['date'].split(' ')[0] # Get just the YYYY-MM-DD
            # Epley Formula
            estimated_1rm = row['weight_lbs'] * (1 + (row['reps'] / 30.0))
            
            # Keep the highest 1RM for that specific day
            if date not in trends or estimated_1rm > trends[date]:
                trends[date] = estimated_1rm
                
        return trends

    @staticmethod
    def get_all_workout_dates() -> list:
        """Returns a list of YYYY-MM-DD strings for days a workout occurred."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT date(date) as w_date FROM workouts")
        results = [row['w_date'] for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_tracked_exercises() -> list:
        """Returns a list of exercise names that have logged data."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT e.name 
            FROM exercises e
            JOIN workout_logs l ON e.id = l.exercise_id
            ORDER BY e.name ASC
        ''')
        results = [row['name'] for row in cursor.fetchall()]
        conn.close()
        return results

    @staticmethod
    def get_active_program_volume() -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.primary_muscle, e.secondary_muscles, r.target_sets
            FROM routine_exercises r
            JOIN exercises e ON r.exercise_name = e.name
            JOIN routine_templates t ON r.template_id = t.id
            WHERE t.is_active = 1
        ''')
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