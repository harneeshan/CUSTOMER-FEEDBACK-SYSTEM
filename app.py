from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
import sqlite3
from datetime import datetime
import bcrypt

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key in production

def init_db():
    with sqlite3.connect('feedback.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback_forms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                feedback TEXT NOT NULL,
                rating INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (form_id) REFERENCES feedback_forms (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        # Create default admin user if not exists
        cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                          ('admin', 'admin@example.com', hashed, 'admin'))
        conn.commit()

def get_user(user_id):
    with sqlite3.connect('feedback.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = get_user(session['user_id'])
    with sqlite3.connect('feedback.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, title, description FROM feedback_forms ORDER BY created_at DESC')
        forms = cursor.fetchall()
    return render_template('index.html', user=user, forms=forms)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('feedback.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
                session['user_id'] = user[0]
                session['role'] = user[4]
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'error')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            with sqlite3.connect('feedback.db') as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)',
                              (username, email, hashed, 'user'))
                conn.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/create_form', methods=['GET', 'POST'])
def create_form():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Only admins can create feedback forms', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        created_by = session['user_id']
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect('feedback.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO feedback_forms (title, description, created_by, created_at) VALUES (?, ?, ?, ?)',
                          (title, description, created_by, created_at))
            conn.commit()
            flash('Feedback form created successfully!', 'success')
            return redirect(url_for('index'))
    return render_template('create_form.html')

@app.route('/api/feedback', methods=['GET'])
def get_feedback():
    with sqlite3.connect('feedback.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.id, u.username, f.email, f.feedback, f.rating, f.created_at, ff.title
            FROM feedback f
            JOIN users u ON f.user_id = u.id
            JOIN feedback_forms ff ON f.form_id = ff.id
            ORDER BY f.created_at DESC
        ''')
        feedback_list = cursor.fetchall()
        return jsonify([{
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'feedback': row[3],
            'rating': row[4],
            'created_at': row[5],
            'form_title': row[6]
        } for row in feedback_list])

@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json
    form_id = data.get('form_id')
    name = data.get('name')
    email = data.get('email')
    feedback = data.get('feedback')
    rating = data.get('rating')
    user_id = session['user_id']
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with sqlite3.connect('feedback.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (form_id, user_id, name, email, feedback, rating, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (form_id, user_id, name, email, feedback, rating, created_at))
        conn.commit()
        return jsonify({'message': 'Feedback added successfully'}), 201

@app.route('/api/feedback/<int:id>', methods=['DELETE'])
def delete_feedback(id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    with sqlite3.connect('feedback.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM feedback WHERE id = ?', (id,))
        conn.commit()
        return jsonify({'message': 'Feedback deleted successfully'}), 200

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 