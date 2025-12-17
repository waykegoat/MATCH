from telebot import types
from telebot.handler_backends import State, StatesGroup
from database.models import User
from database.db import get_db
from sqlalchemy.orm import Session
import json

class ProfileStates(StatesGroup):
    name = State()
    age = State()
    region = State()
    platform = State()
    games = State()
    genres = State()
    ranks = State()
    about = State()
    photo = State()

def register_profile_handlers(bot):
    @bot.message_handler(commands=['profile'])
    def start_profile(message):
        bot.set_state(message.from_user.id, ProfileStates.name, message.chat.id)
        bot.send_message(message.chat.id, "Введите ваше имя:")
    
    @bot.message_handler(state=ProfileStates.name)
    def process_name(message):
        bot.set_state(message.from_user.id, ProfileStates.age, message.chat.id)
        bot.send_message(message.chat.id, "Введите ваш возраст (или напишите 'пропустить'):")
    
    @bot.message_handler(state=ProfileStates.age)
    def process_age(message):
        from config import Config
        
        if message.text.lower() == 'пропустить':
            age = None
        else:
            try:
                age = int(message.text)
                if age < 13 or age > 100:
                    bot.send_message(message.chat.id, "Введите корректный возраст (13-100):")
                    return
            except:
                bot.send_message(message.chat.id, "Введите число или 'пропустить':")
                return
        
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['age'] = age
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for region in Config.REGIONS:
            markup.add(types.KeyboardButton(region))
        
        bot.set_state(message.from_user.id, ProfileStates.region, message.chat.id)
        bot.send_message(message.chat.id, "Выберите ваш регион:", reply_markup=markup)