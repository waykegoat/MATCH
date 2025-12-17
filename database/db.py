# database/db.py
import os
from sqlalchemy import create_engine, inspect, text
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

print(f"📦 Подключаемся к БД: {'***' + database_url.split('@')[1] if '@' in database_url else database_url}")

# Разные настройки для PostgreSQL и SQLite
if 'postgresql' in database_url:
    engine = create_engine(
        database_url,
        echo=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
else:
    engine = create_engine(
        database_url,
        echo=True,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """Создает таблицы в БД с проверкой"""
    try:
        # ВАЖНО: импорт моделей ДО создания таблиц
        from database.models import User, Profile, Like, Message, Notification
        
        print("🔄 Создаем таблицы в БД...")
        Base.metadata.create_all(bind=engine)
        
        # Проверяем, что таблицы создались
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Таблицы в БД: {tables}")
        
        if 'users' not in tables:
            print("⚠️ Таблица 'users' не найдена! Пробуем принудительно...")
            # Пробуем выполнить CREATE TABLE напрямую
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        username VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        name VARCHAR(255),
                        age INTEGER,
                        region VARCHAR(100),
                        platform VARCHAR(100),
                        favorite_games TEXT,
                        about TEXT,
                        photos TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        search_by_interests BOOLEAN DEFAULT FALSE,
                        likes_given INTEGER DEFAULT 0,
                        likes_received INTEGER DEFAULT 0,
                        matches INTEGER DEFAULT 0
                    )
                """))
                conn.commit()
        
        print(f"✅ База данных инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    """Проверяет подключение к БД"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False