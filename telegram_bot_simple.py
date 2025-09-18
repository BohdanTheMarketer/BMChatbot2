#!/usr/bin/env python3
"""
Simple Telegram Bot for Business Match
Uses direct API calls instead of python-telegram-bot library
"""

import requests
import json
import time
import logging
import fcntl
import os
from datetime import datetime, timedelta
from data_handler import DataHandler
from chatgpt_handler import ChatGPTHandler
from config import TELEGRAM_BOT_TOKEN, USERS_CSV_PATH
from database import Database
from audio_handler import AudioHandler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.data_handler = DataHandler(USERS_CSV_PATH)
        self.chatgpt_handler = ChatGPTHandler(self.data_handler)
        self.database = Database()  # Initialize database
        self.audio_handler = AudioHandler()
        self.user_sessions = {}
        self.user_last_search_time = {}  # Track when each user last searched (24h limit)
        self.last_update_id = 0
        self.processed_updates = set()  # Track processed updates to prevent duplicates
        
        # File lock to prevent multiple bot instances
        self.lock_file = "/tmp/bmchatbot.lock"
        self.lock_fd = None
        self._acquire_lock()
    
    def _acquire_lock(self):
        """Acquire file lock to prevent multiple bot instances"""
        try:
            self.lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            logger.info("🔒 File lock acquired - single bot instance ensured")
        except (OSError, IOError):
            logger.error("❌ Another bot instance is already running!")
            raise SystemExit("Bot instance already running")
    
    def _cleanup_lock(self):
        """Release file lock"""
        try:
            if self.lock_fd:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                os.close(self.lock_fd)
                os.unlink(self.lock_file)
                logger.info("🔓 File lock released")
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
    
    def get_user_session(self, user_id: int) -> ChatGPTHandler:
        """Get or create user session"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = ChatGPTHandler(self.data_handler)
        return self.user_sessions[user_id]
    
    def log_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Log user information to database"""
        try:
            self.database.add_user(user_id, username, first_name, last_name)
        except Exception as e:
            logger.error(f"Error logging user {user_id}: {e}")
    
    def log_message(self, user_id: int, content: str, is_bot: bool = False, message_type: str = "text"):
        """Log message to database"""
        try:
            self.database.add_message(user_id, content, is_bot, message_type)
        except Exception as e:
            logger.error(f"Error logging message for user {user_id}: {e}")
    
    def log_search(self, user_id: int, search_query: str, search_result: str = None):
        """Log search to database"""
        try:
            self.database.add_search(user_id, search_query, search_result)
        except Exception as e:
            logger.error(f"Error logging search for user {user_id}: {e}")
    
    def can_user_search(self, user_id: int) -> tuple[bool, str]:
        """Check if user can make a search (24h limit)"""
        current_time = datetime.now()
        
        if user_id not in self.user_last_search_time:
            return True, ""
        
        last_search = self.user_last_search_time[user_id]
        time_passed = current_time - last_search
        
        if time_passed >= timedelta(hours=24):
            return True, ""
        
        # Calculate remaining time
        remaining_time = timedelta(hours=24) - time_passed
        hours = int(remaining_time.total_seconds() // 3600)
        minutes = int((remaining_time.total_seconds() % 3600) // 60)
        
        if hours > 0:
            time_str = f"{hours} год. {minutes} хв."
        else:
            time_str = f"{minutes} хв."
        
        return False, time_str
    
    def _is_search_query(self, text: str) -> bool:
        """Check if the message is a search query or other message"""
        text_lower = text.lower().strip()
        
        # Non-search indicators
        non_search_indicators = [
            "дякую", "спасибі", "thank you", "thanks",
            "привіт", "вітаю", "добрий день", "доброго дня", "hello", "hi",
            "як справи", "що нового", "how are you",
            "допоможи", "help", "допомога",
            "що робиш", "що можна", "можливості",
            "тест", "test", "перевірка",
            "працює", "робота", "work",
            "старт", "start", "почати",
            "інформація", "information", "інфо", "info"
        ]
        
        # Check for non-search indicators
        for indicator in non_search_indicators:
            if indicator in text_lower:
                return False
        
        # Check for search keywords
        search_keywords = [
            "шукаю", "потрібен", "потрібні", "потрібна", "потрібно",
            "експерт", "фахівець", "спеціаліст", "професіонал",
            "маркетинг", "дизайн", "розробка", "програмування",
            "інвестор", "інвестиції", "бізнес", "стартап",
            "ментор", "консультант", "тренер", "коуч",
            "продажі", "реклама", "PR", "брендинг",
            "фінанси", "бухгалтер", "юрист", "HR",
            "IT", "технології", "цифрові", "онлайн"
        ]
        
        # If contains search keywords, it's likely a search query
        for keyword in search_keywords:
            if keyword in text_lower:
                return True
        
        # If very short and no clear indicators, treat as non-search
        if len(text_lower) < 10:
            return False
        
        # Default to search query for longer messages without clear non-search indicators
        return True
    
    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown"):
        """Send a message to a chat"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return None
    
    def send_photo(self, chat_id: int, photo_url: str, caption: str = ""):
        """Send a photo to a chat"""
        url = f"{self.base_url}/sendPhoto"
        data = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }
        
        try:
            logger.info(f"Sending photo to chat {chat_id}: {photo_url}")
            response = requests.post(url, json=data)
            result = response.json()
            if response.status_code == 200:
                logger.info(f"✅ Photo sent successfully to chat {chat_id}")
            else:
                logger.error(f"❌ Failed to send photo: HTTP {response.status_code}: {result}")
            return result
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return None
    
    def send_audio(self, chat_id: int, audio_path: str):
        """Send an audio file to a chat"""
        url = f"{self.base_url}/sendAudio"
        
        try:
            with open(audio_path, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {
                    'chat_id': chat_id,
                    'title': 'Підсумок збігу',
                    'performer': 'Business Match Bot'
                }
                
                response = requests.post(url, files=files, data=data)
                
                if response.status_code == 200:
                    logger.info(f"✅ Audio sent to chat {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to send audio: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending audio: {e}")
            return False
    
    def send_typing(self, chat_id: int):
        """Send typing indicator"""
        url = f"{self.base_url}/sendChatAction"
        data = {
            "chat_id": chat_id,
            "action": "typing"
        }
        
        try:
            requests.post(url, json=data)
        except Exception as e:
            logger.error(f"Error sending typing: {e}")
    
    def get_updates(self):
        """Get new updates from Telegram"""
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": 10,
            "allowed_updates": ["message"]
        }
        
        try:
            response = requests.get(url, params=params, timeout=35)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"HTTP {response.status_code}: {response.text}")
                return None
        except requests.exceptions.Timeout:
            # Timeout is normal for long polling
            return {"ok": True, "result": []}
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return None
    
    def handle_start_command(self, chat_id: int, user_id: int, user_info: dict = None):
        """Handle /start command"""
        logger.info(f"🚀 Starting /start command for user {user_id} in chat {chat_id}")
        
        # Log user information if available
        if user_info:
            self.log_user(
                user_id, 
                user_info.get('username'),
                user_info.get('first_name'),
                user_info.get('last_name')
            )
        
        # Log the /start command
        self.log_message(user_id, "/start", False, "start")
        
        # Send Business Match image first
        logger.info(f"📸 Attempting to send Business Match image to chat {chat_id}")
        # Use your Business Match image from Postimage
        business_match_image_url = "https://i.postimg.cc/mtFChPhV/ChatGPT-Image-15-вер-2025-р-18-52-13.png"
        logger.info(f"Using Business Match image URL: {business_match_image_url}")
        self.send_photo(chat_id, business_match_image_url, caption="🚀 Business Match - Ваш асистент з нетворкінгу")
        
        # Use the new greeting message directly
        message = """Вітаємо у Business Match 🚀
Я — ваш асистент зі структурованого нетворкінгу. У нашій базі понад 50 000+ перевірених професіоналів, відкритих до співпраці. Допоможу швидко знайти релевантних партнерів та можливості для розвитку бізнесу 📈

🤝 Як це працює:
Опишіть, кого шукаєте: галузь, роль, рівень, географія, формат співпраці.

📌 Приклади запитів:
• «Шукаю маркетологів для IT-стартапу»
• «Потрібні інвестори для e-commerce проєкту»
• «Хочу зустрітися з підприємцями у сфері охорони здоров'я»
• «Шукаю ментора з digital-маркетингу»

Я зіставлю ваш запит із базою та надам короткий список релевантних контактів із обґрунтуванням ✅"""
        
        self.send_message(chat_id, message)
    
    def handle_text_message(self, chat_id: int, user_id: int, text: str):
        """Handle text messages"""
        logger.info(f"🔍 Processing text message from user {user_id}: {text[:50]}...")
        
        # Log user message
        self.log_message(user_id, text, False, "text")
        
        # Check if user can search (24h limit)
        can_search, remaining_time = self.can_user_search(user_id)
        logger.info(f"⏰ User {user_id} can search: {can_search}, remaining time: '{remaining_time}'")
        
        if not can_search:
            logger.info(f"🚫 Blocking user {user_id} due to 24h limit")
            limit_message = (f"⏰ **Ліміт пошуку!**\n\n"
                f"Ви вже зробили пошук менше ніж 24 години тому.\n"
                f"**Доступно через:** {remaining_time}\n\n"
                f"🚀 **Для необмеженого доступу встановіть додаток Business Match:**\n\n"
                f"📱 [Business Match App](https://apps.apple.com/ua/app/business-match-social-app/id1547614364)\n\n"
                f"✨ Там ви зможете робити необмежену кількість пошуків та знайти всіх експертів!")
            
            self.send_message(chat_id, limit_message)
            self.log_message(user_id, limit_message, True, "text")
            return
        
        chatgpt_handler = self.get_user_session(user_id)
        
        # Check if this is a search query or other message
        is_search_query = self._is_search_query(text)
        
        if not is_search_query:
            # Handle non-search messages with ChatGPT
            logger.info(f"💬 Handling non-search message from user {user_id}")
            response = chatgpt_handler.handle_non_search_message(text)
            self.send_message(chat_id, response)
            return
        
        # This is a search query - use custom model
        logger.info(f"🔍 Handling search query from user {user_id}")
        
        # Send typing indicator
        self.send_typing(chat_id)
        
        # Send progress messages with delays
        self.send_message(chat_id, "📥 **Отримання інформації...**")
        import time
        time.sleep(3)
        
        self.send_message(chat_id, "🤖 **Обробка інформації за допомогою AI...**")
        time.sleep(3)
        
        self.send_message(chat_id, "🔍 **Пошук користувачів, які підходять під ваш запит...**")
        time.sleep(3)
        
        self.send_message(chat_id, "⏳ **Детальний аналіз збігів... (це може зайняти до 2 хвилин)**")
        
        # Get matches from custom model with error handling
        logger.info(f"🔄 Calling custom model for user {user_id}...")
        try:
            matches_response = chatgpt_handler.analyze_user_preferences(text)
            logger.info(f"✅ Custom model response received for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Error calling custom model for user {user_id}: {e}")
            self.send_message(chat_id, 
                "😔 **Виникла помилка при обробці запиту.**\n\n"
                "Спробуйте ще раз або зверніться до підтримки."
            )
            return
        
        # Check if query is unclear
        if matches_response == "unclear_query":
            self.send_message(chat_id,
                "🤔 **Ваш запит не зовсім зрозумілий.**\n\n"
                "Будь ласка, сформулюйте точніше, яких бізнес-професіоналів ви шукаєте.\n\n"
                "**Приклади чітких запитів:**\n"
                "• «Шукаю фахівців із маркетингу для IT-стартапу»\n"
                "• «Потрібні інвестори для e-commerce проєкту»\n"
                "• «Хочу зустрітися з підприємцями у сфері охорони здоров'я»\n"
                "• «Шукаю менторів із digital-маркетингу»"
            )
            return
        
        try:
            # Try to parse JSON response
            import json
            logger.info(f"🔍 Attempting to parse JSON response: {matches_response[:200]}...")
            match_data = json.loads(matches_response)
            logger.info(f"✅ Successfully parsed JSON for user {user_id}")
            
            # Send structured match information
            match_message = f"💼 **Знайдений експерт: {match_data['name']}**\n"
            match_message += f"🧮 **Збіг - {match_data.get('match_percentage', '85')}%**\n\n"
            
            match_message += f"📋 **Про експерта:**\n{match_data['description']}\n\n"
            
            # Add contact information if available
            if match_data.get('contact_info') and match_data['contact_info'] != 'Не вказано':
                match_message += f"📞 **Контактна інформація:** {match_data['contact_info']}\n\n"
            
            match_message += f"✨ **Чому корисний для вас:** {match_data['reason']}"
            
            self.send_message(chat_id, match_message)
            logger.info(f"✅ Sent match result to user {user_id}")
                
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to direct text format
            logger.info(f"📝 Using direct text format for user {user_id}")
            self.send_message(chat_id, matches_response)
            logger.info(f"✅ Sent match result (text format) to user {user_id}")
        
        # Log the search and result
        self.log_search(user_id, text, matches_response)
        
        # Only update search time and send follow-up messages if we successfully sent a match
        # Update last search time (24h limit)
        self.user_last_search_time[user_id] = datetime.now()
        logger.info(f"⏰ Updated search time for user {user_id}")
        
        # Send combined 24h limit and app promotion message
        logger.info(f"📱 Sending combined message to user {user_id}")
        combined_message = "Дякую, що скористались ботом. Ви маєте можливість робити один такий запит раз на 24 години.\n\n💡 Для доступу до більшої бази професіоналів та повного функціоналу встановіть додаток Business Match!\n\n📱 [Встановити Business Match](https://apps.apple.com/ua/app/business-match-social-app/id1547614364)"
        self.send_message(chat_id, combined_message)
        self.log_message(user_id, combined_message, True, "text")
        logger.info(f"✅ Sent combined message to user {user_id}")
        
        # Generate and send audio summary
        try:
            logger.info(f"🎵 Generating audio summary for user {user_id}")
            audio_path = self.audio_handler.generate_audio_summary(matches_response, text)
            if audio_path:
                logger.info(f"🎵 Sending audio summary to user {user_id}")
                if self.send_audio(chat_id, audio_path):
                    logger.info(f"✅ Audio summary sent to user {user_id}")
                else:
                    logger.error(f"❌ Failed to send audio summary to user {user_id}")
                # Clean up audio file
                self.audio_handler.cleanup_audio_file(audio_path)
            else:
                logger.error(f"❌ Failed to generate audio summary for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Error with audio summary for user {user_id}: {e}")
    
    def handle_help_command(self, chat_id: int):
        """Handle /help command"""
        help_text = """
*🤖 Допомога Business Match Bot*

*Команди:*
/start - Почати роботу з ботом та отримати інструкції
/help - Показати це повідомлення допомоги
/cancel - Скасувати поточну розмову

*Як знайти бізнес-зв'язки:*
Просто напишіть, що ви шукаєте! Наприклад:
• "Шукаю експертів з маркетингу в IT-стартапах"
• "Потрібні інвестори для мого e-commerce бізнесу"
• "Хочу зустрітися з підприємцями в сфері охорони здоров'я"

Бот проаналізує нашу базу з 500+ професіоналів і надасть вам топ-3 найкращих збігів з детальними поясненнями!

*Функції:*
✅ AI-збіги за допомогою ChatGPT
✅ 500+ бізнес-професіоналів у базі даних
✅ Детальний аналіз сумісності
✅ Контактна інформація та посилання на соцмережі
✅ Обробка природної мови
"""
        self.send_message(chat_id, help_text)
    
    def process_update(self, update):
        """Process a single update"""
        try:
            if "message" not in update:
                return
            
            message = update["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]
            text = message.get("text", "")
            
            logger.info(f"Received message from user {user_id}: {text[:50]}...")
            
            # Handle commands
            if text.startswith("/start"):
                # Get user info from the message
                user_info = message.get("from", {})
                self.handle_start_command(chat_id, user_id, user_info)
            elif text.startswith("/help"):
                self.handle_help_command(chat_id)
            elif text.startswith("/cancel"):
                self.send_message(chat_id, "✅ Розмову скасовано. Використовуйте /start для початку нового пошуку!")
            else:
                # Handle regular text messages
                if text.strip():
                    self.handle_text_message(chat_id, user_id, text)
                    
        except Exception as e:
            logger.error(f"Error processing update: {e}")
    
    def run(self):
        """Main bot loop"""
        logger.info("🤖 Starting Business Match Telegram Bot...")
        logger.info("📊 Database loaded: 500+ professionals")
        logger.info("🔍 Ready to find business matches!")
        
        # Get bot info
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            bot_info = response.json()
            if bot_info.get("ok"):
                bot_name = bot_info["result"]["first_name"]
                bot_username = bot_info["result"]["username"]
                logger.info(f"✅ Bot connected: {bot_name} (@{bot_username})")
            else:
                logger.error("❌ Failed to get bot info")
                return
        except Exception as e:
            logger.error(f"❌ Error connecting to Telegram: {e}")
            return
        
        logger.info("🔄 Starting polling for messages...")
        logger.info("🛡️ Duplicate message protection enabled")
        
        while True:
            try:
                # Get updates
                updates_response = self.get_updates()
                
                if not updates_response or not updates_response.get("ok"):
                    logger.warning("Failed to get updates")
                    time.sleep(5)
                    continue
                
                updates = updates_response["result"]
                
                # Process each update
                for update in updates:
                    update_id = update["update_id"]
                    
                    # Skip if we already processed this update
                    if update_id in self.processed_updates:
                        logger.info(f"🛡️ Skipping duplicate update {update_id}")
                        self.last_update_id = update_id
                        continue
                    
                    # Mark as processed and process
                    self.processed_updates.add(update_id)
                    self.last_update_id = update_id
                    self.process_update(update)
                
                # Small delay to avoid overwhelming the API
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
        
        # Cleanup on exit
        self._cleanup_lock()

def main():
    """Start the bot"""
    try:
        bot = SimpleTelegramBot()
        bot.run()
    except SystemExit:
        logger.info("🚫 Bot startup blocked - another instance is running")
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        raise

if __name__ == '__main__':
    main()



