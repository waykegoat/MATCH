def validate_age(age_text):
    if not age_text:
        return None
    
    try:
        age = int(age_text)
        if 13 <= age <= 100:
            return age
    except:
        pass
    return None

def validate_username(username):
    if not username:
        return False
    
    if username.startswith('@'):
        username = username[1:]
    
    if len(username) < 5 or len(username) > 32:
        return False
    
    allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_')
    return all(c in allowed for c in username)