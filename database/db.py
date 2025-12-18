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

# ДОБАВЬ ЭТУ ФУНКЦИЮ:
def get_db():
    """Генератор сессий для зависимостей"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        
        # Проверяем структуру
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Таблицы созданы: {tables}")
        
        if 'users' in tables:
            # Проверяем колонки
            columns = inspector.get_columns('users')
            column_names = [col['name'] for col in columns]
            print(f"📊 Колонки users: {column_names}")
            
            # Проверяем наличие нужных колонок
            required_columns = ['likes_given', 'likes_received', 'matches', 
                               'likes_given_count', 'likes_received_count', 'matches_count']
            missing = [col for col in required_columns if col not in column_names]
            if missing:
                print(f"⚠️ Отсутствуют колонки: {missing}")
        
        print("✅ База данных инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        return False