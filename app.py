from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key_needed_for_sessions'  # Required for admin password login
DB_NAME = 'timeclock.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            action TEXT NOT NULL,
            location TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    cursor.execute('PRAGMA table_info(attendance)')
    columns = [column[1] for column in cursor.fetchall()]
    if 'location' not in columns:
        cursor.execute('ALTER TABLE attendance ADD COLUMN location TEXT')
        cursor.execute("UPDATE attendance SET location = 'Unknown' WHERE location IS NULL")

    conn.commit()
    conn.close()

@app.route('/kitchen')
def kitchen_page():
    return render_template('index.html', location='Kitchen')

@app.route('/market')
def market_page():
    return render_template('index.html', location='Market')

@app.route('/api/clock', methods=['POST'])
def clock_action():
    data = request.get_json()
    name = data.get('name', '').strip()
    action = data.get('action')
    location = data.get('location')
    
    if not name or action not in ['Clock In', 'Clock Out'] or location not in ['Kitchen', 'Market']:
        return jsonify({'success': False, 'error': 'Invalid input'}), 400
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO attendance (name, action, location, timestamp) 
        VALUES (?, ?, ?, ?)
    ''', (name, action, location, timestamp))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'timestamp': timestamp})

@app.route('/api/logs/<location>', methods=['GET'])
def get_logs(location):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, action, timestamp FROM attendance 
        WHERE location = ? 
        ORDER BY id DESC LIMIT 50
    ''', (location,))
    rows = cursor.fetchall()
    conn.close()
    #jfajshfj bjs 
    logs = [{'name': r[0], 'action': r[1], 'timestamp': r[2]} for r in rows]
    return jsonify(logs)

# --- ADMIN ROUTES ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'admin123':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Incorrect password'
    return render_template('login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Get all records ordered chronologically to calculate shifts properly
    cursor.execute('SELECT name, action, location, timestamp FROM attendance ORDER BY timestamp ASC')
    rows = cursor.fetchall()
    conn.close()

    # Process logs into paired shifts: Name, Location, Day, Start Time, Finish Time, Total Hours
    sessions_dict = {}  # Key: (name, date, location), Value: {'in': time, 'out': time, 'location': loc}
    report_rows = []

    for row in rows:
        name, action, location, timestamp = row
        dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        date_str = dt.strftime('%Y-%m-%d')

        key = (name, date_str, location)

        if action == 'Clock In':
            # Keep each location separate so Kitchen and Market entries do not overwrite each other
            sessions_dict[key] = {'name': name, 'location': location, 'date': date_str, 'in': dt, 'out': None}
        elif action == 'Clock Out':
            if key in sessions_dict:
                sessions_dict[key]['out'] = dt

    # Build final easy-to-read list
    for key, data in sorted(sessions_dict.items(), reverse=True):
        start_dt = data['in']
        out_dt = data['out']
        
        start_formatted = start_dt.strftime('%H:%M') if start_dt else '-'
        finish_formatted = out_dt.strftime('%H:%M') if out_dt else 'Still Working...'
        
        hours_str = '-'
        if out_dt and start_dt:
            diff = out_dt - start_dt
            total_seconds = diff.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            hours_str = f"{hours}h {minutes}m"

        report_rows.append({
            'name': data['name'],
            'location': data['location'],
            'date': data['date'],
            'start': start_formatted,
            'finish': finish_formatted,
            'hours': hours_str
        })

    return render_template('admin.html', rows=report_rows)



if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

    