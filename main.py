import telebot
from telebot import types
from telebot.storage import StateMemoryStorage
from config import Config
from database.db import init_db, get_db, SessionLocal
from database.models import User
from sqlalchemy.orm.attributes import flag_modified
import random
from datetime import datetime, timedelta
from collections import Counter

# ========== ФУНКЦИИ ОФОРМЛЕНИЯ ==========

def send_formatted_message(chat_id, text, reply_markup=None, parse_mode='Markdown'):
    """
    Отправляет сообщение с оформлением (фото бота + текст)
    """
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
    """
    Редактирует сообщение с оформлением
    """
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

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(Config.BOT_TOKEN, state_storage=state_storage)

init_db()

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

def get_db_session():
    try:
        db = SessionLocal()
        return db
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        try:
            from database.db import engine
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db = SessionLocal()
            return db
        except:
            return None

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if not check_subscription_sync(user_id):
        show_subscription_required(message.chat.id, user_id)
        return
    
    # УБЕРИТЕ "🎮 Добро пожаловать в GamerMatch!" из текста
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

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def send_help(message):
    user_id = message.from_user.id
    
    if not check_subscription_sync(user_id):
        show_subscription_required(message.chat.id, user_id)
        return
    
    help_text = """🎮 *GamerMatch - бот для знакомств геймеров*

📋 *Основные функции:*
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
    
    send_formatted_message(message.chat.id, help_text, reply_markup=get_main_keyboard())

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
        
        profile_text += f"\n\n❤️ Лайков получено: {len(user.likes_received) if user.likes_received else 0}"
        profile_text += f"\n💌 Мэтчей: {len(user.matches) if user.matches else 0}"
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('games_done_') and not call.data.endswith('_edit'))
@require_subscription_callback
def finish_profile(call):
    try:
        user_id = int(call.data.split('_')[2])
        
        if user_id not in profile_data:
            bot.answer_callback_query(call.id, "Ошибка!")
            return
        
        data = profile_data[user_id]
        
        if not data.get('games'):
            bot.answer_callback_query(call.id, "Выберите хотя бы один интерес!")
            return
        
        db = get_db_session()
        if not db:
            bot.answer_callback_query(call.id, "Ошибка БД")
            return
        
        try:
            existing_user = db.query(User).filter(User.telegram_id == user_id).first()
            if existing_user:
                existing_user.name = data['name']
                existing_user.username = data.get('username')
                existing_user.age = data.get('age')
                existing_user.region = data['region']
                existing_user.platform = data['platform']
                existing_user.favorite_games = data['games']
                existing_user.about = data.get('about', '')
                existing_user.is_active = True
            else:
                user = User(
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
                    search_by_interests=True
                )
                db.add(user)
            
            db.commit()
            
            if user_id in profile_data:
                del profile_data[user_id]
            
            games_text = ', '.join(data['games'][:8])
            if len(data['games']) > 8:
                games_text += f"... (+{len(data['games']) - 8})"
            
            profile_text = f"""✅ Анкета создана!

👤 Имя: {data['name']}
🌍 Регион: {data['region']}
🎮 Платформа: {data['platform']}
🎲 Интересы: {games_text}"""
            
            if data.get('age'):
                profile_text += f"\n🎂 Возраст: {data['age']}"
            
            if data.get('about'):
                about_text = data['about'][:200]
                profile_text += f"\n\n📝 О себе:\n{about_text}..."
            
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, profile_text, reply_markup=get_main_keyboard())
            bot.send_message(call.message.chat.id, "📸 Вы можете добавить фото, просто отправьте его боту")
            
        except Exception as e:
            print(f"Ошибка: {e}")
            bot.answer_callback_query(call.id, "Ошибка сохранения")
        finally:
            db.close()
            
    except:
        bot.answer_callback_query(call.id, "Ошибка обработки")

# ВАЖНО: ИСПРАВЛЕННЫЙ КОД НИЖЕ
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

# ВАЖНО: ИСПРАВЛЕННЫЙ КОД НИЖЕ
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
        
        profile_text += f"\n\n❤️ Лайков получено: {len(user.likes_received) if user.likes_received else 0}"
        profile_text += f"\n💌 Мэтчей: {len(user.matches) if user.matches else 0}"
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

@bot.message_handler(commands=['search'])
@bot.message_handler(func=lambda message: message.text == "🔍 Искать игроков")
def search_profiles(message):
    user_id = message.from_user.id
    
    if not check_subscription_sync(user_id):
        show_subscription_required(message.chat.id, user_id)
        return
    
    db = get_db_session()
    
    if not db:
        bot.send_message(message.chat.id, "Ошибка подключения к базе данных.", reply_markup=get_main_keyboard())
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.send_message(message.chat.id, "Сначала создайте анкету!", reply_markup=get_main_keyboard())
            return
        
        if not hasattr(user, 'search_by_interests'):
            user.search_by_interests = True
        
        other_users = db.query(User).filter(
            User.telegram_id != user_id,
            User.is_active == True
        ).all()
        
        if not other_users:
            bot.send_message(message.chat.id, "😔 Пока нет других анкет для просмотра", reply_markup=get_main_keyboard())
            return
        
        if hasattr(user, 'search_by_interests') and user.search_by_interests and user.favorite_games:
            filtered_users = []
            for other_user in other_users:
                if other_user.favorite_games:
                    common_interests = set(user.favorite_games) & set(other_user.favorite_games)
                    if common_interests:
                        filtered_users.append(other_user)
            
            if len(filtered_users) < 5:
                for other_user in other_users:
                    if other_user not in filtered_users:
                        filtered_users.append(other_user)
                        if len(filtered_users) >= 10:
                            break
        else:
            filtered_users = other_users[:10]
        
        user_likes_given = user.likes_given or []
        filtered_users = [u for u in filtered_users if u.telegram_id not in user_likes_given]
        
        if not filtered_users:
            bot.send_message(message.chat.id, "Вы уже просмотрели все доступные анкеты!", reply_markup=get_main_keyboard())
            return
        
        random.shuffle(filtered_users)
        show_profile_search(message.chat.id, filtered_users[0], 0, len(filtered_users), user_id)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(message.chat.id, "Ошибка при поиске", reply_markup=get_main_keyboard())
    finally:
        db.close()

def show_profile_search(chat_id, profile_user, index, total, viewer_id):
    try:
        text = f"""👤 {profile_user.name}
🌍 Регион: {profile_user.region}
🎮 Платформа: {profile_user.platform}
🎲 Интересы: {', '.join(profile_user.favorite_games[:5]) if profile_user.favorite_games else 'Не указаны'}"""
        
        if profile_user.age:
            text += f"\n🎂 Возраст: {profile_user.age}"
        
        if profile_user.about:
            about_text = profile_user.about[:150]
            text += f"\n\n📝 О себе:\n{about_text}"
        
        text += f"\n\nАнкета {index+1}/{total}"
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("❤️ Лайк", callback_data=f"like_{profile_user.telegram_id}_{index}_{total}"),
            types.InlineKeyboardButton("👎 Пропустить", callback_data=f"skip_{index}_{total}")
        )
        
        if profile_user.photos and len(profile_user.photos) > 0:
            try:
                bot.send_photo(chat_id, profile_user.photos[0], caption=text, reply_markup=markup)
            except:
                bot.send_message(chat_id, text, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.send_message(chat_id, "Ошибка при показе анкеты", reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('like_'))
@require_subscription_callback
def handle_like(call):
    try:
        data = call.data.split('_')
        target_id = int(data[1])
        index = int(data[2])
        total = int(data[3])
        
        user_id = call.from_user.id
        
        db = get_db_session()
        if not db:
            bot.answer_callback_query(call.id, "Ошибка БД")
            return
        
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            target_user = db.query(User).filter(User.telegram_id == target_id).first()
            
            if not user or not target_user:
                bot.answer_callback_query(call.id, "Ошибка!")
                return
            
            if user.likes_given is None:
                user.likes_given = []
            if target_user.likes_received is None:
                target_user.likes_received = []
            
            if target_id not in user.likes_given:
                user.likes_given.append(target_id)
                flag_modified(user, "likes_given")
            
            if user_id not in target_user.likes_received:
                target_user.likes_received.append(user_id)
                flag_modified(target_user, "likes_received")
            
            if user.matches is None:
                user.matches = []
            if target_user.matches is None:
                target_user.matches = []
            
            target_likes_given = target_user.likes_given or []
            
            if user_id in target_likes_given:
                if target_id not in user.matches:
                    user.matches.append(target_id)
                    flag_modified(user, "matches")
                
                if user_id not in target_user.matches:
                    target_user.matches.append(user_id)
                    flag_modified(target_user, "matches")
                
                db.commit()
                bot.answer_callback_query(call.id, "🎉 Мэтч! Вы понравились друг другу!")
                
                if target_user.username:
                    bot.send_message(call.message.chat.id, f"🎉 Мэтч с {target_user.name}!\nНапишите: @{target_user.username}", reply_markup=get_main_keyboard())
                
                if user.username:
                    bot.send_message(target_user.telegram_id, f"🎉 Мэтч! {user.name} тоже лайкнул вас!\nНапишите: @{user.username}", reply_markup=get_main_keyboard())
            else:
                db.commit()
                bot.answer_callback_query(call.id, "❤️ Лайк отправлен!")
            
            bot.delete_message(call.message.chat.id, call.message.message_id)
            
            db = get_db_session()
            if db:
                try:
                    user = db.query(User).filter(User.telegram_id == user_id).first()
                    if user:
                        other_users = db.query(User).filter(
                            User.telegram_id != user_id,
                            User.is_active == True
                        ).all()
                        
                        user_likes_given = user.likes_given or []
                        filtered_users = [u for u in other_users if u.telegram_id not in user_likes_given]
                        
                        if filtered_users and index < total - 1:
                            next_index = min(index + 1, len(filtered_users) - 1)
                            show_profile_search(call.message.chat.id, filtered_users[next_index], next_index, len(filtered_users), user_id)
                        else:
                            bot.send_message(call.message.chat.id, "Вы просмотрели все доступные анкеты!", reply_markup=get_main_keyboard())
                finally:
                    db.close()
                        
        except Exception as e:
            print(f"Ошибка: {e}")
            bot.answer_callback_query(call.id, "Ошибка")
        finally:
            if db:
                db.close()
                
    except:
        bot.answer_callback_query(call.id, "Ошибка обработки")

@bot.callback_query_handler(func=lambda call: call.data.startswith('skip_'))
@require_subscription_callback
def handle_skip(call):
    try:
        data = call.data.split('_')
        index = int(data[1])
        total = int(data[2])
        
        user_id = call.from_user.id
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        db = get_db_session()
        if not db:
            bot.send_message(call.message.chat.id, "Ошибка БД", reply_markup=get_main_keyboard())
            return
        
        try:
            user = db.query(User).filter(User.telegram_id == user_id).first()
            
            other_users = db.query(User).filter(
                User.telegram_id != user_id,
                User.is_active == True
            ).all()
            
            user_likes_given = user.likes_given or []
            filtered_users = [u for u in other_users if u.telegram_id not in user_likes_given]
            
            if filtered_users and index < total - 1:
                next_index = min(index + 1, len(filtered_users) - 1)
                show_profile_search(call.message.chat.id, filtered_users[next_index], next_index, len(filtered_users), user_id)
            else:
                bot.send_message(call.message.chat.id, "Вы просмотрели все доступные анкеты!", reply_markup=get_main_keyboard())
                
        except Exception as e:
            print(f"Ошибка: {e}")
            bot.send_message(call.message.chat.id, "Ошибка", reply_markup=get_main_keyboard())
        finally:
            db.close()
            
    except Exception as e:
        print(f"Ошибка обработки skip: {e}")
        bot.send_message(call.message.chat.id, "Ошибка обработки", reply_markup=get_main_keyboard())

@bot.message_handler(commands=['likes'])
@bot.message_handler(func=lambda message: message.text == "❤️ Мои лайки")
def show_likes(message):
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
            send_formatted_message(
                message.chat.id,
                "❌ *Сначала создайте анкету!*\n\nНажмите '📝 Моя анкета' для создания.",
                reply_markup=get_main_keyboard()
            )
            return
        
        likes_received = user.likes_received or []
        
        if not likes_received:
            send_formatted_message(
                message.chat.id,
                "😔 *У вас пока нет лайков*\n\nБудьте активнее, заполните анкету и ищите других игроков!",
                reply_markup=get_main_keyboard()
            )
            return
        
        users_who_liked = db.query(User).filter(User.telegram_id.in_(likes_received[:20])).all()
        
        text = f"""❤️ *Вас лайкнули ({len(users_who_liked)})*

"""
        for i, liked_user in enumerate(users_who_liked[:10], 1):
            text += f"{i}. {liked_user.name} (@{liked_user.username or 'нет username'})\n"
        
        if len(users_who_liked) > 10:
            text += f"\n... и еще {len(users_who_liked) - 10}"
        
        markup = types.InlineKeyboardMarkup()
        if users_who_liked:
            markup.add(types.InlineKeyboardButton("🔍 Посмотреть их анкеты", callback_data="view_likers"))
        
        send_formatted_message(message.chat.id, text, reply_markup=markup)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        send_formatted_message(
            message.chat.id,
            "❌ *Ошибка при загрузке лайков*\n\nПопробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data == 'view_likers')
@require_subscription_callback
def view_likers(call):
    user_id = call.from_user.id
    db = get_db_session()
    
    if not db:
        bot.answer_callback_query(call.id, "Ошибка БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.answer_callback_query(call.id, "Ошибка!")
            return
        
        likes_received = user.likes_received or []
        users_who_liked = db.query(User).filter(User.telegram_id.in_(likes_received[:20])).all()
        
        if users_who_liked:
            show_profile_search(call.message.chat.id, users_who_liked[0], 0, len(users_who_liked), user_id)
        else:
            bot.answer_callback_query(call.id, "Нет лайков для просмотра")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

@bot.message_handler(commands=['matches'])
@bot.message_handler(func=lambda message: message.text == "💌 Мэтчи")
def show_matches(message):
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
            send_formatted_message(
                message.chat.id,
                "❌ *Сначала создайте анкету!*\n\nНажмите '📝 Моя анкета' для создания.",
                reply_markup=get_main_keyboard()
            )
            return
        
        matches = user.matches or []
        
        if not matches:
            send_formatted_message(
                message.chat.id,
                "😔 *У вас пока нет мэтчей*\n\nСтавьте лайки понравившимся игрокам! При взаимном лайке вы получите контакт.",
                reply_markup=get_main_keyboard()
            )
            return
        
        matched_users = db.query(User).filter(User.telegram_id.in_(matches[:20])).all()
        
        text = f"""💌 *Ваши мэтчи ({len(matched_users)})*

"""
        for i, match_user in enumerate(matched_users[:5], 1):
            username = match_user.username or 'нет username'
            text += f"{i}. *{match_user.name}* (@{username})\n"
            text += f"   🎮 {match_user.platform} | {', '.join(match_user.favorite_games[:2]) if match_user.favorite_games else 'Общение'}\n\n"
        
        if len(matched_users) > 5:
            text += f"... и еще {len(matched_users) - 5}"
        
        send_formatted_message(message.chat.id, text, reply_markup=get_main_keyboard())
        
    except Exception as e:
        print(f"Ошибка: {e}")
        send_formatted_message(
            message.chat.id,
            "❌ *Ошибка при загрузке мэтчей*\n\nПопробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    finally:
        db.close()

@bot.message_handler(commands=['settings'])
@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки")
@bot.callback_query_handler(func=lambda call: call.data == 'search_settings')
def show_settings(message):
    if hasattr(message, 'data'):
        chat_id = message.message.chat.id
        message_id = message.message.message_id
        user_id = message.from_user.id
        is_callback = True
    else:
        chat_id = message.chat.id
        message_id = None
        user_id = message.from_user.id
        is_callback = False
    
    if not check_subscription_sync(user_id):
        show_subscription_required(chat_id, user_id)
        if is_callback:
            bot.answer_callback_query(message.id, "❌ Сначала подпишитесь на канал!")
        return
    
    db = get_db_session()
    
    if not db:
        if is_callback:
            bot.answer_callback_query(message.id, "Ошибка БД")
        else:
            bot.send_message(chat_id, "Ошибка подключения к БД", reply_markup=get_main_keyboard())
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            if is_callback:
                bot.answer_callback_query(message.id, "Сначала создайте анкету!")
            else:
                bot.send_message(chat_id, "Сначала создайте анкету!", reply_markup=get_main_keyboard())
            return
        
        if not hasattr(user, 'search_by_interests') or user.search_by_interests is None:
            user.search_by_interests = True
        
        text = """⚙️ *Настройки поиска*

🔍 *Поиск активен:* {active}
🎯 *Поиск по интересам:* {interests}

{search_info}

*Используйте кнопки ниже для настройки:*""".format(
            active='✅ Да' if user.is_active else '❌ Нет',
            interests='✅ Включен' if user.search_by_interests else '❌ Выключен',
            search_info='🔍 Бот ищет людей с общими интересами' if user.search_by_interests else '🔍 Бот показывает случайные анкеты'
        )
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        if user.is_active:
            markup.add(types.InlineKeyboardButton("⏸️ Скрыть анкету", callback_data="hide_profile"))
        else:
            markup.add(types.InlineKeyboardButton("▶️ Показать анкету", callback_data="show_profile"))
        
        if user.search_by_interests:
            markup.add(types.InlineKeyboardButton("🎯 Случайный поиск", callback_data="random_search"))
        else:
            markup.add(types.InlineKeyboardButton("🎯 Поиск по интересам", callback_data="interest_search"))
        
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_profile"))
        
        if is_callback and message_id:
            try:
                edit_formatted_message(chat_id, message_id, text, reply_markup=markup)
            except:
                # Если не получается отредактировать, отправляем новое
                send_formatted_message(chat_id, text, reply_markup=markup)
        else:
            send_formatted_message(chat_id, text, reply_markup=markup)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        if is_callback:
            bot.answer_callback_query(message.id, "Ошибка")
        else:
            bot.send_message(chat_id, "Ошибка при загрузке настроек", reply_markup=get_main_keyboard())
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data in ['hide_profile', 'show_profile', 'random_search', 'interest_search'])
@require_subscription_callback
def toggle_settings(call):
    user_id = call.from_user.id
    db = get_db_session()
    
    if not db:
        bot.answer_callback_query(call.id, "Ошибка БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if not user:
            bot.answer_callback_query(call.id, "Ошибка!")
            return
        
        if call.data == 'hide_profile':
            user.is_active = False
            text = "✅ Ваша анкета скрыта от других пользователей"
        elif call.data == 'show_profile':
            user.is_active = True
            text = "✅ Ваша анкета теперь видна другим пользователям"
        elif call.data == 'random_search':
            user.search_by_interests = False
            text = "✅ Включен случайный поиск"
        elif call.data == 'interest_search':
            user.search_by_interests = True
            text = "✅ Включен поиск по интересам"
        
        db.commit()
        
        bot.answer_callback_query(call.id, text)
        show_settings(call)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

@bot.callback_query_handler(func=lambda call: call.data == 'delete_profile')
@require_subscription_callback
def delete_profile(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_delete"),
        types.InlineKeyboardButton("❌ Нет, отмена", callback_data="back_to_profile")
    )
    
    try:
        bot.edit_message_text(
            "❌ Вы уверены, что хотите удалить анкету?\nЭто действие нельзя отменить!",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    except:
        bot.send_message(
            call.message.chat.id,
            "❌ Вы уверены, что хотите удалить анкету?\nЭто действие нельзя отменить!",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == 'confirm_delete')
@require_subscription_callback
def confirm_delete(call):
    user_id = call.from_user.id
    
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "Ошибка БД")
        return
    
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        
        if user:
            db.delete(user)
            db.commit()
        
        try:
            bot.edit_message_text(
                "❌ Ваша анкета удалена",
                call.message.chat.id,
                call.message.message_id
            )
        except:
            pass
        
        bot.send_message(call.message.chat.id, "Анкета удалена. Вы можете создать новую в любое время!", reply_markup=get_main_keyboard())
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "Ошибка")
    finally:
        db.close()

# АДМИН-ПАНЕЛЬ
@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = message.from_user.id
    
    if user_id in admin_sessions and admin_sessions[user_id]:
        show_admin_menu(message.chat.id)
        return
    
    bot.send_message(message.chat.id, 
                    "🔒 Введите админ-токен для доступа к панели управления:",
                    reply_markup=types.ReplyKeyboardRemove())
    
    bot.register_next_step_handler(message, check_admin_token)

def check_admin_token(message):
    user_id = message.from_user.id
    entered_token = message.text.strip()
    
    if entered_token == Config.ADMIN_TOKEN:
        admin_sessions[user_id] = True
        send_formatted_message(message.chat.id, "✅ *Доступ разрешен!*\n\nДобро пожаловать в админ-панель.")
        show_admin_menu(message.chat.id)
    else:
        admin_sessions[user_id] = False
        send_formatted_message(
            message.chat.id, 
            "❌ *Неверный токен!*\n\nДоступ запрещен.",
            reply_markup=get_main_keyboard()
        )

def show_admin_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    buttons = [
        types.InlineKeyboardButton("📊 Общая статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("👥 Просмотр анкет", callback_data="admin_view_profiles"),
        types.InlineKeyboardButton("🔄 Лайв-стата", callback_data="admin_live_stats"),
        types.InlineKeyboardButton("❌ Выйти из админки", callback_data="admin_logout")
    ]
    
    markup.add(buttons[0], buttons[1])
    markup.add(buttons[2])
    markup.add(buttons[3])
    
    send_formatted_message(
        chat_id, 
        "🛠️ *Админ-панель*\n\nВыберите действие:",
        reply_markup=markup
    )
    
    bot.send_message(chat_id, 
                    "🛠️ *Админ-панель*\nВыберите действие:",
                    parse_mode='Markdown',
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callback(call):
    user_id = call.from_user.id
    
    if user_id not in admin_sessions or not admin_sessions[user_id]:
        bot.answer_callback_query(call.id, "❌ Сессия истекла! Войдите снова.")
        return
    
    action = call.data
    
    if action == 'admin_stats':
        show_general_stats(call)
    elif action == 'admin_view_profiles':
        show_profiles_list(call, page=0)
    elif action == 'admin_live_stats':
        show_live_stats(call)
    elif action == 'admin_logout':
        admin_logout(call)
    elif action == 'admin_back_menu':
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_admin_menu(call.message.chat.id)
    elif action.startswith('admin_profile_'):
        profile_id = int(call.data.split('_')[2])
        show_admin_profile(call, profile_id)
    elif action.startswith('admin_page_'):
        page = int(call.data.split('_')[2])
        show_profiles_list(call, page)
    elif action.startswith('admin_toggle_'):
        profile_id = int(call.data.split('_')[2])
        toggle_profile_active(call, profile_id)
    elif action.startswith('admin_delete_'):
        profile_id = int(call.data.split('_')[2])
        confirm_delete_profile(call, profile_id)
    elif action == 'admin_confirm_delete':
        profile_id = admin_delete_data.get(call.from_user.id, {}).get('profile_id')
        if profile_id:
            delete_profile_by_admin(call, profile_id)
    elif action == 'admin_cancel_delete':
        user_id = call.from_user.id
        if user_id in admin_delete_data:
            del admin_delete_data[user_id]
        bot.answer_callback_query(call.id, "❌ Удаление отменено")
        show_profiles_list(call, page=0)

def get_db_stats():
    db = get_db_session()
    if not db:
        return None
    
    try:
        from database.models import User
        
        total_users = db.query(User).count()
        active_profiles = db.query(User).filter(User.is_active == True).count()
        
        total_likes = 0
        total_matches = 0
        
        all_users = db.query(User).all()
        for user in all_users:
            if user.likes_given:
                total_likes += len(user.likes_given)
            
            if user.matches:
                total_matches += len(user.matches)
        
        from collections import Counter
        game_counter = Counter()
        
        for user in all_users:
            if user.favorite_games:
                for game in user.favorite_games:
                    game_counter[game] += 1
        
        top_games = game_counter.most_common(5)
        
        return {
            'total_users': total_users,
            'active_profiles': active_profiles,
            'total_likes': total_likes,
            'total_matches': total_matches // 2,
            'top_games': top_games
        }
        
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        return None
    finally:
        db.close()

def show_general_stats(call):
    stats = get_db_stats()
    
    if not stats:
        bot.answer_callback_query(call.id, "❌ Ошибка получения статистики")
        return
    
    text = f"""📊 *Общая статистика бота*

👥 *Пользователи:*
├ Всего пользователей: {stats['total_users']}
└ Активных анкет: {stats['active_profiles']}

❤️ *Лайки и мэтчи:*
├ Всего лайков: {stats['total_likes']}
└ Всего мэтчей: {stats['total_matches']}

🎮 *Топ-5 игр/интересов:*
"""
    
    for i, (game, count) in enumerate(stats['top_games'], 1):
        text += f"{i}. {game}: {count} чел.\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup
    )

profiles_per_page = 10

def show_profiles_list(call, page=0):
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "❌ Ошибка БД")
        return
    
    try:
        total_profiles = db.query(User).count()
        total_pages = (total_profiles + profiles_per_page - 1) // profiles_per_page
        
        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0
        
        offset = page * profiles_per_page
        profiles = db.query(User).order_by(User.created_at.desc()).offset(offset).limit(profiles_per_page).all()
        
        text = f"👥 *Просмотр анкет*\nСтраница {page+1}/{max(total_pages, 1)}\n\n"
        
        for i, profile in enumerate(profiles, offset + 1):
            status = "✅" if profile.is_active else "⏸️"
            games_preview = ', '.join(profile.favorite_games[:2]) if profile.favorite_games else 'Нет'
            if profile.favorite_games and len(profile.favorite_games) > 2:
                games_preview += f"... (+{len(profile.favorite_games)-2})"
            
            text += f"{i}. {status} {profile.name} (@{profile.username or 'нет'})\n"
            text += f"   🎮 {games_preview}\n"
            text += f"   📅 {profile.created_at.strftime('%d.%m.%Y')}\n\n"
        
        markup = types.InlineKeyboardMarkup(row_width=3)
        
        for profile in profiles:
            status_icon = "👁️" if profile.is_active else "👁️‍🗨️"
            markup.add(
                types.InlineKeyboardButton(
                    f"{status_icon} {profile.name[:15]}",
                    callback_data=f"admin_profile_{profile.telegram_id}"
                )
            )
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_page_{page-1}"))
        
        nav_buttons.append(types.InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"admin_page_{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
        
        markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="admin_back_menu"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки")
    finally:
        db.close()

def show_admin_profile(call, profile_id):
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "❌ Ошибка БД")
        return
    
    try:
        profile = db.query(User).filter(User.telegram_id == profile_id).first()
        
        if not profile:
            bot.answer_callback_query(call.id, "❌ Анкета не найдена")
            return
        
        status = "✅ Активна" if profile.is_active else "⏸️ Скрыта"
        
        text = f"""📋 *Анкета пользователя*

👤 *Имя:* {profile.name}
🔗 *Username:* @{profile.username or 'нет'}
🆔 *ID:* {profile.telegram_id}
🌍 *Регион:* {profile.region}
🎮 *Платформа:* {profile.platform}
📅 *Создана:* {profile.created_at.strftime('%d.%m.%Y %H:%M')}
📊 *Статус:* {status}

🎲 *Интересы:*
{', '.join(profile.favorite_games) if profile.favorite_games else 'Не указаны'}

📝 *О себе:*
{profile.about or 'Не указано'}

❤️ *Лайков отправлено:* {len(profile.likes_given) if profile.likes_given else 0}
💌 *Лайков получено:* {len(profile.likes_received) if profile.likes_received else 0}
🤝 *Мэтчей:* {len(profile.matches) if profile.matches else 0}
📸 *Фото:* {len(profile.photos) if profile.photos else 0}"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        if profile.is_active:
            markup.add(types.InlineKeyboardButton("⏸️ Скрыть анкету", callback_data=f"admin_toggle_{profile_id}"))
        else:
            markup.add(types.InlineKeyboardButton("▶️ Показать анкету", callback_data=f"admin_toggle_{profile_id}"))
        
        markup.add(types.InlineKeyboardButton("🗑️ Удалить анкету", callback_data=f"admin_delete_{profile_id}"))
        markup.add(types.InlineKeyboardButton("⬅️ Назад к списку", callback_data="admin_view_profiles"))
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка")
    finally:
        db.close()

def toggle_profile_active(call, profile_id):
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "❌ Ошибка БД")
        return
    
    try:
        profile = db.query(User).filter(User.telegram_id == profile_id).first()
        
        if not profile:
            bot.answer_callback_query(call.id, "❌ Анкета не найдена")
            return
        
        profile.is_active = not profile.is_active
        db.commit()
        
        action = "скрыта" if not profile.is_active else "активирована"
        bot.answer_callback_query(call.id, f"✅ Анкета {action}")
        
        show_admin_profile(call, profile_id)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка")
    finally:
        db.close()

def confirm_delete_profile(call, profile_id):
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "❌ Ошибка БД")
        return
    
    try:
        profile = db.query(User).filter(User.telegram_id == profile_id).first()
        
        if not profile:
            bot.answer_callback_query(call.id, "❌ Анкета не найдена")
            return
        
        admin_delete_data[call.from_user.id] = {
            'profile_id': profile_id,
            'profile_name': profile.name
        }
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Да, удалить", callback_data="admin_confirm_delete"),
            types.InlineKeyboardButton("❌ Нет, отмена", callback_data="admin_cancel_delete")
        )
        
        bot.edit_message_text(
            f"❌ *Подтверждение удаления*\n\nВы уверены, что хотите удалить анкету пользователя *{profile.name}*?",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка")
    finally:
        db.close()

def delete_profile_by_admin(call, profile_id):
    db = get_db_session()
    if not db:
        bot.answer_callback_query(call.id, "❌ Ошибка БД")
        return
    
    try:
        profile = db.query(User).filter(User.telegram_id == profile_id).first()
        
        if profile:
            db.delete(profile)
            db.commit()
        
        user_id = call.from_user.id
        if user_id in admin_delete_data:
            del admin_delete_data[user_id]
        
        bot.answer_callback_query(call.id, "✅ Анкета удалена")
        show_profiles_list(call, page=0)
        
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка удаления")
    finally:
        db.close()

def get_live_stats_data():
    db = get_db_session()
    if not db:
        return None
    
    try:
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day)
        week_ago = today_start - timedelta(days=7)
        
        all_users = db.query(User).all()
        
        today_new = 0
        week_new = 0
        
        for user in all_users:
            if user.created_at and user.created_at >= today_start:
                today_new += 1
            
            if user.created_at and user.created_at >= week_ago:
                week_new += 1
        
        total_likes_week = 0
        total_matches_week = 0
        
        for user in all_users:
            if user.likes_given:
                total_likes_week += len(user.likes_given)
            
            if user.matches:
                total_matches_week += len(user.matches)
        
        conversion_rate = 0
        if total_likes_week > 0:
            conversion_rate = round((total_matches_week / 2 / total_likes_week) * 100, 1)
        
        return {
            'today_new': today_new,
            'week_new': week_new,
            'total_likes': total_likes_week,
            'total_matches': total_matches_week // 2,
            'conversion_rate': conversion_rate
        }
        
    except Exception as e:
        print(f"Ошибка получения live-статистики: {e}")
        return None
    finally:
        db.close()

def show_live_stats(call):
    stats = get_live_stats_data()
    
    if not stats:
        bot.answer_callback_query(call.id, "❌ Ошибка получения статистики")
        return
    
    text = f"""🔄 *Лайв-статистика*

📈 *За сегодня:*
├ Новые анкеты: {stats['today_new']}

📊 *За неделю:*
├ Новые анкеты: {stats['week_new']}
├ Всего лайков: {stats['total_likes']}
└ Всего мэтчей: {stats['total_matches']}

📊 *Конверсия в мэтчи:* {stats['conversion_rate']}%"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="admin_live_stats"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu"))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup
    )

def admin_logout(call):
    user_id = call.from_user.id
    
    if user_id in admin_sessions:
        del admin_sessions[user_id]
    
    if user_id in admin_delete_data:
        del admin_delete_data[user_id]
    
    bot.answer_callback_query(call.id, "✅ Вы вышли из админ-панели")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Админ-сессия завершена.", reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    if message.text.lower() in ["привет", "hi", "hello"]:
        bot.send_message(message.chat.id, f"Привет, {message.from_user.first_name}! 🎮\nИспользуй кнопки ниже для навигации!", reply_markup=get_main_keyboard())
    else:
        bot.send_message(message.chat.id, "Используй кнопки для навигации! 🎮", reply_markup=get_main_keyboard())

if __name__ == '__main__':
    print("🎮 Бот GamerMatch запущен!")
    print(f"📢 Проверка подписки на канал: {CHANNEL_ID}")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import time
        time.sleep(5)
        print("Перезапуск бота...")
        bot.infinity_polling()