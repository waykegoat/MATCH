from telebot import types
from database.models import User, Like
from database.db import get_db
from sqlalchemy.orm import Session
from datetime import datetime

def register_likes_handlers(bot):
    @bot.message_handler(commands=['likes'])
    @bot.message_handler(func=lambda message: message.text == "❤️ Лайки")
    def show_likes(message):
        db: Session = next(get_db())
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            bot.send_message(message.chat.id, "Сначала создайте анкету (/profile)")
            return
        
        likes = db.query(User).filter(User.telegram_id.in_(user.likes_received)).all()
        
        if not likes:
            bot.send_message(message.chat.id, "У вас пока нет лайков")
            return
        
        text = f"❤️ Вас лайкнули ({len(likes)}):\n\n"
        for like_user in likes[:10]:
            text += f"👤 {like_user.name} (@{like_user.username or 'нет username'})\n"
        
        markup = types.InlineKeyboardMarkup()
        for like_user in likes[:5]:
            markup.add(types.InlineKeyboardButton(
                f"Посмотреть {like_user.name}", 
                callback_data=f"view_like_{like_user.telegram_id}"
            ))
        
        bot.send_message(message.chat.id, text, reply_markup=markup)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('like_'))
    def handle_like(call):
        target_id = int(call.data.split('_')[1])
        db: Session = next(get_db())
        
        user = db.query(User).filter(User.telegram_id == call.from_user.id).first()
        target_user = db.query(User).filter(User.telegram_id == target_id).first()
        
        if not user or not target_user:
            bot.answer_callback_query(call.id, "Ошибка!")
            return
        
        if target_id not in user.likes_given:
            user.likes_given.append(target_id)
            target_user.likes_received.append(call.from_user.id)
        
        if call.from_user.id in target_user.likes_given:
            if target_id not in user.matches:
                user.matches.append(target_id)
            if call.from_user.id not in target_user.matches:
                target_user.matches.append(call.from_user.id)
            
            bot.answer_callback_query(call.id, "Мэтч! Вы понравились друг другу!")
            
            if target_user.username:
                bot.send_message(call.message.chat.id, 
                               f"🎉 Мэтч! Напишите @{target_user.username}")
            if user.username and call.from_user.id not in target_user.likes_given:
                bot.send_message(target_user.telegram_id,
                               f"🎉 Мэтч! Напишите @{user.username}")
        else:
            bot.answer_callback_query(call.id, "Лайк отправлен!")
        
        db.commit()
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Следующий", callback_data="next_profile"))
        
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)