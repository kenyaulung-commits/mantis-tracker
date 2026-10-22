from flask import Flask, request, jsonify, render_template
import sqlite3
import os

app = Flask(__name__, template_folder='templates', static_folder='static')
DB_FILE = 'mantis.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                summary TEXT NOT NULL,
                description TEXT,
                steps TEXT,
                status TEXT DEFAULT 'New',
                severity TEXT DEFAULT 'Minor',
                priority TEXT DEFAULT 'Normal',
                category TEXT DEFAULT 'General',
                reproducibility TEXT DEFAULT 'Always',
                platform TEXT DEFAULT 'Web',
                assigned_to TEXT DEFAULT 'Unassigned',
                reporter TEXT DEFAULT 'Admin',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                author TEXT NOT NULL,
                text TEXT NOT NULL,
                is_private INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    conn = get_db()
    tickets = conn.execute('SELECT * FROM tickets ORDER BY updated_at DESC').fetchall()
    result = []
    for t in tickets:
        t_dict = dict(t)
        comments = conn.execute('SELECT * FROM comments WHERE ticket_id = ? ORDER BY created_at ASC', (t['id'],)).fetchall()
        t_dict['comments'] = [dict(c) for c in comments]
        result.append(t_dict)
    conn.close()
    return jsonify(result)

@app.route('/api/tickets', methods=['POST'])
def create_ticket():
    data = request.json or {}
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tickets (project, summary, description, steps, status, severity, priority, category, reproducibility, platform, assigned_to, reporter)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('project', 'General'),
        data.get('summary', 'Untitled Bug'),
        data.get('description', ''),
        data.get('steps', ''),
        data.get('status', 'New'),
        data.get('severity', 'Minor'),
        data.get('priority', 'Normal'),
        data.get('category', 'General'),
        data.get('reproducibility', 'Always'),
        data.get('platform', 'Web'),
        data.get('assigned_to', 'Unassigned'),
        data.get('reporter', 'Admin')
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({'status': 'success', 'id': new_id}), 201

@app.route('/api/tickets/<int:ticket_id>', methods=['PUT'])
def update_ticket(ticket_id):
    data = request.json or {}
    conn = get_db()
    conn.execute('''
        UPDATE tickets 
        SET status = coalesce(?, status), 
            severity = coalesce(?, severity), 
            priority = coalesce(?, priority), 
            assigned_to = coalesce(?, assigned_to), 
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (
        data.get('status'),
        data.get('severity'),
        data.get('priority'),
        data.get('assigned_to'),
        ticket_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'status': 'updated'})

@app.route('/api/tickets/<int:ticket_id>/comments', methods=['POST'])
def add_comment(ticket_id):
    data = request.json or {}
    conn = get_db()
    conn.execute('''
        INSERT INTO comments (ticket_id, author, text, is_private)
        VALUES (?, ?, ?, ?)
    ''', (
        ticket_id,
        data.get('author', 'Developer'),
        data.get('text', ''),
        1 if data.get('is_private') else 0
    ))
    conn.execute('UPDATE tickets SET updated_at = CURRENT_TIMESTAMP WHERE id = ?', (ticket_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'comment added'})

@app.route('/api/tickets/<int:ticket_id>', methods=['DELETE'])
def delete_ticket(ticket_id):
    conn = get_db()
    conn.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
