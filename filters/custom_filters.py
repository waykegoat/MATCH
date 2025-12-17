from telebot import types
from telebot.custom_filters import AdvancedCustomFilter

class IsAdminFilter(AdvancedCustomFilter):
    key = 'is_admin'
    
    def check(self, message, text):
        from config import Config
        return message.from_user.id == Config.ADMIN_ID

class HasProfileFilter(AdvancedCustomFilter):
    key = 'has_profile'
    
    def check(self, message, text):
        from database.db import get_db
        from database.models import User
        from sqlalchemy.orm import Session
        
        db: Session = next(get_db())
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        return user is not None