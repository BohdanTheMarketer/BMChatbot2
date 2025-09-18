import openai
from typing import List, Dict, Any
import json
from config import OPENAI_API_KEY
from data_handler import DataHandler

class ChatGPTHandler:
    def __init__(self, data_handler: DataHandler):
        self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        self.data_handler = data_handler
        self.conversation_history = []
    
    def add_to_conversation(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({"role": role, "content": content})
    
    def _is_query_unclear(self, query: str) -> bool:
        """Check if the user query is unclear or irrelevant"""
        query_lower = query.lower().strip()
        
        # Check if query is too short (less than 5 characters)
        if len(query_lower) < 5:
            return True
        
        # Check for clear business/professional keywords
        business_keywords = [
            "шукаю", "потрібен", "потрібні", "потрібна", "потрібно",
            "експерт", "фахівець", "спеціаліст", "професіонал",
            "маркетинг", "дизайн", "розробка", "програмування",
            "інвестор", "інвестиції", "бізнес", "стартап",
            "ментор", "консультант", "тренер", "коуч",
            "продажі", "реклама", "PR", "брендинг",
            "фінанси", "бухгалтер", "юрист", "HR",
            "IT", "технології", "цифрові", "онлайн",
            "e-commerce", "інтернет", "соціальні мережі"
        ]
        
        # If query contains business keywords, it's likely clear
        for keyword in business_keywords:
            if keyword in query_lower:
                return False
        
        # Check for very unclear indicators (only obvious ones)
        unclear_indicators = [
            "....", "...", "???", "??", "???",
            "що робиш", "як справи", "що нового",
            "тест", "перевірка", "працює",
            "що можна", "можливості", "допоможи"
        ]
        
        # Only check for unclear indicators if no business keywords found
        for indicator in unclear_indicators:
            if indicator in query_lower:
                return True
                
        # If query is very short and has no business keywords, it's unclear
        if len(query_lower) < 15:
            return True
                
        return False

    def analyze_user_preferences(self, user_preferences: str) -> str:
        """Analyze user preferences and find matches using optimized custom model"""
        
        # First check if the query is clear enough
        if self._is_query_unclear(user_preferences):
            return "unclear_query"
        
        # Use the optimized custom model for matching with extended timeout
        import threading
        import time
        
        response = None
        exception = None
        
        def make_request():
            nonlocal response, exception
            try:
                response = self.client.responses.create(
                    prompt={
                        "id": "pmpt_68caa4dc45e88195bbd73fc66ea17464072cc683f555624b",
                        "version": "2"
                    },
                    input=user_preferences
                )
            except Exception as e:
                exception = e
        
        try:
            # Start the request in a thread
            thread = threading.Thread(target=make_request)
            thread.daemon = True
            thread.start()
            
            # Wait for 120 seconds (increased from 60)
            thread.join(timeout=120)
            
            if thread.is_alive():
                # Request is still running, it timed out
                raise Exception("Custom model call timed out after 120 seconds")
            
            if exception:
                raise exception
            
            # Extract the actual text content from the response
            if hasattr(response, 'output') and response.output:
                # Find the message content in the output
                for item in response.output:
                    if hasattr(item, 'content') and item.content:
                        for content_item in item.content:
                            if hasattr(content_item, 'text'):
                                result = content_item.text
                                break
                        else:
                            continue
                        break
                else:
                    result = "Збігів не знайдено."
            else:
                result = "Збігів не знайдено."
            
            # Add to conversation history
            self.add_to_conversation("user", user_preferences)
            self.add_to_conversation("assistant", result)
            
            return result
            
        except Exception as e:
            # Fallback to original method if custom model fails
            print(f"Custom model failed: {e}, falling back to ChatGPT 3.5")
            return self._fallback_analyze_user_preferences(user_preferences)
    
    def _fallback_analyze_user_preferences(self, user_preferences: str) -> str:
        """Fallback method using original ChatGPT approach"""
        
        # Get a sample of users for analysis (to avoid token limits)
        all_users = self.data_handler.get_all_users()
        
        # Create a focused context with key information
        users_sample = all_users[:20]  # Use first 20 users to avoid token limits
        
        users_context = "Business Match Users Database (Sample):\n\n"
        
        for i, user in enumerate(users_sample, 1):
            users_context += f"Професіонал {i}:\n"
            users_context += f"Ім'я: {user['name']}\n"
            users_context += f"Локація: {user['location']}\n"
            users_context += f"Бізнес-сектор: {user['business_sector']}\n"
            users_context += f"Цілі: {user['goals']}\n"
            users_context += f"Шукає: {user['looking_for']}\n"
            users_context += f"Відкритий до: {user['open_to']}\n"
            users_context += f"Бізнес-потреби: {user['business_needs']}\n"
            users_context += f"Інтереси: {user['interests']}\n"
            users_context += f"Компанії: {user['companies']}\n"
            users_context += f"Досягнення: {user['achievements']}\n"
            users_context += "---\n\n"
        
        # Create system prompt in Ukrainian with improved logic
        system_prompt = """Ви професійний помічник з бізнес-нетворкінгу для Business Match. 
        Ваше завдання - проаналізувати запит клієнта та знайти 1 найкращий збіг з нашої бази даних.
        
        ВАЖЛИВО: Якщо клієнт шукає конкретну професію (наприклад, веб-розробника), знайдіть людей, які ПРАЦЮЮТЬ у цій сфері, а НЕ тих, хто також ШУКАЄ цю професію.
        
        Логіка підбору:
        - Якщо клієнт шукає веб-розробника → знайдіть людей зі сфери "IT", "веб-розробка", "програмування"
        - Якщо клієнт шукає маркетолога → знайдіть людей зі сфери "маркетинг", "реклама", "PR"
        - Якщо клієнт шукає інвестора → знайдіть людей зі сфери "інвестиції", "фінанси", "бізнес-ангели"
        
        Створіть структурований, професійний опис експерта на основі даних з бази. Опис має бути природним та зрозумілим, НЕ копіюванням полів бази даних.
        
        Форматуйте вашу відповідь як JSON з одним об'єктом:
        {
            "name": "[Ім'я]",
            "match_percentage": "[Відсоток збігу від 60 до 95, наприклад 85]",
            "description": "[Структурований опис експерта у вигляді 5-10 речень, що містять ключову інформацію: професія, досвід, компанія, досягнення, що шукає, до чого відкритий]",
            "contact_info": "[Контактна інформація якщо є, інакше 'Не вказано']",
            "reason": "[Коротке пояснення чому цей експерт корисний для клієнта - 2-3 речення]"
        }
        
        Відповідайте ВИКЛЮЧНО українською мовою. Будьте професійними та зосередженими на бізнес-корисності."""
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Ось наша база даних професіоналів:\n\n{users_context}\n\nКлієнт шукає: {user_preferences}\n\nБудь ласка, знайдіть 1 найкращий збіг та відповідайте у форматі JSON як зазначено в інструкціях."}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            
            # Add to conversation history
            self.add_to_conversation("user", user_preferences)
            self.add_to_conversation("assistant", result)
            
            return result
            
        except Exception as e:
            return f"Sorry, I encountered an error while analyzing your preferences: {str(e)}"
    
    def handle_non_search_message(self, message: str) -> str:
        """Handle non-search messages using ChatGPT"""
        system_prompt = """Ви дружній бот для бізнес-нетворкінгу Business Match. 
        Відповідайте українською мовою на повідомлення користувачів.
        Якщо користувач дякує або пише привітання, відповідайте коротко та дружньо.
        Якщо користувач запитує щось не пов'язане з пошуком експертів, вежливо направте їх до пошуку."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return "Дякую за звернення! Якщо потрібно знайти бізнес-експертів, просто опишіть, кого ви шукаєте."
    
    def get_greeting_message(self) -> str:
        """Generate personalized greeting message"""
        system_prompt = """Ви дружній бот для бізнес-нетворкінгу Business Match. 
        Напишіть тепле, професійне привітання українською мовою з бізнес-емодзі. 
        Не звертайтеся до людини як "користувач", а як до реальної людини. 
        Поясніть, що ви допомагаєте знайти ідеальних бізнес-партнерів з бази 500+ професіоналів."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": system_prompt}],
                max_tokens=300,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return """Вітаємо у Business Match 🚀
Я — ваш асистент зі структурованого нетворкінгу. У нашій базі понад 50 000+ перевірених професіоналів, відкритих до співпраці. Допоможу швидко знайти релевантних партнерів та можливості для розвитку бізнесу 📈

🤝 Як це працює:
Опишіть, кого шукаєте: галузь, роль, рівень, географія, формат співпраці.

📌 Приклади запитів:
• «Шукаю маркетологів для IT-стартапу»
• «Потрібні інвестори для e-commerce проєкту»
• «Хочу зустрітися з підприємцями у сфері охорони здоров'я»
• «Шукаю ментора з digital-маркетингу»

Я зіставлю ваш запит із базою та надам короткий список релевантних контактів із обґрунтуванням ✅"""
