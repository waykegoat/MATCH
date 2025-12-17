import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///database.db')
    
    REGIONS = ['EU', 'RU', 'SA', 'NA']
    PLATFORMS = ['PC', 'Mobile', 'PS/XBOX']
    
    GENRES = [
        'Фэнтези', 'Хоррор', 'PVP', 'PVE', 
        'MMO RPG', 'Шутеры', 'Battle Royale', 'Песочницы'
    ]
    
    ALL_GAMES = [
        'Roblox', 'Dota 2', 'Valorant', 'Counter-Strike 2', 
        'Overwatch', 'Marvel Rivals', 'Souls Like', 'Minecraft',
        'Arc Riders', 'Fortnite', 'PUBG', 'Mobile Legends', 'LOL'
    ]
    
    COMPETITIVE_GAMES = {
        'Counter-Strike 2': ['Silver', 'Gold Nova', 'Master Guardian', 'Legendary Eagle', 'Global Elite'],
        'Valorant': ['Iron', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Diamond', 'Immortal', 'Radiant'],
        'Dota 2': ['Herald', 'Guardian', 'Crusader', 'Archon', 'Legend', 'Ancient', 'Divine', 'Immortal'],
        'Mobile Legends': ['Warrior', 'Elite', 'Master', 'Grandmaster', 'Epic', 'Legend', 'Mythic'],
        'LOL': ['Iron', 'Bronze', 'Silver', 'Gold', 'Platinum', 'Emerald', 'Diamond', 'Master', 'Grandmaster', 'Challenger']
    }