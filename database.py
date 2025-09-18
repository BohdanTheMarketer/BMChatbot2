import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str = "bot_chats.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_searches INTEGER DEFAULT 0
            )
        ''')
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_bot BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Search history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                search_query TEXT NOT NULL,
                search_result TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update user information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, last_activity)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        conn.close()
    
    def add_message(self, user_id: int, content: str, is_bot: bool = False, message_type: str = "text"):
        """Add message to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (user_id, content, is_bot, message_type)
            VALUES (?, ?, ?, ?)
        ''', (user_id, content, is_bot, message_type))
        
        # Update user's last activity
        cursor.execute('''
            UPDATE users SET last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def add_search(self, user_id: int, search_query: str, search_result: str = None):
        """Add search to history and increment user's search count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO search_history (user_id, search_query, search_result)
            VALUES (?, ?, ?)
        ''', (user_id, search_query, search_result))
        
        # Increment user's total searches
        cursor.execute('''
            UPDATE users SET total_searches = total_searches + 1
            WHERE user_id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def get_all_users(self) -> List[Dict]:
        """Get all users with their statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name, u.last_name, 
                   u.created_at, u.last_activity, u.total_searches,
                   COUNT(m.id) as total_messages
            FROM users u
            LEFT JOIN messages m ON u.user_id = m.user_id
            GROUP BY u.user_id
            ORDER BY u.last_activity DESC
        ''')
        
        columns = [description[0] for description in cursor.description]
        users = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return users
    
    def get_user_messages(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get messages for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT content, timestamp, is_bot, message_type
            FROM messages
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        columns = [description[0] for description in cursor.description]
        messages = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return messages
    
    def get_user_searches(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Get search history for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT search_query, search_result, timestamp
            FROM search_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user_id, limit))
        
        columns = [description[0] for description in cursor.description]
        searches = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return searches
    
    def get_stats(self) -> Dict:
        """Get overall statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Total messages
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        
        # Total searches
        cursor.execute('SELECT COUNT(*) FROM search_history')
        total_searches = cursor.fetchone()[0]
        
        # Active users (last 24 hours)
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE last_activity > datetime('now', '-1 day')
        ''')
        active_users = cursor.fetchone()[0]
        
        # Most active users
        cursor.execute('''
            SELECT u.user_id, u.username, u.first_name, u.total_searches,
                   COUNT(m.id) as message_count
            FROM users u
            LEFT JOIN messages m ON u.user_id = m.user_id
            GROUP BY u.user_id
            ORDER BY u.total_searches DESC, message_count DESC
            LIMIT 5
        ''')
        
        columns = [description[0] for description in cursor.description]
        top_users = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_messages': total_messages,
            'total_searches': total_searches,
            'active_users': active_users,
            'top_users': top_users
        }


