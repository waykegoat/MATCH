from telebot.handler_backends import State, StatesGroup

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

class SearchStates(StatesGroup):
    filters = State()