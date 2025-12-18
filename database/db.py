import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Получаем URL из окружения Railway
database_url = os.getenv('DATABASE_URL', 'sqlite:///gamers.db')

# Если Railway дал postgres:// - конвертируем
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

print(f"📦 Подключаемся к БД: {database_url}")

# Настройки для разных БД
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
        
        # Удаляем старые таблицы и создаем новые
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Проверяем
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"✅ Таблицы созданы: {tables}")
        
        if 'users' not in tables:
            print("❌ КРИТИЧЕСКО: таблица 'users' не создана!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        return False