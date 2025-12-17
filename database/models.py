from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    name = Column(String(100))
    age = Column(Integer, nullable=True)
    region = Column(String(10))
    platform = Column(String(20))
    favorite_games = Column(JSON, default=list)
    about = Column(Text, nullable=True)
    
    photos = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    search_by_interests = Column(Boolean, default=True)  # Добавили это поле
    
    likes_given = Column(JSON, default=list)
    likes_received = Column(JSON, default=list)
    matches = Column(JSON, default=list)