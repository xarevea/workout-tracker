import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tracker.db')

engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session():
    """Context manager for SQLAlchemy ORM sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def initialize_database():
    from core.models import Base, User
    Base.metadata.create_all(bind=engine)
    
    with get_db_session() as session:
        if not session.query(User).filter_by(id=1).first():
            session.add(User(id=1, username="Default User"))
            
        from core.models import Exercise
        if session.query(Exercise).count() == 0:
            try:
                from core.default_data import get_default_exercises
                for ex in get_default_exercises():
                    cues = ex.get('cues', "1. Focus on form\n2. Maintain tension")
                    session.add(Exercise(name=ex['name'], category=ex.get('category', 'Strength'), primary_muscle=ex['primary_muscle'], secondary_muscles=ex['secondary_muscles'], cues=cues))
            except ImportError: pass
            
    print(f"Database successfully verified/initialized via ORM at {DB_PATH}")