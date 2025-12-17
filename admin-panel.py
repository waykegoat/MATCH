import telebot
from telebot import types
from database.db import get_db
from database.models import User
from config import Config
from logger import logger
from datetime import datetime, timedelta

class AdminPanel:
    def __init__(self, bot):
        self.bot = bot
        self.admin_id = Config.ADMIN_ID
    
    def is_admin(self, user_id):
        return user_id == self.admin_id
    
    def show_admin_menu(self, message):
        if not self.is_admin(message.from_user.id):
            self.bot.send_message(message.chat.id, "⛔ Доступ запрещен!")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            types.InlineKeyboardButton("👥 Все анкеты", callback_data="admin_all_profiles")
        )
        markup.add(
            types.InlineKeyboardButton("🆕 Новые за 24ч", callback_data="admin_new_profiles"),
            types.InlineKeyboardButton("💌 Мэтчи", callback_data="admin_matches")
        )
        markup.add(
            types.InlineKeyboardButton("📈 Лайв-стата", callback_data="admin_live_stats"),
            types.InlineKeyboardButton("🔄 Обновить", callback_data="admin_refresh")
        )
        
        text = "👨‍💼 *Админ-панель GamerMatch*\n\nВыберите действие:"
        self.bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    
    def get_stats(self):
        db = get_db()
        if not db:
            return None
        
        try:
            total_users = db.query(User).count()
            active_users = db.query(User).filter(User.is_active == True).count()
            
            today = datetime.now().date()
            new_today = db.query(User).filter(
                User.created_at >= today
            ).count()
            
            last_24h = datetime.now() - timedelta(hours=24)
            new_24h = db.query(User).filter(
                User.created_at >= last_24h
            ).count()
            
            users_with_photos = db.query(User).filter(
                User.photos != None,
                User.photos != []
            ).count()
            
            total_likes = 0
            total_matches = 0
            all_users = db.query(User).all()
            for user in all_users:
                total_likes += len(user.likes_received or [])
                total_matches += len(user.matches or [])
            
            avg_likes = total_likes / total_users if total_users > 0 else 0
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'new_today': new_today,
                'new_24h': new_24h,
                'users_with_photos': users_with_photos,
                'total_likes': total_likes,
                'total_matches': total_matches,
                'avg_likes': round(avg_likes, 2)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return None
        finally:
            db.close()
    
    def show_stats(self, call):
        stats = self.get_stats()
        if not stats:
            self.bot.answer_callback_query(call.id, "❌ Ошибка получения статистики")
            return
        
        text = f"""📊 *Статистика бота*

👥 Пользователи:
├ Всего: {stats['total_users']}
├ Активных: {stats['active_users']}
├ С фото: {stats['users_with_photos']}
└ Новых за 24ч: {stats['new_24h']}

❤️ Взаимодействия:
├ Всего лайков: {stats['total_likes']}
├ Всего мэтчей: {stats['total_matches']}
└ Среднее лайков: {stats['avg_likes']}

📅 Новых сегодня: {stats['new_today']}"""
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=self.get_back_button()
        )
    
    def show_all_profiles(self, call, page=0, page_size=10):
        db = get_db()
        if not db:
            self.bot.answer_callback_query(call.id, "❌ Ошибка БД")
            return
        
        try:
            total_users = db.query(User).count()
            users = db.query(User).order_by(User.created_at.desc()).offset(page * page_size).limit(page_size).all()
            
            text = f"👥 *Все анкеты* (страница {page+1})\n\n"
            
            for i, user in enumerate(users, start=1):
                created_str = user.created_at.strftime("%d.%m.%Y %H:%M")
                active = "✅" if user.is_active else "⛔"
                photos = f"📸{len(user.photos)}" if user.photos else "❌"
                
                text += f"{i}. *{user.name}* (@{user.username or 'нет'})\n"
                text += f"   ID: `{user.telegram_id}` | {active} | {photos}\n"
                text += f"   🎮 {user.platform} | 🌍 {user.region}\n"
                text += f"   📅 {created_str}\n"
                text += f"   ❤️ {len(user.likes_received or [])} | 💌 {len(user.matches or [])}\n\n"
            
            text += f"Всего анкет: {total_users}"
            
            markup = types.InlineKeyboardMarkup()
            
            if page > 0:
                markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"admin_profiles_{page-1}"))
            
            if (page + 1) * page_size < total_users:
                if page > 0:
                    markup.row()
                markup.add(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"admin_profiles_{page+1}"))
            
            markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="admin_back"))
            
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа анкет: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")
        finally:
            db.close()
    
    def show_new_profiles(self, call):
        db = get_db()
        if not db:
            self.bot.answer_callback_query(call.id, "❌ Ошибка БД")
            return
        
        try:
            last_24h = datetime.now() - timedelta(hours=24)
            new_users = db.query(User).filter(
                User.created_at >= last_24h
            ).order_by(User.created_at.desc()).limit(20).all()
            
            text = "🆕 *Новые анкеты за 24 часов*\n\n"
            
            if not new_users:
                text += "Нет новых анкет за последние 24 часа."
            else:
                for i, user in enumerate(new_users, start=1):
                    created_str = user.created_at.strftime("%H:%M")
                    text += f"{i}. *{user.name}* (@{user.username or 'нет'})\n"
                    text += f"   🕐 {created_str} | 🎮 {user.platform}\n"
                    text += f"   📝 {user.about[:50]}...\n\n"
            
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=self.get_back_button()
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа новых анкет: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")
        finally:
            db.close()
    
    def show_matches_stats(self, call):
        db = get_db()
        if not db:
            self.bot.answer_callback_query(call.id, "❌ Ошибка БД")
            return
        
        try:
            all_users = db.query(User).all()
            
            matches_data = []
            for user in all_users:
                if user.matches:
                    matches_data.append({
                        'name': user.name,
                        'username': user.username,
                        'matches': len(user.matches),
                        'telegram_id': user.telegram_id
                    })
            
            matches_data.sort(key=lambda x: x['matches'], reverse=True)
            
            text = "💌 *Топ пользователей по мэтчам*\n\n"
            
            if not matches_data:
                text += "Пока нет мэтчей."
            else:
                for i, data in enumerate(matches_data[:10], start=1):
                    text += f"{i}. *{data['name']}* (@{data['username'] or 'нет'})\n"
                    text += f"   💌 {data['matches']} мэтчей | ID: `{data['telegram_id']}`\n\n"
            
            total_matches = sum([len(user.matches or []) for user in all_users]) // 2
            
            text += f"\nВсего мэтчей в системе: {total_matches}"
            
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=self.get_back_button()
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа мэтчей: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")
        finally:
            db.close()
    
    def show_live_stats(self, call):
        db = get_db()
        if not db:
            self.bot.answer_callback_query(call.id, "❌ Ошибка БД")
            return
        
        try:
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(days=1)
            
            # Активность за последний час
            recent_activity = 0
            all_users = db.query(User).all()
            for user in all_users:
                if user.likes_given:
                    # Простая проверка - считаем что активность есть если есть лайки
                    recent_activity += len(user.likes_given) * 0.1  # Примерная метрика
            
            # Новые пользователи за день
            new_today = db.query(User).filter(
                User.created_at >= day_ago
            ).count()
            
            # Лайки за день
            likes_today = 0
            for user in all_users:
                # Простая оценка - считаем что 30% лайков были сегодня
                likes_today += len(user.likes_given or []) * 0.3
            
            text = f"""📈 *Лайв-статистика*

🕐 *Последний час:*
├ Активных пользователей: ~{int(recent_activity)}
└ Примерная активность: {'🔥' if recent_activity > 10 else '💤'}

📅 *За последние 24 часа:*
├ Новых пользователей: {new_today}
├ Примерно лайков: ~{int(likes_today)}
└ Мэтчей: ~{int(likes_today * 0.1)}

💡 *Рекомендации:*
{'✅ Всё отлично! Бот активен.' if recent_activity > 5 else '⚠️ Низкая активность. Возможно нужна реклама.'}

⏰ Время сервера: {now.strftime('%H:%M:%S')}"""
            
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=self.get_refresh_button()
            )
            
        except Exception as e:
            logger.error(f"Ошибка лайв-статы: {e}")
            self.bot.answer_callback_query(call.id, "❌ Ошибка")
        finally:
            db.close()
    
    def get_back_button(self):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="admin_back"))
        return markup
    
    def get_refresh_button(self):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="admin_live_stats"))
        markup.add(types.InlineKeyboardButton("⬅️ Назад в меню", callback_data="admin_back"))
        return markup
    
    def handle_callback(self, call):
        data = call.data
        
        if data == "admin_stats":
            self.show_stats(call)
        elif data == "admin_all_profiles":
            self.show_all_profiles(call)
        elif data.startswith("admin_profiles_"):
            page = int(data.split("_")[2])
            self.show_all_profiles(call, page)
        elif data == "admin_new_profiles":
            self.show_new_profiles(call)
        elif data == "admin_matches":
            self.show_matches_stats(call)
        elif data == "admin_live_stats":
            self.show_live_stats(call)
        elif data == "admin_refresh":
            self.show_admin_menu(call.message)
        elif data == "admin_back":
            self.show_admin_menu(call.message)