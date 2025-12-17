from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("📝 Анкета"), KeyboardButton("🔍 Поиск"))
    markup.add(KeyboardButton("❤️ Лайки"), KeyboardButton("💌 Мэтчи"))
    markup.add(KeyboardButton("⚙️ Настройки"))
    return markup

def skip_button():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("Пропустить"))
    return markup

def regions_keyboard():
    from config import Config
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for region in Config.REGIONS:
        markup.add(KeyboardButton(region))
    return markup

def platforms_keyboard():
    from config import Config
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for platform in Config.PLATFORMS:
        markup.add(KeyboardButton(platform))
    return markup