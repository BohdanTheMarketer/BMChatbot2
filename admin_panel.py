from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import Database
import json
from datetime import datetime

app = Flask(__name__)
db = Database()

# Simple authentication (in production, use proper authentication)
ADMIN_PASSWORD = "businessmatch2024"

def check_auth():
    """Simple authentication check"""
    return request.cookies.get('admin_auth') == ADMIN_PASSWORD

@app.route('/')
def index():
    """Main dashboard"""
    if not check_auth():
        return redirect(url_for('login'))
    
    stats = db.get_stats()
    from datetime import datetime
    current_time = datetime.now().strftime('%d.%m.%Y %H:%M')
    return render_template('dashboard.html', stats=stats, moment=current_time)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            response = redirect(url_for('index'))
            response.set_cookie('admin_auth', ADMIN_PASSWORD)
            return response
        else:
            return render_template('login.html', error="Неправильний пароль")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Admin logout"""
    response = redirect(url_for('login'))
    response.set_cookie('admin_auth', '', expires=0)
    return response

@app.route('/users')
def users():
    """Users list page"""
    if not check_auth():
        return redirect(url_for('login'))
    
    users_list = db.get_all_users()
    return render_template('users.html', users=users_list)

@app.route('/user/<int:user_id>')
def user_detail(user_id):
    """User detail page with messages and searches"""
    if not check_auth():
        return redirect(url_for('login'))
    
    # Get user info
    users_list = db.get_all_users()
    user = next((u for u in users_list if u['user_id'] == user_id), None)
    
    if not user:
        return "Користувач не знайдений", 404
    
    # Get user messages and searches
    messages = db.get_user_messages(user_id, 100)
    searches = db.get_user_searches(user_id, 50)
    
    return render_template('user_detail.html', 
                         user=user, 
                         messages=messages, 
                         searches=searches)

@app.route('/api/stats')
def api_stats():
    """API endpoint for statistics"""
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = db.get_stats()
    return jsonify(stats)

@app.route('/api/messages/<int:user_id>')
def api_user_messages(user_id):
    """API endpoint for user messages"""
    if not check_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    
    limit = request.args.get('limit', 50, type=int)
    messages = db.get_user_messages(user_id, limit)
    return jsonify(messages)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
