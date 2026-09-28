from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import hashlib
import os

app = Flask(__name__)
CORS(app)

DB_FILE = "zsatc_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS vault (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            site TEXT NOT NULL,
            site_user TEXT NOT NULL,
            site_pass TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/', methods=['GET'])
def status():
    return jsonify({"status": "online", "service": "ZSATC Browser Cloud Network"})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json or {}
    user = data.get('username')
    pw = data.get('password')
    if not user or not pw:
        return jsonify({"error": "Missing username or password"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (user, hash_pw(pw)))
        conn.commit()
        return jsonify({"message": "Account created successfully!"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    user = data.get('username')
    pw = data.get('password')
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (user, hash_pw(pw)))
    account = c.fetchone()
    conn.close()

    if account:
        return jsonify({"message": "Login successful", "username": user}), 200
    return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/vault/sync', methods=['POST'])
def sync_vault():
    data = request.json or {}
    user = data.get('username')
    entries = data.get('entries', [])

    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM vault WHERE username = ?", (user,))
    for item in entries:
        c.execute("INSERT INTO vault (username, site, site_user, site_pass) VALUES (?, ?, ?, ?)",
                  (user, item.get('site'), item.get('site_user'), item.get('site_pass')))
    conn.commit()
    conn.close()
    return jsonify({"message": "Vault synced successfully!"}), 200

@app.route('/api/vault/get', methods=['GET'])
def get_vault():
    user = request.args.get('username')
    if not user:
        return jsonify({"error": "Missing username"}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT site, site_user, site_pass FROM vault WHERE username = ?", (user,))
    rows = c.fetchall()
    conn.close()

    entries = [{"site": r[0], "site_user": r[1], "site_pass": r[2]} for r in rows]
    return jsonify({"entries": entries}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
