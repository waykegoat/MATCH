import telebot
from telebot import types
from telebot.storage import StateMemoryStorage
from config import Config
import random
from datetime import datetime, timedelta
from collections import Counter
import os
import time
import traceback
import sys

# ========== СОЗДАНИЕ БОТА В САМОМ НАЧАЛЕ ==========
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(Config.BOT_TOKEN, state_storage=state_storage)

# ========== ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК ==========
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Глобальный обработчик необработанных исключений"""
    print("="*60)
    print("🔥 НЕОБРАБОТАННАЯ ОШИБКА В КОДЕ:")
    print("="*60)
    print(f"Тип: {exc_type.__name__}")
    print(f"Сообщение: {exc_value}")
    print("\nТрассировка:")
    
    tb = traceback.extract_tb(exc_traceback)
    if tb:
        last_frame = tb[-1]
        print(f"Файл: {last_frame.filename}")
        print(f"Строка: {last_frame.lineno}")
        print(f"Функция: {last_frame.name}")
        print(f"Код: {last_frame.line}")
    
    print("="*60)

sys.excepthook = global_exception_handler

# ========== ИНИЦИАЛИЗАЦИЯ БД ==========
try:
    print("🔄 Инициализация базы данных...")
    from database.db import init_db
    init_db()
    print("✅ База данных инициализирована")
except Exception as e:
    print(f"⚠️ Ошибка инициализации БД: {e}")

# ========== ИМПОРТ МОДЕЛЕЙ И ФУНКЦИЙ БД ==========
from database.db import SessionLocal, get_db
from database.models import User
from sqlalchemy.orm.attributes import flag_modified

# ========== ВАЖНОЕ ИСПРАВЛЕНИЕ ==========
# Добавляем очистку кэша в get_db_session
def get_db_session():
    """Создает новую сессию БД с очисткой кэша"""
    try:
        # Создаем новую сессию
        db = SessionLocal()
        
        # ВАЖНО: Очищаем кэш перед каждым использованием!
        db.expire_all()
        
        return db
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        
        # Пробуем переподключиться
        try:
            from database.db import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            db = SessionLocal()
            db.expire_all()  # Очищаем кэш
            return db
        except:
            return None

# ========== ФУНКЦИИ ОФОРМЛЕНИЯ ==========
def send_formatted_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """Отправляет сообщение с оформлением (фото бота + текст)"""
    # Добавляем шапку и подпись
    formatted_text = f"""✨ *GamerMatch* ✨
    
{text}

🎮 *Найди свою идеальную команду!*"""
    
    # Если есть фото бота (file_id)
    if Config.BOT_PHOTO_FILE_ID:
        try:
            return bot.send_photo(
                chat_id=chat_id,
                photo=Config.BOT_PHOTO_FILE_ID,
                caption=formatted_text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Ошибка отправки фото (file_id): {e}")
            # Fallback на текст
            return bot.send_message(
                chat_id=chat_id,
                text=formatted_text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
    # Если есть URL фото
    elif Config.BOT_PHOTO_URL:
        try:
            return bot.send_photo(
                chat_id=chat_id,
                photo=Config.BOT_PHOTO_URL,
                caption=formatted_text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Ошибка отправки фото (URL): {e}")
            return bot.send_message(
                chat_id=chat_id,
                text=formatted_text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
    else:
        # Без фото
        return bot.send_message(
            chat_id=chat_id,
            text=formatted_text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )

def edit_formatted_message(chat_id, message_id, text, reply_markup=None, parse_mode='Markdown'):
    """Редактирует сообщение с оформлением"""
    formatted_text = f"""✨ *GamerMatch* ✨
    
{text}

🎮 *Найди свою идеальную команду!*"""
    
    try:
        return bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=formatted_text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Ошибка редактирования сообщения: {e}")
        # Если не получается отредактировать (сообщение с фото),
        # удаляем старое и отправляем новое
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        return send_formatted_message(chat_id, text, reply_markup, parse_mode)

# ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
profile_data = {}
editing_state = {}
admin_sessions = {}
admin_delete_data = {}

ALL_GAMES_WITH_CHAT = Config.ALL_GAMES + ['💬 Общение']

CHANNEL_ID = "@dimbub"
CHANNEL_URL = "https://t.me/dimbub"

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "📝 Моя анкета",
        "🔍 Искать игроков",
        "❤️ Мои лайки",
        "💌 Мэтчи",
        "⚙️ Настройки",
        "❓ Помощь"
    ]
    for i in range(0, len(buttons), 2):
        markup.add(*buttons[i:i+2])
    return markup

def check_subscription_sync(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def require_subscription_callback(func):
    def wrapper(call):
        user_id = call.from_user.id
        
        if check_subscription_sync(user_id):
            return func(call)
        else:
            show_subscription_required(call.message.chat.id, user_id)
            bot.answer_callback_query(call.id, "❌ Сначала подпишитесь на канал!")
    
    return wrapper

def show_subscription_required(chat_id, user_id):
    subscription_text = f"""🔒 Для использования бота необходимо подписаться на наш канал!

📢 Канал: {CHANNEL_ID}
🔗 Ссылка: {CHANNEL_URL}

📌 После подписки нажмите кнопку '✅ Я подписался'"""
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("📢 Перейти в канал", url=CHANNEL_URL),
        types.InlineKeyboardButton("✅ Я подписался", callback_data=f"check_sub_{user_id}")
    )
    
    bot.send_message(chat_id, subscription_text, reply_markup=markup)

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if not check_subscription_sync(user_id):
        show_subscription_required(message.chat.id, user_id)
        return
    
    welcome_text = """✨ *Основные функции:*
📝 Моя анкета - Создать/редактировать анкету
🔍 Искать игроков - Поиск по анкетам
❤️ Мои лайки - Кто вас лайкнул
💌 Мэтчи - Ваши взаимные лайки
⚙️ Настройки - Настройки поиска

📌 *Как работает:*
1. Создайте анкету с играми и интересами
2. Ищите людей через поиск
3. Ставьте лайки понравившимся
4. При взаимном лайке получаете контакт!

💬 Можно искать не только для игр, но и просто для общения!

📷 Чтобы добавить фото - просто отправьте его боту"""
    
    send_formatted_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_sub_'))
def check_subscription_callback(call):
    user_id = int(call.data.split('_')[2])
    
    if user_id != call.from_user.id:
        bot.answer_callback_query(call.id, "❌ Это не ваш запрос!")
        return
    
    if check_subscription_sync(user_id):
        bot.answer_callback_query(call.id, "✅ Отлично! Вы подписаны!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        welcome_text = """🎮 Добро пожаловать в GamerMatch!

✨ Основные функции:
📝 Моя анкета - Создать/редактировать анкету
🔍 Искать игроков - Поиск по анкетам
❤️ Мои лайки - Кто вас лайкнул
💌 Мэтчи - Ваши взаимные лайки
⚙️ Настройки - Настройки поиска

📌 Как работает:
1. Создайте анкету с играми и интересами
2. Ищите людей через поиск
3. Ставьте лайки понравившимся
4. При взаимном лайке получаете контакт!

💬 Можно искать не только для игр, но и просто для общения!

📷 Чтобы добавить фото - просто отправьте его боту"""
        
        bot.send_message(call.message.chat.id, welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())
    else:
        bot.answer_callback_query(call.id, "❌ Вы еще не подписаны! Подпишитесь и попробуйте снова.")

# ========== АНКЕТА ==========
@bot.message_handler(commands=['profile'])
@bot.message_handler(func=lambda message: message.text == "📝 Моя анкета")
def my_profile(message):
    user_id = message.from_user.id
    
    if not check_subscription_sync(user_id):
        show_subscription_required(message.chat.id, user_id)
        return
    
    db = get_db_session()
    
    if not db:
        bot.send_message(message.chat.id, "Ошибка подключения к базе данных.", reply_markup=get_main_keyboard())
        return
    
    try:
        # ОЧИЩАЕМ КЭШ перед поиском
        db.expire_all()
        
        # ⚠️ ВОТ ЭТО МЕСТО - запрос к таблице users!
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Создать анкету", callback_data="create_profile"))
            bot.send_message(message.chat.id, "У вас нет анкеты. Хотите создать?", reply_markup=markup)
            return
        
        profile_text = f"""📋 Ваша анкета:

👤 Имя: {user.name}
🌍 Регион: {user.region}
🎮 Платформа: {user.platform}
🎲 Интересы: {', '.join(user.favorite_games[:8]) if user.favorite_games else 'Не указаны'}"""
        
        if user.age:
            profile_text += f"\n🎂 Возраст: {user.age}"
        
        if user.about:
            profile_text += f"\n\n📝 О себе:\n{user.about[:200]}"
        
        profile_text += f"\n\n❤️ Лайков получено: {user.likes_received_count}"
        profile_text += f"\n💌 Мэтчей: {user.matches_count}"
        profile_text += f"\n📸 Фото: {len(user.photos) if user.photos else 0}"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ Редактировать", callback_data="edit_profile_menu"),
            types.InlineKeyboardButton("📸 Фото", callback_data="manage_photos")
        )
        markup.add(
            types.InlineKeyboardButton("⚙️ Настройки поиска", callback_data="search_settings"),
            types.InlineKeyboardButton("❌ Удалить анкету", callback_data="delete_profile")
        )
        
        if user.photos and len(user.photos) > 0:
            try:
                bot.send_photo(message.chat.id, user.photos[0], caption=profile_text, reply_markup=markup)
            except:
                bot.send_message(message.chat.id, profile_text, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, profile_text, reply_markup=markup)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(message.chat.id, "Ошибка при загрузке анкеты", reply_markup=get_main_keyboard())
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data == 'create_profile')
@require_subscription_callback
def create_profile_callback(call):
    user_id = call.from_user.id
    
    profile_data[user_id] = {
        'name': '',
        'username': call.from_user.username,
        'telegram_id': user_id,
        'games': []
    }
    
    bot.send_message(call.message.chat.id, "Введите ваше имя:")
    bot.register_next_step_handler(call.message, process_name)

def process_name(message):
    user_id = message.from_user.id
    name = message.text.strip()
    
    if not name or len(name) < 2:
        bot.send_message(message.chat.id, "Введите имя (минимум 2 символа):")
        bot.register_next_step_handler(message, process_name)
        return
    
    username = message.from_user.username
    
    profile_data[user_id] = {
        'name': name,
        'username': username,
        'telegram_id': user_id,
        'games': []
    }
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for region in Config.REGIONS:
        markup.add(types.KeyboardButton(region))
    
    bot.send_message(message.chat.id, "Выберите регион (это только для информации):", reply_markup=markup)
    bot.register_next_step_handler(message, process_region)

def process_region(message):
    user_id = message.from_user.id
    region = message.text.strip()
    
    if region not in Config.REGIONS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for reg in Config.REGIONS:
            markup.add(types.KeyboardButton(reg))
        bot.send_message(message.chat.id, "Выберите регион из списка:", reply_markup=markup)
        bot.register_next_step_handler(message, process_region)
        return
    
    profile_data[user_id]['region'] = region
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for platform in Config.PLATFORMS:
        markup.add(types.KeyboardButton(platform))
    
    bot.send_message(message.chat.id, "Выберите платформу (это только для информации):", reply_markup=markup)
    bot.register_next_step_handler(message, process_platform)

def process_platform(message):
    user_id = message.from_user.id
    platform = message.text.strip()
    
    if platform not in Config.PLATFORMS:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for plat in Config.PLATFORMS:
            markup.add(types.KeyboardButton(plat))
        bot.send_message(message.chat.id, "Выберите платформу из списка:", reply_markup=markup)
        bot.register_next_step_handler(message, process_platform)
        return
    
    profile_data[user_id]['platform'] = platform
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Введите ваш возраст (или напишите 'пропустить'):", reply_markup=markup)
    bot.register_next_step_handler(message, process_age)

def process_age(message):
    user_id = message.from_user.id
    age_text = message.text.strip().lower()
    age = None
    
    if age_text != 'пропустить':
        try:
            age = int(age_text)
            if age < 13 or age > 100:
                bot.send_message(message.chat.id, "Введите возраст от 13 до 100 лет (или 'пропустить'):")
                bot.register_next_step_handler(message, process_age)
                return
        except ValueError:
            bot.send_message(message.chat.id, "Введите число или 'пропустить':")
            bot.register_next_step_handler(message, process_age)
            return
    
    profile_data[user_id]['age'] = age
    
    bot.send_message(message.chat.id, "Расскажите о себе (ваши интересы, что ищете и т.д.):")
    bot.register_next_step_handler(message, process_about)

def process_about(message):
    user_id = message.from_user.id
    about = message.text.strip()
    
    profile_data[user_id]['about'] = about
    
    show_games_selection(message.chat.id, user_id, False)

def show_games_selection(chat_id, user_id, is_editing=False):
    if user_id not in profile_data:
        profile_data[user_id] = {'games': []}
    
    selected_games = profile_data[user_id].get('games', [])
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    games_to_show = ALL_GAMES_WITH_CHAT[:18]
    
    for i in range(0, len(games_to_show), 3):
        row_games = games_to_show[i:i+3]
        row_buttons = []
        for game in row_games:
            if game in selected_games:
                text = f"✅ {game}"
            else:
                text = f"⬜ {game}"
            callback_data = f"game_{game}_{user_id}"
            if is_editing:
                callback_data += "_edit"
            row_buttons.append(types.InlineKeyboardButton(text, callback_data=callback_data))
        markup.row(*row_buttons)
    
    markup.row(types.InlineKeyboardButton("📋 Показать все игры", callback_data="show_all_games"))
    
    done_callback = f"games_done_{user_id}"
    if is_editing:
        done_callback += "_edit"
    
    markup.row(types.InlineKeyboardButton("✅ Завершить выбор", callback_data=done_callback))
    
    games_text = ', '.join(selected_games[:8]) if selected_games else 'Не выбрано'
    if len(selected_games) > 8:
        games_text += f"... (+{len(selected_games) - 8})"
    
    bot.send_message(chat_id, f"Выбранные интересы: {games_text}\n\nВыберите интересы (можно несколько):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'show_all_games')
@require_subscription_callback
def show_all_games(call):
    user_id = call.from_user.id
    is_editing = '_edit' in call.data if hasattr(call, 'data') else False
    
    if user_id not in profile_data:
        profile_data[user_id] = {'games': []}
    
    selected_games = profile_data[user_id].get('games', [])
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    all_games = ALL_GAMES_WITH_CHAT
    
    for i in range(0, len(all_games), 3):
        row_games = all_games[i:i+3]
        row_buttons = []
        for game in row_games:
            if game in selected_games:
                text = f"✅ {game}"
            else:
                text = f"⬜ {game}"
            callback_data = f"game_{game}_{user_id}"
            if is_editing:
                callback_data += "_edit"
            row_buttons.append(types.InlineKeyboardButton(text, callback_data=callback_data))
        markup.row(*row_buttons)
    
    done_callback = f"games_done_{user_id}"
    if is_editing:
        done_callback += "_edit"
    
    markup.row(types.InlineKeyboardButton("✅ Завершить выбор", callback_data=done_callback))
    
    bot.edit_message_text(
        "Все игры и интересы (можно выбрать несколько):",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('game_') and not call.data.endswith('_edit'))
@require_subscription_callback
def handle_game_selection(call):
    try:
        data_parts = call.data.split('_')
        game = data_parts[1]
        user_id = int(data_parts[2])
        
        if user_id not in profile_data:
            profile_data[user_id] = {'games': []}
        
        if game in profile_data[user_id]['games']:
            profile_data[user_id]['games'].remove(game)
            selected = False
        else:
            profile_data[user_id]['games'].append(game)
            selected = True
        
        selected_games = profile_data[user_id].get('games', [])
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        games_to_show = ALL_GAMES_WITH_CHAT[:18]
        
        for i in range(0, len(games_to_show), 3):
            row_games = games_to_show[i:i+3]
            row_buttons = []
            for g in row_games:
                if g in selected_games:
                    text = f"✅ {g}"
                else:
                    text = f"⬜ {g}"
                row_buttons.append(types.InlineKeyboardButton(text, callback_data=f"game_{g}_{user_id}"))
            markup.row(*row_buttons)
        
        markup.row(types.InlineKeyboardButton("📋 Показать все игры", callback_data="show_all_games"))
        markup.row(types.InlineKeyboardButton("✅ Завершить выбор", callback_data=f"games_done_{user_id}"))
        
        games_text = ', '.join(selected_games[:8]) if selected_games else 'Не выбрано'
        if len(selected_games) > 8:
            games_text += f"... (+{len(selected_games) - 8})"
        
        bot.edit_message_text(
            f"Выбранные интересы: {games_text}\n\nВыберите интересы (можно несколько):",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        if selected:
            bot.answer_callback_query(call.id, f"✅ Добавлено: {game}")
        else:
            bot.answer_callback_query(call.id, f"❌ Убрано: {game}")
            
    except:
        bot.answer_callback_query(call.id, "Ошибка")

# ========== ИСПРАВЛЕННАЯ ФУНКЦИЯ СОХРАНЕНИЯ АНКЕТЫ ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('games_done_') and not call.data.endswith('_edit'))
@require_subscription_callback
def finish_profile(call):
    try:
        user_id = int(call.data.split('_')[2])
        
        if user_id not in profile_data:
            bot.answer_callback_query(call.id, "Ошибка! Данные не найдены")
            return
        
        data = profile_data[user_id]
        
        db = get_db_session()
        if not db:
            bot.answer_callback_query(call.id, "Ошибка подключения к БД")
            return
        
        try:
            # Проверяем, существует ли пользователь
            existing_user = db.query(User).filter(User.telegram_id == user_id).first()
            
            if existing_user:
                # Обновляем существующего
                existing_user.name = data['name']
                existing_user.username = data.get('username')
                existing_user.age = data.get('age')
                existing_user.region = data['region']
                existing_user.platform = data['platform']
                existing_user.favorite_games = data['games']
                existing_user.about = data.get('about', '')
                existing_user.is_active = True
            else:
                # Создаем нового
                new_user = User(
                    telegram_id=data['telegram_id'],
                    username=data.get('username'),
                    name=data['name'],
                    age=data.get('age'),
                    region=data['region'],
                    platform=data['platform'],
                    favorite_games=data['games'],
                    about=data.get('about', ''),
                    is_active=True,
                    photos=[],
                    search_by_interests=True,
                    likes_given_count=0,
                    likes_received_count=0,
                    matches_count=0,
                    likes_given=[],
                    likes_received=[],
                    matches=[]
                )
                db.add(new_user)
            
            db.commit()
            
            # Очищаем временные данные
            if user_id in profile_data:
                del profile_data[user_id]
            
            # Показываем успешное сообщение
            games_text = ', '.join(data['games'][:8])
            if len(data['games']) > 8:
                games_text += f"... (+{len(data['games']) - 8})"
            
            success_text = f"""✅ Анкета создана!

👤 Имя: {data['name']}
🌍 Регион: {data['region']}
🎮 Платформа: {data['platform']}
🎲 Интересы: {games_text}"""
            
            if data.get('age'):
                success_text += f"\n🎂 Возраст: {data['age']}"
            
            if data.get('about'):
                about_text = data['about'][:200]
                success_text += f"\n\n📝 О себе:\n{about_text}..."
            
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, success_text, reply_markup=get_main_keyboard())
            bot.send_message(call.message.chat.id, "📸 Вы можете добавить фото, просто отправьте его боту")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения анкеты: {e}")
            bot.answer_callback_query(call.id, f"Ошибка: {str(e)[:50]}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Ошибка обработки: {e}")
        bot.answer_callback_query(call.id, "Ошибка обработки")

# ========== ОСТАЛЬНЫЕ ФУНКЦИИ АНКЕТЫ ==========
@bot.callback_query_handler(func=lambda call: call.data == 'edit_profile_menu')
@require_subscription_callback
def edit_profile_menu(call):
    user_id = call.from_user.id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👤 Имя", callback_data="edit_name"),
        types.InlineKeyboardButton("🌍 Регион", callback_data="edit_region")
    )
    markup.add(
        types.InlineKeyboardButton("🎮 Платформа", callback_data="edit_platform"),
        types.InlineKeyboardButton("🎂 Возраст", callback_data="edit_age")
    )
    markup.add(
        types.InlineKeyboardButton("🎲 Интересы", callback_data="edit_games"),
        types.InlineKeyboardButton("📝 О себе", callback_data="edit_about")
    )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_profile"))
    
    # Удаляем старое сообщение
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    # Отправляем с оформлением
    send_formatted_message(
        call.message.chat.id,
        "🎛️ *Что хотите изменить?*\n\nВыберите пункт для редактирования:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_') and call.data not in ['edit_profile_menu'])
@require_subscription_callback
def edit_field(call):
    user_id = call.from_user.id
    field = call.data[5:]
    
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "Ошибка подключения к БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.answer_callback_query(call.id, "Ошибка! Сначала создайте анкету")
            return
        
        editing_state[user_id] = field
        
        if field == 'name':
            bot.send_message(call.message.chat.id, "Введите новое имя:")
        elif field == 'region':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for region in Config.REGIONS:
                markup.add(types.KeyboardButton(region))
            bot.send_message(call.message.chat.id, "Выберите новый регион:", reply_markup=markup)
        elif field == 'platform':
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            for platform in Config.PLATFORMS:
                markup.add(types.KeyboardButton(platform))
            bot.send_message(call.message.chat.id, "Выберите новую платформу:", reply_markup=markup)
        elif field == 'age':
            bot.send_message(call.message.chat.id, "Введите новый возраст (или 'пропустить'):")
        elif field == 'about':
            bot.send_message(call.message.chat.id, "Введите новое описание:")
        elif field == 'games':
            profile_data[user_id] = {
                'games': user.favorite_games.copy() if user.favorite_games else []
            }
            show_games_selection(call.message.chat.id, user_id, True)
        
        if field != 'games':
            bot.answer_callback_query(call.id)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

@bot.message_handler(func=lambda message: message.from_user.id in editing_state)
def process_edit(message):
    user_id = message.from_user.id
    field = editing_state.get(user_id)
    
    if not field or field == 'waiting_field':
        return
    
    db = get_db_session()
    if not db:
        bot.send_message(message.chat.id, "Ошибка подключения к БД", reply_markup=get_main_keyboard())
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            del editing_state[user_id]
            bot.send_message(message.chat.id, "Сначала создайте анкету!", reply_markup=get_main_keyboard())
            return
        
        if field == 'name':
            name = message.text.strip()
            if len(name) >= 2:
                user.name = name
                db.commit()
                bot.send_message(message.chat.id, f"✅ Имя изменено на: {name}", reply_markup=get_main_keyboard())
            else:
                bot.send_message(message.chat.id, "Имя должно быть не короче 2 символов")
                return
        
        elif field == 'region':
            region = message.text.strip()
            if region in Config.REGIONS:
                user.region = region
                db.commit()
                bot.send_message(message.chat.id, f"✅ Регион изменен на: {region}", reply_markup=get_main_keyboard())
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                for reg in Config.REGIONS:
                    markup.add(types.KeyboardButton(reg))
                bot.send_message(message.chat.id, "Выберите регион из списка:", reply_markup=markup)
                return
        
        elif field == 'platform':
            platform = message.text.strip()
            if platform in Config.PLATFORMS:
                user.platform = platform
                db.commit()
                bot.send_message(message.chat.id, f"✅ Платформа изменена на: {platform}", reply_markup=get_main_keyboard())
            else:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                for plat in Config.PLATFORMS:
                    markup.add(types.KeyboardButton(plat))
                bot.send_message(message.chat.id, "Выберите платформу из списка:", reply_markup=markup)
                return
        
        elif field == 'age':
            age_text = message.text.strip().lower()
            if age_text == 'пропустить':
                user.age = None
                db.commit()
                bot.send_message(message.chat.id, "✅ Возраст удален", reply_markup=get_main_keyboard())
            else:
                try:
                    age = int(age_text)
                    if 13 <= age <= 100:
                        user.age = age
                        db.commit()
                        bot.send_message(message.chat.id, f"✅ Возраст изменен на: {age}", reply_markup=get_main_keyboard())
                    else:
                        bot.send_message(message.chat.id, "Возраст должен быть от 13 до 100 лет")
                        return
                except ValueError:
                    bot.send_message(message.chat.id, "Введите число или 'пропустить'")
                    return
        
        elif field == 'about':
            about = message.text.strip()
            user.about = about
            db.commit()
            bot.send_message(message.chat.id, "✅ Описание обновлено", reply_markup=get_main_keyboard())
        
        del editing_state[user_id]
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(message.chat.id, f"Ошибка при сохранении", reply_markup=get_main_keyboard())
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data.endswith('_edit'))
@require_subscription_callback
def handle_edit_game_selection(call):
    try:
        data_parts = call.data.split('_')
        game = data_parts[1]
        user_id = int(data_parts[2])
        
        if user_id not in profile_data:
            profile_data[user_id] = {'games': []}
        
        if game in profile_data[user_id]['games']:
            profile_data[user_id]['games'].remove(game)
            selected = False
        else:
            profile_data[user_id]['games'].append(game)
            selected = True
        
        db = get_db_session()
        if db:
            try:
                user = db.query(User).filter(User.telegram_id == user_id).first()
                if user:
                    user.favorite_games = profile_data[user_id]['games']
                    flag_modified(user, "favorite_games")
                    db.commit()
            finally:
                db.close()
        
        bot.answer_callback_query(call.id, f"{'✅ Добавлено' if selected else '❌ Убрано'}: {game}")
        
    except:
        bot.answer_callback_query(call.id, "Ошибка")

@bot.callback_query_handler(func=lambda call: call.data.endswith('_edit') and call.data.startswith('games_done_'))
@require_subscription_callback
def finish_edit_games(call):
    try:
        user_id = int(call.data.split('_')[2])
        
        if user_id not in profile_data:
            bot.answer_callback_query(call.id, "Ошибка!")
            return
        
        data = profile_data[user_id]
        
        db = get_db_session()
        if not db:
            bot.answer_callback_query(call.id, "Ошибка БД")
            return
        
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            
            if user:
                user.favorite_games = data['games']
                flag_modified(user, "favorite_games")
                db.commit()
                
                if user_id in profile_data:
                    del profile_data[user_id]
                if user_id in editing_state:
                    del editing_state[user_id]
            
            bot.delete_message(call.message.chat.id, call.message.message_id)
            games_text = ', '.join(data['games'][:8])
            if len(data['games']) > 8:
                games_text += f"... (+{len(data['games']) - 8})"
            bot.send_message(call.message.chat.id, f"✅ Интересы обновлены: {games_text}", reply_markup=get_main_keyboard())
            
        except Exception as e:
            print(f"Ошибка: {e}")
            bot.answer_callback_query(call.id, "Ошибка сохранения")
        finally:
            db.close()
            
    except:
        bot.answer_callback_query(call.id, "Ошибка обработки")

# ========== ФОТО ==========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id
    
    if not check_subscription_sync(user_id):
        show_subscription_required(message.chat.id, user_id)
        return
    
    db = get_db_session()
    
    if not db:
        bot.send_message(message.chat.id, "Ошибка подключения к БД", reply_markup=get_main_keyboard())
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.send_message(message.chat.id, "Сначала создайте анкету!", reply_markup=get_main_keyboard())
            return
        
        file_id = message.photo[-1].file_id
        
        if user.photos is None:
            user.photos = []
        
        if len(user.photos) >= 5:
            bot.send_message(message.chat.id, "❌ Можно загрузить максимум 5 фото.", reply_markup=get_main_keyboard())
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🗑️ Управление фото", callback_data="manage_photos"))
            bot.send_message(message.chat.id, "Хотите удалить старые фото?", reply_markup=markup)
            return
        
        photos_list = list(user.photos) if user.photos else []
        photos_list.append(file_id)
        user.photos = photos_list
        flag_modified(user, "photos")
        
        db.commit()
        
        bot.reply_to(message, f"✅ Фото добавлено! У вас {len(photos_list)} фото")
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, f"Ошибка при добавлении фото")
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data == 'manage_photos')
@require_subscription_callback
def manage_photos(call):
    user_id = call.from_user.id
    db = get_db_session()
    
    if not db:
        bot.answer_callback_query(call.id, "Ошибка БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.answer_callback_query(call.id, "Сначала создайте анкету")
            return
        
        if not user.photos or len(user.photos) == 0:
            bot.answer_callback_query(call.id, "У вас нет фото")
            send_formatted_message(
                call.message.chat.id,
                "📸 *У вас нет фото*\n\nОтправьте фото для добавления.",
                reply_markup=get_main_keyboard()
            )
            return
        
        markup = types.InlineKeyboardMarkup()
        
        for i, photo_id in enumerate(user.photos):
            markup.add(types.InlineKeyboardButton(f"🗑️ Удалить фото {i+1}", callback_data=f"delete_photo_{i}"))
        
        markup.add(types.InlineKeyboardButton("❌ Удалить все фото", callback_data="delete_all_photos"))
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_profile"))
        
        # Удаляем старое сообщение
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        send_formatted_message(
            call.message.chat.id,
            f"📸 *Управление фото*\n\nУ вас {len(user.photos)} фото. Выберите действие:",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('delete_photo_'))
@require_subscription_callback
def delete_photo(call):
    user_id = call.from_user.id
    photo_index = int(call.data.split('_')[2])
    
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "Ошибка БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user or not user.photos or photo_index >= len(user.photos):
            bot.answer_callback_query(call.id, "Ошибка удаления")
            return
        
        photos_list = list(user.photos)
        photos_list.pop(photo_index)
        user.photos = photos_list
        flag_modified(user, "photos")
        
        db.commit()
        
        bot.answer_callback_query(call.id, f"Фото {photo_index+1} удалено")
        
        if photos_list:
            # Удаляем старое сообщение и обновляем список
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            # Отправляем обновленный список фото
            markup = types.InlineKeyboardMarkup()
            for i, photo_id in enumerate(photos_list):
                markup.add(types.InlineKeyboardButton(f"🗑️ Удалить фото {i+1}", callback_data=f"delete_photo_{i}"))
            
            markup.add(types.InlineKeyboardButton("❌ Удалить все фото", callback_data="delete_all_photos"))
            markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_profile"))
            
            bot.send_message(
                call.message.chat.id,
                f"Управление фото ({len(photos_list)} фото):",
                reply_markup=markup
            )
        else:
            # Удаляем старое сообщение
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            bot.send_message(
                call.message.chat.id,
                "✅ Все фото удалены",
                reply_markup=get_main_keyboard()
            )
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data == 'delete_all_photos')
@require_subscription_callback
def delete_all_photos(call):
    user_id = call.from_user.id
    
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "Ошибка БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.answer_callback_query(call.id, "Ошибка")
            return
        
        user.photos = []
        flag_modified(user, "photos")
        db.commit()
        
        bot.answer_callback_query(call.id, "Все фото удалены")
        
        # Удаляем старое сообщение и отправляем новое
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        bot.send_message(
            call.message.chat.id,
            "✅ Все фото удалены",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_profile')
@require_subscription_callback
def back_to_profile(call):
    user_id = call.from_user.id
    db = get_db_session()
    
    if not db:
        bot.answer_callback_query(call.id, "Ошибка БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.answer_callback_query(call.id, "Сначала создайте анкету")
            return
        
        profile_text = f"""📋 Ваша анкета:

👤 Имя: {user.name}
🌍 Регион: {user.region}
🎮 Платформа: {user.platform}
🎲 Интересы: {', '.join(user.favorite_games[:8]) if user.favorite_games else 'Не указаны'}"""
        
        if user.age:
            profile_text += f"\n🎂 Возраст: {user.age}"
        
        if user.about:
            about_text = user.about[:200]
            profile_text += f"\n\n📝 О себе:\n{about_text}"
        
        profile_text += f"\n\n❤️ Лайков получено: {user.likes_received_count}"
        profile_text += f"\n💌 Мэтчей: {user.matches_count}"
        profile_text += f"\n📸 Фото: {len(user.photos) if user.photos else 0}"
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ Редактировать", callback_data="edit_profile_menu"),
            types.InlineKeyboardButton("📸 Фото", callback_data="manage_photos")
        )
        markup.add(
            types.InlineKeyboardButton("⚙️ Настройки поиска", callback_data="search_settings"),
            types.InlineKeyboardButton("❌ Удалить анкету", callback_data="delete_profile")
        )
        
        # Удаляем старое сообщение и отправляем новое с анкетой
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        if user.photos and len(user.photos) > 0:
            try:
                bot.send_photo(call.message.chat.id, user.photos[0], caption=profile_text, reply_markup=markup)
            except:
                bot.send_message(call.message.chat.id, profile_text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, profile_text, reply_markup=markup)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

# ========== ЗАПУСК БОТА ==========
if __name__ == "__main__":
    print("🎮 Бот GamerMatch запущен на Railway!")
    print(f"📢 Проверка подписки на канал: {CHANNEL_ID}")
    
    # Удаляем вебхук если был
    try:
        bot.remove_webhook()
        print("✅ Старый вебхук удален")
    except:
        pass
    
    # Запускаем polling с параметром skip_pending для избежания конфликта 409
    print("🔄 Запускаем бота...")
    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=5
    )