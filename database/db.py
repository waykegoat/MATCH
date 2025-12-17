# database/db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Получаем URL из окружения Railway
database_url = os.getenv('DATABASE_URL')

# Если Railway не дал URL (локальная разработка) - используем SQLite
if not database_url:
    database_url = 'sqlite:///gamers.db'
# Если Railway дал postgres:// - конвертируем в postgresql://
elif database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

engine = create_engine(
    database_url,
    echo=True,  # Для отладки в логах Railway
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """Создает таблицы в БД"""
    from database.models import User
    Base.metadata.create_all(bind=engine)
    print(f"✅ Таблицы созданы в БД: {database_url.split('@')[1] if '@' in database_url else database_url}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()