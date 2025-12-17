import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_TOKEN = os.getenv('ADMIN_TOKEN')
    
    # Railway автоматически создает DATABASE_URL для PostgreSQL
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Если Railway предоставляет PostgreSQL, конвертируем URL
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Настройки канала
    CHANNEL_ID = os.getenv('CHANNEL_ID', '@dimbub')
    CHANNEL_URL = os.getenv('CHANNEL_URL', 'https://t.me/dimbub')
    
    # Игры
    ALL_GAMES = [
        "🎮 Dota 2", "🎮 CS:GO", "🎮 Valorant", "🎮 League of Legends", "🎮 Apex Legends",
        "🎮 PUBG", "🎮 Fortnite", "🎮 Overwatch 2", "🎮 World of Warcraft", "🎮 Minecraft",
        "🎮 GTA V", "🎮 Rainbow Six Siege", "🎮 Call of Duty", "🎮 Rust", "🎮 Ark",
        "🎮 Teamfight Tactics", "🎮 Hearthstone", "🎮 TFT", "🎮 Path of Exile", "🎮 Warframe",
        "🎮 Escape from Tarkov", "🎮 Lost Ark", "🎮 Mobile Legends", "🎮 Wild Rift"
    ]
    
    # Регионы
    REGIONS = ["🇷🇺 Россия", "🇺🇦 Украина", "🇧🇾 Беларусь", "🇰🇿 Казахстан", "🌍 Другое"]
    
    # Платформы
    PLATFORMS = ["PC", "PlayStation", "Xbox", "Mobile", "Nintendo Switch"]