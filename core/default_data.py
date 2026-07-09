# core/default_data.py

def get_default_exercises():
    """
    Returns the complete baseline list of exercises loaded when the app runs for the first time.
    Includes built-in cues for the Active Tracker UI.
    """
    return [
        # --- CALISTHENICS & RINGS ---
        {
            "category": "Bodyweight", "name": "Ring Dips", 
            "primary_muscle": "chest", "secondary_muscles": "triceps, shoulders, core",
            "cues": "1. Keep rings close to body\n2. Break 90 degrees\n3. Lock out at top and turn rings out"
        },
        {
            "category": "Bodyweight", "name": "Ring Push-ups", 
            "primary_muscle": "chest", "secondary_muscles": "triceps, shoulders, core",
            "cues": "1. Maintain hollow body\n2. Rings turned out at top\n3. Full protraction of shoulder blades"
        },
        {
            "category": "Bodyweight", "name": "Pull-ups", 
            "primary_muscle": "latissimus", "secondary_muscles": "upper-back, biceps, forearms, core",
            "cues": "1. Hollow body\n2. Pull elbows down and back\n3. Chin clearly over bar"
        },
        {
            "category": "Bodyweight", "name": "Chin-ups", 
            "primary_muscle": "latissimus", "secondary_muscles": "biceps, upper-back, core",
            "cues": "1. Supinated (underhand) grip\n2. Drive chest to bar\n3. Squeeze biceps at top"
        },
        {
            "category": "Bodyweight", "name": "Ring Muscle-ups", 
            "primary_muscle": "latissimus", "secondary_muscles": "upper-back, chest, triceps, shoulders, core",
            "cues": "1. Deep false grip\n2. Explosive pull to sternum\n3. Aggressive sit-up transition\n4. Keep rings tight to chest"
        },
        {
            "category": "Bodyweight", "name": "Front Lever Holds", 
            "primary_muscle": "latissimus", "secondary_muscles": "upper-back, core",
            "cues": "1. Depress and retract scapulae\n2. Keep arms perfectly straight\n3. Squeeze glutes and point toes"
        },
        {
            "category": "Bodyweight", "name": "Planche Progressions", 
            "primary_muscle": "shoulders", "secondary_muscles": "chest, triceps, core",
            "cues": "1. Protracted scapulae (hollow back)\n2. Straight arms\n3. Lean forward deeply"
        },
        {
            "category": "Bodyweight", "name": "Wall Handstand Holds", 
            "primary_muscle": "shoulders", "secondary_muscles": "triceps, upper-back, core",
            "cues": "1. Push tall through shoulders\n2. Squeeze glutes for hollow body\n3. Look at space between hands"
        },
        {
            "category": "Bodyweight", "name": "Handstand Push-ups", 
            "primary_muscle": "shoulders", "secondary_muscles": "triceps, upper-back, core",
            "cues": "1. Create a tripod with head and hands\n2. Control the descent\n3. Press back towards the wall on ascent"
        },
        {
            "category": "Bodyweight", "name": "Pistol Squats", 
            "primary_muscle": "quadriceps", "secondary_muscles": "glutes, calves, core",
            "cues": "1. Control the descent\n2. Keep planted heel on floor\n3. Drive up through mid-foot"
        },
        {
            "category": "Bodyweight", "name": "Nordic Curls", 
            "primary_muscle": "hamstrings", "secondary_muscles": "glutes, calves",
            "cues": "1. Squeeze glutes to lock hips\n2. Hinge only at knees\n3. Fight the eccentric descent as long as possible"
        },
        {
            "category": "Bodyweight", "name": "L-Sit", 
            "primary_muscle": "core", "secondary_muscles": "triceps, shoulders, quadriceps",
            "cues": "1. Push floor away (depress shoulders)\n2. Lock knees straight\n3. Point toes"
        },
        {
            "category": "Bodyweight", "name": "Human Flag", 
            "primary_muscle": "core", "secondary_muscles": "latissimus, shoulders, obliques",
            "cues": "1. Push bottom arm, pull top arm\n2. Lock core and obliques tight\n3. Keep a straight line from head to toe"
        },
        
        # --- POWER RACK / BARBELL ---
        {
            "category": "Barbell", "name": "Barbell Back Squats", 
            "primary_muscle": "quadriceps", "secondary_muscles": "glutes, hamstrings, lower-back, core",
            "cues": "1. Brace core hard\n2. Break at hips and knees simultaneously\n3. Drive chest up out of the hole"
        },
        {
            "category": "Barbell", "name": "Barbell Front Squats", 
            "primary_muscle": "quadriceps", "secondary_muscles": "glutes, lower-back, core",
            "cues": "1. Keep elbows high\n2. Maintain an upright torso\n3. Drive through mid-foot"
        },
        {
            "category": "Barbell", "name": "Barbell Bench Press", 
            "primary_muscle": "chest", "secondary_muscles": "triceps, shoulders",
            "cues": "1. Pin scapulae together and down\n2. Drive feet into floor\n3. Try to bend the bar\n4. Push yourself into the bench"
        },
        {
            "category": "Barbell", "name": "Incline Bench Press", 
            "primary_muscle": "chest", "secondary_muscles": "shoulders, triceps",
            "cues": "1. Maintain slight arch\n2. Touch high on chest\n3. Press back over eyes"
        },
        {
            "category": "Barbell", "name": "Barbell Overhead Press", 
            "primary_muscle": "shoulders", "secondary_muscles": "triceps, core, upper-back",
            "cues": "1. Squeeze glutes and brace core\n2. Keep bar path perfectly straight up\n3. Push head through window at the top"
        },
        {
            "category": "Barbell", "name": "Barbell Deadlift", 
            "primary_muscle": "glutes", "secondary_muscles": "hamstrings, lower-back, quadriceps, upper-back",
            "cues": "1. Hinge hips back\n2. Drag bar up the shins\n3. Drive the floor away with your legs"
        },
        {
            "category": "Barbell", "name": "Romanian Deadlift (RDL)", 
            "primary_muscle": "hamstrings", "secondary_muscles": "glutes, lower-back",
            "cues": "1. Soft knees, do not bend further\n2. Push hips straight back to the wall\n3. Stop when hamstrings are fully stretched"
        },
        {
            "category": "Barbell", "name": "Barbell Rows", 
            "primary_muscle": "upper-back", "secondary_muscles": "latissimus, biceps, lower-back",
            "cues": "1. Hinge torso almost parallel to floor\n2. Pull bar to belly button\n3. Squeeze shoulder blades together"
        },
        {
            "category": "Barbell", "name": "Good Mornings", 
            "primary_muscle": "hamstrings", "secondary_muscles": "glutes, lower-back",
            "cues": "1. Keep bar low on back\n2. Hinge deeply with straight back\n3. Drive hips forward to stand"
        },
        
        # --- DUMBBELL / ACCESSORY ---
        {
            "category": "Dumbbell", "name": "Dumbbell Bicep Curls", 
            "primary_muscle": "biceps", "secondary_muscles": "forearms",
            "cues": "1. Pin elbows to your sides\n2. Achieve full extension at bottom\n3. Squeeze hard at the top"
        },
        {
            "category": "Dumbbell", "name": "Hammer Curls", 
            "primary_muscle": "biceps", "secondary_muscles": "forearms",
            "cues": "1. Maintain neutral grip\n2. Use zero momentum\n3. Control the descent"
        },
        {
            "category": "Dumbbell", "name": "Overhead Tricep Extensions", 
            "primary_muscle": "triceps", "secondary_muscles": "",
            "cues": "1. Keep elbows tucked in\n2. Get a deep stretch at bottom\n3. Lock out fully at the top"
        },
        {
            "category": "Dumbbell", "name": "Tricep Pushdowns", 
            "primary_muscle": "triceps", "secondary_muscles": "",
            "cues": "1. Keep shoulders locked down\n2. Keep elbows fixed at sides\n3. Spread rope at the very bottom"
        },
        {
            "category": "Dumbbell", "name": "Lateral Raises", 
            "primary_muscle": "shoulders", "secondary_muscles": "",
            "cues": "1. Slight forward lean\n2. Lead with the pinkies\n3. Control the negative drop"
        },
        {
            "category": "Dumbbell", "name": "Calf Raises", 
            "primary_muscle": "calves", "secondary_muscles": "",
            "cues": "1. Get a full stretch at the bottom\n2. Explode up onto toes\n3. Hold the top contraction for 1 second"
        },
        {
            "category": "Dumbbell", "name": "Hanging Leg Raises", 
            "primary_muscle": "core", "secondary_muscles": "forearms, quadriceps",
            "cues": "1. Maintain an active hang\n2. Eliminate all swinging\n3. Pull toes to bar (or 90 degrees)"
        },
        {
            "category": "Dumbbell", "name": "Farmer's Walk", 
            "primary_muscle": "forearms", "secondary_muscles": "core, upper-back, calves",
            "cues": "1. Chest up, shoulders back\n2. Take short, quick steps\n3. Try to crush the grip handles"
        }
    ]