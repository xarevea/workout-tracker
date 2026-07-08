# ========================================
# FILE PATH: core/models.py
# ========================================
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

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

# Add remaining mapped classes (Workouts, Programs, etc.) here as you transition. 
# SQLAlchemy can comfortably sit right alongside raw sqlite3 during the transition.