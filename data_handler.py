import pandas as pd
import json
from typing import List, Dict, Any

class DataHandler:
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
        self.columns = {
            'name': 'Імʼя і прізвище',
            'location': 'Локація', 
            'goals': 'Цілі',
            'business_sector': 'Сфера бізнесу',
            'interests': 'Захоплення',
            'business_needs': 'Бізнес потреби',
            'reviews': 'Відгуки про людину',
            'social_links': 'Посилання на соц.мережі',
            'achievements': 'Досягнення, якими пишається',
            'business_sectors': 'Сфери бізнесу',
            'companies': 'Компанії',
            'self_description': 'Опис від людини',
            'looking_for': 'Кого шукає',
            'open_to': 'Відкритий до',
            'interesting_facts': 'Цікаві факти про мене'
        }
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users as list of dictionaries"""
        users = []
        for _, row in self.df.iterrows():
            user = {}
            for key, column in self.columns.items():
                user[key] = str(row[column]) if pd.notna(row[column]) else ""
            users.append(user)
        return users
    
    def get_user_context_for_chatgpt(self) -> str:
        """Create context string for ChatGPT about all users"""
        users = self.get_all_users()
        context = "Business Match Users Database:\n\n"
        
        for i, user in enumerate(users, 1):
            context += f"User {i}:\n"
            context += f"Name: {user['name']}\n"
            context += f"Location: {user['location']}\n"
            context += f"Business Sector: {user['business_sector']}\n"
            context += f"Goals: {user['goals']}\n"
            context += f"Interests: {user['interests']}\n"
            context += f"Business Needs: {user['business_needs']}\n"
            context += f"Looking for: {user['looking_for']}\n"
            context += f"Open to: {user['open_to']}\n"
            context += f"Self Description: {user['self_description']}\n"
            context += f"Achievements: {user['achievements']}\n"
            context += f"Interesting Facts: {user['interesting_facts']}\n"
            context += f"Reviews: {user['reviews']}\n"
            context += f"Social Links: {user['social_links']}\n"
            context += f"Companies: {user['companies']}\n"
            context += f"Business Sectors: {user['business_sectors']}\n"
            context += "---\n\n"
        
        return context




