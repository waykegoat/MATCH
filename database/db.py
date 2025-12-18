import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Получаем URL из окружения Railway
database_url = os.getenv('DATABASE_URL')

# Если Railway дал postgres:// - конвертируем в postgresql://
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Если нет PostgreSQL URL, используем SQLite (только для тестов)
if not database_url:
    database_url = 'sqlite:///gamers.db'

print(f"📦 Подключаемся к БД: {database_url.split('@')[-1] if '@' in database_url else database_url}")

# РАЗНЫЕ НАСТРОЙКИ ДЛЯ PostgreSQL и SQLite
if 'postgresql' in database_url:
    # PostgreSQL - постоянная БД
    engine = create_engine(
        database_url,
        echo=True,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
else:
    # SQLite - только для разработки (данные не сохраняются)
    engine = create_engine(
        database_url,
        echo=True,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Генератор сессий для зависимостей"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Создает таблицы в БД"""
    try:
        print("🔄 Создаем таблицы в БД...")
        
        # Импортируем ВСЕ модели
        import database.models
        
        # Создаем таблицы (не удаляем старые!)
        Base.metadata.create_all(bind=engine)
        
        # Проверяем
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Таблицы в БД: {tables}")
        
        if 'users' not in tables:
            print("⚠️ Таблица 'users' не найдена, создаем...")
            Base.metadata.create_all(bind=engine)
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        return False