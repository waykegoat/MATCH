from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from .models import Base

engine = create_engine(Config.DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("База данных инициализирована")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()