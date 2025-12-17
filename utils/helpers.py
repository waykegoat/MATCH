def format_profile_text(user):
    text = f"👤 *{user.name}*\n"
    
    if user.age:
        text += f"🎂 Возраст: {user.age}\n"
    
    text += f"🌍 Регион: {user.region}\n"
    text += f"🎮 Платформа: {user.platform}\n"
    
    if user.favorite_games:
        text += f"🎲 Игры: {', '.join(user.favorite_games[:5])}\n"
    
    if user.genres:
        text += f"📁 Жанры: {', '.join(user.genres[:5])}\n"
    
    if user.competitive_ranks:
        text += "\n🏆 Ранги:\n"
        for game, rank in user.competitive_ranks.items():
            text += f"  • {game}: {rank}\n"
    
    if user.about:
        text += f"\n📝 О себе:\n{user.about}\n"
    
    return text

def calculate_age_range(user_age, range_years=5):
    if not user_age:
        return None, None
    
    min_age = max(18, user_age - range_years)
    max_age = user_age + range_years
    return min_age, max_age