from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import Config

# Используем DATABASE_URL из Config (Railway сам его установит)
if Config.DATABASE_URL:
    engine = create_engine(Config.DATABASE_URL)
else:
    # Fallback для локальной разработки
    engine = create_engine('sqlite:///gamers.db', connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from database.models import User
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()