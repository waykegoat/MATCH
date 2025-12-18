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

# database/db.py - исправленная функция init_db()
def init_db():
    """Создает таблицы в БД с правильной структурой"""
    try:
        # ВАЖНО: импорт моделей ДО создания таблиц
        from database.models import User, Profile, Like, Message, Notification
        
        print("🔄 Создаем таблицы в БД...")
        
        # Для SQLite: удаляем старые таблицы если есть
        if 'sqlite' in str(engine.url):
            print("🗑️ Очищаем старые таблицы для SQLite...")
            Base.metadata.drop_all(bind=engine)
        
        # Создаем таблицы с новой структурой
        Base.metadata.create_all(bind=engine)
        
        print("✅ Таблицы созданы с JSON полями")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        
        # Пробуем создать таблицу напрямую
        try:
            from sqlalchemy import text
            
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                name VARCHAR(255),
                age INTEGER,
                region VARCHAR(100),
                platform VARCHAR(100),
                favorite_games TEXT,  -- JSON как TEXT
                about TEXT,
                photos TEXT,  -- JSON как TEXT
                is_active BOOLEAN DEFAULT TRUE,
                search_by_interests BOOLEAN DEFAULT FALSE,
                likes_given TEXT DEFAULT '[]',  -- JSON как TEXT
                likes_received TEXT DEFAULT '[]',  -- JSON как TEXT
                matches TEXT DEFAULT '[]',  -- JSON как TEXT
                likes_given_count INTEGER DEFAULT 0,
                likes_received_count INTEGER DEFAULT 0,
                matches_count INTEGER DEFAULT 0
            )
            """
            
            with engine.connect() as conn:
                conn.execute(text(create_table_sql))
                conn.commit()
            
            print("✅ Таблица users создана напрямую")
            return True
        except Exception as e2:
            print(f"❌ Ошибка прямого создания таблицы: {e2}")
            return False