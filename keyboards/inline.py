from telebot import types
from config import Config

def create_games_keyboard(selected_games=None):
    if selected_games is None:
        selected_games = []
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    
    for game in Config.ALL_GAMES:
        if game in selected_games:
            text = f"✅ {game}"
        else:
            text = f"☐ {game}"
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"game_{game}"))
    
    for i in range(0, len(buttons), 3):
        markup.row(*buttons[i:i+3])
    
    markup.add(types.InlineKeyboardButton("Готово", callback_data="games_done"))
    return markup

def create_genres_keyboard(selected_genres=None):
    if selected_genres is None:
        selected_genres = []
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for genre in Config.GENRES:
        if genre in selected_genres:
            text = f"✅ {genre}"
        else:
            text = f"☐ {genre}"
        buttons.append(types.InlineKeyboardButton(text, callback_data=f"genre_{genre}"))
    
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])
    
    markup.add(types.InlineKeyboardButton("Готово", callback_data="genres_done"))
    return markup

def create_ranks_keyboard(game):
    markup = types.InlineKeyboardMarkup()
    
    if game in Config.COMPETITIVE_GAMES:
        for rank in Config.COMPETITIVE_GAMES[game]:
            markup.add(types.InlineKeyboardButton(rank, callback_data=f"rank_{rank}"))
    
    markup.add(types.InlineKeyboardButton("Пропустить", callback_data="skip_rank"))
    return markup