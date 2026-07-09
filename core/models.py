import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class ExerciseMode(enum.Enum):
    STANDARD = "Standard"
    CIRCUIT = "Circuit"
    EMOM = "EMOM"

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)

class BodyweightLog(Base):
    __tablename__ = 'bodyweight_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), default=1)
    date = Column(String, default="CURRENT_DATE")
    weight_lbs = Column(Float, nullable=False)
    notes = Column(String)

class Equipment(Base):
    __tablename__ = 'equipment'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), default=1)
    name = Column(String, nullable=False)
    weight_lbs = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    is_barbell = Column(Boolean, default=False)

class Exercise(Base):
    __tablename__ = 'exercises'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    primary_muscle = Column(String)
    secondary_muscles = Column(String)
    cues = Column(String)
    tracks_weight = Column(Boolean, default=True)
    tracks_time = Column(Boolean, default=False)
    media_path = Column(String)

class Workout(Base):
    __tablename__ = 'workouts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), default=1)
    date = Column(String)
    name = Column(String, nullable=False)
    duration_minutes = Column(Integer)
    bodyweight_at_time = Column(Float)
    logs = relationship("WorkoutLog", back_populates="workout", cascade="all, delete-orphan")

class WorkoutLog(Base):
    __tablename__ = 'workout_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_id = Column(Integer, ForeignKey('workouts.id'))
    exercise_id = Column(Integer, ForeignKey('exercises.id'))
    set_number = Column(Integer)
    reps = Column(Integer)
    weight_lbs = Column(Float)
    rpe = Column(Float)
    target_hit = Column(Boolean, default=False)
    is_warmup = Column(Boolean, default=False)
    workout = relationship("Workout", back_populates="logs")
    exercise = relationship("Exercise")

class ApiIntegration(Base):
    __tablename__ = 'api_integrations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_name = Column(String, nullable=False, unique=True)
    access_token = Column(String)
    refresh_token = Column(String)
    token_expires_at = Column(Float)

class RoutineTemplate(Base):
    __tablename__ = 'routine_templates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=False)
    exercises = relationship("RoutineExercise", back_populates="template", cascade="all, delete-orphan")

class RoutineExercise(Base):
    __tablename__ = 'routine_exercises'
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey('routine_templates.id'))
    exercise_name = Column(String, nullable=False)
    target_sets = Column(Integer)
    target_reps_min = Column(Integer, default=8)
    target_reps_max = Column(Integer, default=10)
    target_weight = Column(Float)
    rest_seconds = Column(Integer, default=90)
    is_bodyweight = Column(Boolean, default=False)

    # Strictly typed Enums at the database level
    mode = Column(SQLEnum(ExerciseMode), default=ExerciseMode.STANDARD)
    circuit_group = Column(Integer, default=0)

    template = relationship("RoutineTemplate", back_populates="exercises")

class Program(Base):
    __tablename__ = 'programs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), default=1)
    name = Column(String, nullable=False)
    cycle_length_days = Column(Integer, default=7)
    total_cycles = Column(Integer, default=4)
    is_active = Column(Boolean, default=False)
    days = relationship("ProgramDay", back_populates="program", cascade="all, delete-orphan")

class ProgramDay(Base):
    __tablename__ = 'program_days'
    id = Column(Integer, primary_key=True, autoincrement=True)
    program_id = Column(Integer, ForeignKey('programs.id'))
    day_number = Column(Integer)
    template_id = Column(Integer, ForeignKey('routine_templates.id'))
    is_deload = Column(Boolean, default=False)
    program = relationship("Program", back_populates="days")
    template = relationship("RoutineTemplate")