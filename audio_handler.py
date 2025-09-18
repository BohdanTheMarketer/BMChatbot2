import requests
import json
import logging
import openai
from config import ELEVENLABS_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)

class AudioHandler:
    def __init__(self):
        self.api_key = ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"
        self.voice_id = "pNInz6obpgDQGcFmaJgB"  # Eleven3 alpha (Adam - male voice)
        
        # Initialize OpenAI client for text generation
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
    def generate_audio_summary(self, match_result: str, user_query: str) -> str:
        """
        Generate audio summary starting with "Привіт! Я думаю, що..."
        Returns the path to the generated audio file
        """
        try:
            # Create summary text using ChatGPT for better quality
            summary_text = self._create_summary_with_chatgpt(match_result, user_query)
            logger.info(f"📝 Created audio summary text: {summary_text[:100]}...")
            
            # Generate audio using ElevenLabs API
            audio_path = self._generate_audio(summary_text)
            logger.info(f"🎵 Generated audio file: {audio_path}")
            
            return audio_path
            
        except Exception as e:
            logger.error(f"❌ Error generating audio summary: {e}")
            return None
    
    def _create_summary_text(self, match_result: str, user_query: str) -> str:
        """
        Create a summary text that paraphrases only the "Чому корисний для вас" part
        """
        # Extract key information from match result
        lines = match_result.split('\n')
        expert_name = ""
        match_percentage = ""
        description = ""
        reason = ""
        
        for line in lines:
            if "Знайдений експерт:" in line:
                # Remove emoji and clean up the name
                expert_name = line.replace("💼 Знайдений експерт:", "").strip()
                expert_name = expert_name.replace("—", "-").strip()
            elif "Збіг —" in line:
                match_percentage = line.replace("🧮 Збіг —", "").strip()
        
        # Get description part
        desc_start = match_result.find("📋 Про експерта:")
        if desc_start != -1:
            desc_part = match_result[desc_start:]
            desc_lines = desc_part.split('\n')[1:]  # Skip the header
            # Find the end of description (before "Чому корисний")
            desc_text = []
            for line in desc_lines:
                if "Чому корисний для вас:" in line:
                    break
                desc_text.append(line.strip())
            description = ' '.join(desc_text[:2])  # Take first 2 lines
        
        # Get reason part
        reason_start = match_result.find("Чому корисний для вас:")
        if reason_start != -1:
            reason_part = match_result[reason_start:]
            reason_lines = reason_part.split('\n')[1:]  # Skip the header
            reason_text = []
            for line in reason_lines:
                if line.strip() and not line.startswith("📋") and not line.startswith("💼") and not line.startswith("✨"):
                    # Clean the line from emojis
                    clean_line = line.replace("✅", "").strip()
                    if clean_line:
                        reason_text.append(clean_line)
            reason = ' '.join(reason_text[:1])  # Take first line
            
        # Create summary with paraphrased reason
        summary = "Привіт! Я думаю, що знайшов для вас ідеального експерта. "
        
        if expert_name:
            summary += f"Це {expert_name}. "
            
        if match_percentage:
            summary += f"Збіг становить {match_percentage}. "
            
        if description:
            # Keep description as is, just clean emojis
            clean_desc = description.replace("✅", "").replace("📋", "").replace("💼", "").replace("🧮", "").strip()
            summary += f"Експерт {clean_desc}. "
            
        if reason:
            # Paraphrase only the reason part
            clean_reason = reason.replace("✨", "").replace("✅", "").strip()
            # Simple paraphrasing for the reason
            paraphrased_reason = self._paraphrase_reason(clean_reason)
            summary += f"{paraphrased_reason}. "
        else:
            # If no reason found, add default
            summary += "Корисний тому що має відповідний досвід та навички для вашого запиту. "
            
        summary += "Рекомендую звернутися до цього професіонала для подальшої співпраці."
        
        return summary
    
    def _create_summary_with_chatgpt(self, match_result: str, user_query: str) -> str:
        """
        Create a realistic summary text using ChatGPT for better quality and naturalness
        """
        try:
            # Extract key information from match result
            lines = match_result.split('\n')
            expert_name = ""
            match_percentage = ""
            description = ""
            reason = ""
            
            for line in lines:
                if "Знайдений експерт:" in line:
                    expert_name = line.replace("💼 Знайдений експерт:", "").strip()
                    expert_name = expert_name.replace("—", "-").strip()
                elif "Збіг —" in line:
                    match_percentage = line.replace("🧮 Збіг —", "").strip()
            
            # Get description part
            desc_start = match_result.find("📋 Про експерта:")
            if desc_start != -1:
                desc_part = match_result[desc_start:]
                desc_lines = desc_part.split('\n')[1:]
                desc_text = []
                for line in desc_lines:
                    if "Чому корисний для вас:" in line:
                        break
                    desc_text.append(line.strip())
                description = ' '.join(desc_text[:2])
            
            # Get reason part
            reason_start = match_result.find("Чому корисний для вас:")
            if reason_start != -1:
                reason_part = match_result[reason_start:]
                reason_lines = reason_part.split('\n')[1:]
                reason_text = []
                for line in reason_lines:
                    if line.strip() and not line.startswith("📋") and not line.startswith("💼") and not line.startswith("✨"):
                        clean_line = line.replace("✅", "").strip()
                        if clean_line:
                            reason_text.append(clean_line)
                reason = ' '.join(reason_text[:1])
            
            # Create prompt for ChatGPT
            system_prompt = """Ти - дружній бізнес-консультант, який допомагає людям знаходити професіоналів для співпраці. 
Створи короткий, природний та переконливий текст-рекомендацію українською мовою, який почнеться з "Привіт! Я думаю, що...".
Текст має звучати так, ніби ти особисто рекомендуєш цього експерта і радиш познайомитись з ним.
Будь ентузіастичним, але не надто офіційним. Використовуй природну мову, як у розмові з другом."""
            
            user_prompt = f"""Користувач шукав: {user_query}

Знайдений експерт: {expert_name}
Збіг: {match_percentage}
Про експерта: {description}
Чому корисний: {reason}

Створи короткий текст-рекомендацію (3-4 речення), який почнеться з "Привіт! Я думаю, що..." і звучатиме як особиста рекомендація від друга."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"🤖 ChatGPT generated summary: {summary[:100]}...")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error creating summary with ChatGPT: {e}")
            # Fallback to original method
            return self._create_summary_text(match_result, user_query)
    
    def _paraphrase_reason(self, reason: str) -> str:
        """
        Paraphrase the reason text to make it sound more natural
        """
        # Simple paraphrasing rules
        paraphrases = {
            "Розробка програмного забезпечення": "має досвід у розробці програмного забезпечення",
            "Досвід у сфері штучного інтелекту": "спеціалізується на штучному інтелекті",
            "Making angel investments": "займається ангельськими інвестиціями",
            "Investment in a real estate": "інвестує в нерухомість",
            "Fundraising": "допомагає з залученням коштів",
            "Investing": "має досвід інвестування",
            "Making investments": "займається інвестуванням",
            "Marketing": "спеціалізується на маркетингу",
            "Business development": "займається розвитком бізнесу",
            "Startups": "працює зі стартапами"
        }
        
        # Try to find and replace known phrases
        for original, paraphrase in paraphrases.items():
            if original.lower() in reason.lower():
                return reason.replace(original, paraphrase)
        
        # If no specific paraphrase found, add a natural prefix
        if reason.strip():
            return f"Корисний тому що {reason.strip()}"
        
        return "має відповідний досвід та навички для вашого запиту"
    
    def _generate_audio(self, text: str) -> str:
        """
        Generate audio file using ElevenLabs API
        """
        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_v3",  # Eleven3 alpha model
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        # Add timeout to prevent hanging
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Save audio file
            audio_filename = f"audio_summary_{hash(text) % 10000}.mp3"
            audio_path = f"/tmp/{audio_filename}"
            
            with open(audio_path, 'wb') as f:
                f.write(response.content)
                
            return audio_path
        else:
            logger.error(f"❌ ElevenLabs API error: {response.status_code} - {response.text}")
            raise Exception(f"ElevenLabs API error: {response.status_code}")
    
    def cleanup_audio_file(self, audio_path: str):
        """
        Clean up temporary audio file
        """
        try:
            import os
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"🗑️ Cleaned up audio file: {audio_path}")
        except Exception as e:
            logger.error(f"❌ Error cleaning up audio file: {e}")
