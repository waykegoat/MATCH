from sqlalchemy import Column, Integer, String, Boolean, Text, JSON, DateTime, BigInteger
from datetime import datetime
from database.db import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    name = Column(String(100))
    age = Column(Integer, nullable=True)
    region = Column(String(100))
    platform = Column(String(50))
    favorite_games = Column(JSON, default=list)
    about = Column(Text, nullable=True)
    
    photos = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    search_by_interests = Column(Boolean, default=True)
    
    # Счетчики
    likes_given_count = Column(Integer, default=0)
    likes_received_count = Column(Integer, default=0)
    matches_count = Column(Integer, default=0)
    
    # JSON списки для хранения ID
    likes_given = Column(JSON, default=list)
    likes_received = Column(JSON, default=list)
    matches = Column(JSON, default=list)
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', telegram_id={self.telegram_id})>"

# ДОБАВЬТЕ ЭТИ МОДЕЛИ:
class Like(Base):
    __tablename__ = 'likes'
    
    id = Column(Integer, primary_key=True)
    from_user_id = Column(BigInteger, nullable=False)
    to_user_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    from_user_id = Column(BigInteger, nullable=False)
    to_user_id = Column(BigInteger, nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    type = Column(String(50))
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)