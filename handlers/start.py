from telebot.types import ReplyKeyboardMarkup, KeyboardButton

def register_start_handlers(bot):
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        welcome_text = """🎮 Добро пожаловать в GamerMatch!

✨ Основные команды:
/profile - Создать/редактировать анкету
/search - Найти игроков
/likes - Посмотреть лайки
/matches - Ваши мэтчи
/settings - Настройки поиска

📌 Как это работает:
1. Заполните анкету (/profile)
2. Найдите интересных игроков (/search)
3. Ставьте лайки понравившимся
4. При взаимном лайке получаете контакт!"""
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("📝 Анкета"), KeyboardButton("🔍 Поиск"))
        markup.add(KeyboardButton("❤️ Лайки"), KeyboardButton("💌 Мэтчи"))
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            parse_mode='Markdown',
            reply_markup=markup
        )