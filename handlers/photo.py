from telebot import types
from database.models import User
from database.db import get_db
from sqlalchemy.orm import Session

print(f"File ID для оформления: {file_id}")

def register_photo_handlers(bot):
    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        db: Session = next(get_db())
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            bot.send_message(message.chat.id, "Сначала создайте анкету (/profile)")
            return
        
        file_id = message.photo[-1].file_id
        
        if len(user.photos) >= 5:
            bot.send_message(message.chat.id, "Можно загрузить максимум 5 фото")
            return
        
        user.photos.append(file_id)
        db.commit()
        
        bot.send_message(message.chat.id, f"Фото добавлено! У вас {len(user.photos)} фото")
    
    @bot.message_handler(commands=['photos'])
    def manage_photos(message):
        db: Session = next(get_db())
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            bot.send_message(message.chat.id, "Сначала создайте анкету (/profile)")
            return
        
        if not user.photos:
            bot.send_message(message.chat.id, "У вас нет фото. Отправьте фото для добавления")
            return
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Удалить все фото", callback_data="delete_all_photos"))
        
        for i, photo_id in enumerate(user.photos):
            markup.add(types.InlineKeyboardButton(f"Удалить фото {i+1}", callback_data=f"delete_photo_{i}"))
        
        bot.send_message(message.chat.id, "Управление фото:", reply_markup=markup)