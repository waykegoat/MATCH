from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, JSON, DateTime, ForeignKey
from sqlalchemy import BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)  # BigInteger вместо Integer
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
    
    # ИЗМЕНЕНИЕ: Integer для счетчиков, JSON для списков
    likes_given_count = Column(Integer, default=0)
    likes_received_count = Column(Integer, default=0)
    matches_count = Column(Integer, default=0)
    
    # JSON списки для хранения ID
    likes_given = Column(JSON, default=list)  # Список telegram_id кому лайкнул
    likes_received = Column(JSON, default=list)  # Список telegram_id от кого лайки
    matches = Column(JSON, default=list)  # Список telegram_id мэтчей
    
    # Связи
    profile = relationship("Profile", back_populates="user", uselist=False)
    likes_sent = relationship("Like", foreign_keys="Like.from_user_id", back_populates="from_user")
    likes_received_rel = relationship("Like", foreign_keys="Like.to_user_id", back_populates="to_user")

class Profile(Base):
    __tablename__ = 'profiles'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    game = Column(String(100))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="profile")

class Like(Base):
    __tablename__ = 'likes'
    
    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey('users.id'))
    to_user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="likes_sent")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="likes_received_rel")

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey('users.id'))
    to_user_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    
    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    type = Column(String(50))  # 'like', 'match', 'message'
    content = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")