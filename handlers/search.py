from telebot import types
from database.models import User
from database.db import get_db
from sqlalchemy.orm import Session

def register_search_handlers(bot):
    @bot.message_handler(commands=['search'])
    @bot.message_handler(func=lambda message: message.text == "🔍 Поиск")
    def search_profiles(message):
        db: Session = next(get_db())
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            bot.send_message(message.chat.id, "Сначала создайте анкету (/profile)")
            return
        
        if user.search_by_interests:
            query = db.query(User).filter(
                User.telegram_id != message.from_user.id,
                User.is_active == True,
                User.region == user.region
            )
        else:
            query = db.query(User).filter(
                User.telegram_id != message.from_user.id,
                User.is_active == True
            )
        
        profiles = query.limit(10).all()
        
        if not profiles:
            bot.send_message(message.chat.id, "Нет подходящих анкет")
            return
        
        show_profile(message.chat.id, profiles[0], 0, len(profiles))
    
    def show_profile(chat_id, profile, index, total):
        text = f"Анкета {index+1}/{total}\n\n"
        text += f"👤 Имя: {profile.name}\n"
        if profile.age:
            text += f"🎂 Возраст: {profile.age}\n"
        text += f"🌍 Регион: {profile.region}\n"
        text += f"🎮 Платформа: {profile.platform}\n"
        
        if profile.favorite_games:
            text += f"🎲 Игры: {', '.join(profile.favorite_games[:5])}\n"
        
        if profile.genres:
            text += f"📁 Жанры: {', '.join(profile.genres[:5])}\n"
        
        if profile.about:
            text += f"\n📝 О себе:\n{profile.about}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{profile.telegram_id}"),
            types.InlineKeyboardButton("👎 Пропустить", callback_data=f"skip_{profile.telegram_id}")
        )
        
        if profile.photos:
            bot.send_photo(chat_id, profile.photos[0], caption=text, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)