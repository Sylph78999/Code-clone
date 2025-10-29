from flask import Flask, render_template, request, jsonify, url_for
import sqlite3, os, requests
from datetime import datetime, date
import json
from contextlib import contextmanager
from ip_management import get_feeder_ips, get_rpi_server_url

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================================
# Dynamic IP Loading from feeder.db
# ==========================================================

# Database path (auto-detects feeder.db in same folder)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feeder.db")

try:
    # Get ESP32 and ESP32-CAM IPs
    feeder_ips = get_feeder_ips(1)  # 1 = first feeder module
    ESP32_IP = feeder_ips['esp32_ip']
    ESP_CAM_IP = feeder_ips['esp_cam_ip']

    # Get Raspberry Pi server URL
    RPI_SERVER_URL = get_rpi_server_url()

    print(f"[INFO] Loaded IPs from database:")
    print(f"  ESP32 Main → {ESP32_IP}")
    print(f"  ESP32-CAM  → {ESP_CAM_IP}")
    print(f"  RPi Server → {RPI_SERVER_URL}")

except Exception as e:
    print(f"[WARN] Could not load IPs from database: {e}")
    # Fallback IPs (useful if DB not accessible)
    ESP32_IP = "http://192.168.254.4:80"
    ESP_CAM_IP = "http://192.168.254.2:80"
    RPI_SERVER_URL = "http://192.168.254.5:8080"

# Context manager for database connections
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# DATABASE INITIALIZATION
def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feeder_id INTEGER DEFAULT 1,
            timestamp TEXT,
            source TEXT,
            weight INTEGER,
            amount INTEGER,
            event_type TEXT,
            image_path TEXT,
            feed_type TEXT,
            feeding_id TEXT,
            FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS daily_stats (
            date TEXT PRIMARY KEY,
            total_feedings INTEGER DEFAULT 0
        )''')
        
        # ADD THIS NEW TABLE
        c.execute('''CREATE TABLE IF NOT EXISTS feeding_schedules (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            feeder_id INTEGER DEFAULT 1,
            schedule_name TEXT,
            hour INTEGER,
            minute INTEGER,
            amount_g INTEGER,
            days_of_week TEXT,
            is_enabled INTEGER DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id)
        )''')
        
init_db()

# ============================================
# MAIN ROUTES - UPDATED STRUCTURE
# ============================================

@app.route('/')
def index():
    """Main page - Feeder modules management"""
    return render_template('index.html')

@app.route('/home')
def home():
    """Home page - About Animal Haven (formerly index)"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT weight, timestamp FROM logs ORDER BY id DESC LIMIT 1")
            result = c.fetchone()
       
        if result:
            current_weight = result[0]
            last_updated = result[1]
        else:
            current_weight = "No data"
            last_updated = "N/A"
       
        return render_template('home.html', weight=current_weight, last_updated=last_updated)
    except Exception as e:
        print(f"Error in home route: {e}")
        return render_template('home.html', weight="Error", last_updated="N/A")

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/manual-dashboard')
def manual_dashboard():
    return render_template('manual-dashboard.html')

@app.route('/automatic-dashboard')
def automatic_dashboard():
    return render_template('automatic-dashboard.html')

@app.route('/logs')
def logs():
    return render_template('logs.html')

@app.route('/system-info')
def system_info():
    info = {
        "ESP32_IP": ESP32_IP,
        "Upload_Folder": UPLOAD_FOLDER,
        "Database": os.path.abspath(DB_PATH),
        "Last_Updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return render_template("system-info.html", info=info)

# ============================================
# FEEDER MANAGEMENT ROUTES
# ============================================

@app.route('/get_feeders')
def get_feeders():
    """Get all feeder modules from database"""
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT
                    feeder_id,
                    feeder_name,
                    esp32_ip,
                    esp32_port,
                    esp_cam_ip,
                    esp_cam_port,
                    location,
                    max_capacity_g,
                    current_weight_g,
                    is_active,
                    is_online,
                    last_online,
                    wifi_strength,
                    created_at
                FROM feeders
                WHERE is_active = 1
                ORDER BY feeder_id ASC
            """)
           
            feeders = c.fetchall()
           
            feeders_list = []
            for feeder in feeders:
                # Check if feeder is actually online by pinging it
                is_online = check_feeder_online(feeder[2], feeder[3])
               
                # Update online status in database
                if is_online != feeder[10]:
                    update_feeder_status(feeder[0], is_online)
               
                feeders_list.append({
                    'id': feeder[0],
                    'name': feeder[1],
                    'ip_address': f"{feeder[2]}:{feeder[3]}",
                    'esp32_ip': feeder[2],
                    'esp32_port': feeder[3],
                    'esp_cam_ip': feeder[4],
                    'esp_cam_port': feeder[5],
                    'location': feeder[6],
                    'max_capacity_g': feeder[7],
                    'current_weight_g': feeder[8],
                    'is_active': feeder[9],
                    'is_online': is_online,
                    'last_online': feeder[11],
                    'wifi_strength': feeder[12],
                    'created_at': feeder[13]
                })
           
            print(f"✓ Loaded {len(feeders_list)} feeder(s)")
            return jsonify(feeders_list)
           
    except Exception as e:
        print(f"Error getting feeders: {e}")
        return jsonify([]), 500

@app.route('/add_feeder', methods=['POST'])
def add_feeder():
    """Add a new feeder module"""
    try:
        data = request.get_json()
        name = data.get('name')
        ip_address = data.get('ip_address')
       
        if not name or not ip_address:
            return jsonify({'error': 'Missing required fields'}), 400
       
        # Parse IP and port (default port 80)
        if ':' in ip_address:
            ip, port = ip_address.split(':')
            port = int(port)
        else:
            ip = ip_address
            port = 80
       
        # Validate IP format
        parts = ip.split('.')
        if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
            return jsonify({'error': 'Invalid IP address format'}), 400
       
        with get_db() as conn:
            c = conn.cursor()
           
            # Check if IP already exists
            c.execute("SELECT feeder_id FROM feeders WHERE esp32_ip = ? AND is_active = 1", (ip,))
            if c.fetchone():
                return jsonify({'error': 'A feeder with this IP already exists'}), 400
           
            # Insert new feeder
            c.execute("""
                INSERT INTO feeders (
                    feeder_name,
                    esp32_ip,
                    esp32_port,
                    location,
                    max_capacity_g,
                    is_active,
                    is_online,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, 1, 0, ?)
            """, (
                name,
                ip,
                port,
                data.get('location', 'Main Area'),
                data.get('max_capacity_g', 5000),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
           
            feeder_id = c.lastrowid
           
            # Log the addition
            print(f"✓ New feeder added: {name} ({ip}:{port}) - ID: {feeder_id}")
           
            return jsonify({
                'success': True,
                'feeder_id': feeder_id,
                'message': f'Feeder "{name}" added successfully'
            }), 200
           
    except Exception as e:
        print(f"Error adding feeder: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_feeder/<int:feeder_id>', methods=['DELETE'])
def delete_feeder(feeder_id):
    """Delete a feeder module (soft delete)"""
    try:
        with get_db() as conn:
            c = conn.cursor()
           
            # Get feeder info before deleting
            c.execute("SELECT feeder_name FROM feeders WHERE feeder_id = ?", (feeder_id,))
            feeder = c.fetchone()
           
            if not feeder:
                return jsonify({'error': 'Feeder not found'}), 404
           
            # Soft delete (set is_active to 0)
            c.execute("""
                UPDATE feeders
                SET is_active = 0, updated_at = ?
                WHERE feeder_id = ?
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), feeder_id))
           
            print(f"✓ Feeder deleted: {feeder[0]} (ID: {feeder_id})")
           
            return jsonify({
                'success': True,
                'message': f'Feeder "{feeder[0]}" deleted successfully'
            }), 200
           
    except Exception as e:
        print(f"Error deleting feeder: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/trigger_feeding/<int:feeder_id>', methods=['POST'])
def trigger_feeding_by_feeder(feeder_id):
    """Trigger feeding on a specific feeder module"""
    try:
        # Get feeder details
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT feeder_name, esp32_ip, esp32_port, is_online
                FROM feeders
                WHERE feeder_id = ? AND is_active = 1
            """, (feeder_id,))
           
            feeder = c.fetchone()
           
            if not feeder:
                return jsonify({'error': 'Feeder not found or inactive'}), 404
           
            feeder_name = feeder[0]
            feeder_ip = feeder[1]
            feeder_port = feeder[2]
            is_online = feeder[3]
       
        # Get feeding amount (default 50g, can be customized)
        amount = request.form.get('amount', 50)
       
        # Construct ESP32 URL
        esp32_url = f"http://{feeder_ip}:{feeder_port}/trigger_dispensing"
       
        print(f"🎯 Triggering feeding on {feeder_name} ({feeder_ip}:{feeder_port})")
       
        # Send command to ESP32
        try:
            response = requests.post(
                esp32_url,
                data=f"amount={amount}",
                timeout=5
            )
           
            if response.status_code == 200:
                # Log the feeding event
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO logs (
                            feeder_id,
                            timestamp,
                            source,
                            amount,
                            event_type
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        feeder_id,
                        timestamp,
                        f'Manual - {feeder_name}',
                        amount,
                        'MANUAL_FEED'
                    ))
                   
                    # Update daily stats
                    today = date.today().isoformat()
                    c.execute("""
                        INSERT OR REPLACE INTO daily_stats (feeder_id, date, total_feedings)
                        VALUES (
                            ?,
                            ?,
                            COALESCE((SELECT total_feedings FROM daily_stats WHERE feeder_id = ? AND date = ?), 0) + 1
                        )
                    """, (feeder_id, today, feeder_id, today))
               
                print(f"✓ Feeding triggered successfully on {feeder_name}")
               
                return jsonify({
                    'success': True,
                    'message': f'Feeding triggered on {feeder_name}',
                    'feeder_id': feeder_id,
                    'amount': amount
                }), 200
            else:
                raise Exception(f"ESP32 returned status code {response.status_code}")
               
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to connect to feeder {feeder_name}: {e}")
           
            # Update feeder status to offline
            update_feeder_status(feeder_id, False)
           
            return jsonify({
                'error': f'Cannot connect to feeder {feeder_name}. It may be offline.',
                'details': str(e)
            }), 503
           
    except Exception as e:
        print(f"Error triggering feeding: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================
# HELPER FUNCTIONS
# ============================================

def check_feeder_online(ip, port, timeout=2):
    """Check if a feeder is online by pinging its status endpoint"""
    try:
        response = requests.get(
            f"http://{ip}:{port}/get_status",
            timeout=timeout
        )
        return response.status_code == 200
    except:
        return False

def update_feeder_status(feeder_id, is_online):
    """Update the online status of a feeder in the database"""
    try:
        with get_db() as conn:
            c = conn.cursor()
           
            if is_online:
                c.execute("""
                    UPDATE feeders
                    SET is_online = 1,
                        last_online = ?,
                        updated_at = ?
                    WHERE feeder_id = ?
                """, (
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    feeder_id
                ))
            else:
                c.execute("""
                    UPDATE feeders
                    SET is_online = 0,
                        last_offline = ?,
                        updated_at = ?
                    WHERE feeder_id = ?
                """, (
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    feeder_id
                ))
               
    except Exception as e:
        print(f"Error updating feeder status: {e}")

# ========= DATA API ENDPOINTS =========

@app.route('/get_esp32_status')
def get_esp32_status():
    try:
        response = requests.get(f"{ESP32_IP}/get_status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'weight': data.get('weight', 0),
                'online': True,
                'dispensing_active': data.get('dispensing_active', False),
                'target_weight': data.get('target_weight', 0),
                'feeding_id': data.get('feeding_id', '')
            })
    except:
        pass
   
    return jsonify({'weight': 0, 'online': False, 'dispensing_active': False})

@app.route('/get_feeding_logs')
def get_feeding_logs():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("""SELECT id, timestamp, source, weight, amount, 
                        event_type, image_path, feed_type, feeding_id 
                        FROM logs 
                        ORDER BY timestamp DESC LIMIT 100""")
            logs = c.fetchall()

            logs_list = []
            for log in logs:
                logs_list.append({
                    'id': log[0],
                    'timestamp': log[1],
                    'source': log[2],
                    'weight': log[3],
                    'amount': log[4],
                    'event_type': log[5],
                    'image_path': log[6],
                    'feed_type': log[7] if len(log) > 7 else 'Manual',
                    'feeding_id': log[8] if len(log) > 8 else ''
                })

            return jsonify(logs_list)
    except Exception as e:
        print(f"Error getting feeding logs: {e}")
        return jsonify([])


@app.route('/get_daily_stats')
def get_daily_stats():
    try:
        today = date.today().isoformat()
        with get_db() as conn:
            c = conn.cursor()
           
            # Get today's total feedings
            c.execute("SELECT total_feedings FROM daily_stats WHERE date = ?", (today,))
            result = c.fetchone()
            total_feedings = result[0] if result else 0
           
            # Get total food dispensed today
            c.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM logs
                WHERE DATE(timestamp) = DATE('now')
                AND event_type IN ('MANUAL_FEED', 'SCHEDULED_FEED', 'BUTTON_FEED')
            """)
            total_dispensed = c.fetchone()[0]
       
        return jsonify({
            'total_feedings': total_feedings,
            'total_dispensed': total_dispensed
        })
    except Exception as e:
        print(f"Error getting daily stats: {e}")
        return jsonify({'total_feedings': 0, 'total_dispensed': 0})

@app.route('/log_data', methods=['POST'])
def log_data():
    try:
        weight = request.form.get('weight')
        source = request.form.get('source', 'ESP32')
        amount = request.form.get('amount', 0)
        event_type = request.form.get('event', 'UNKNOWN')
        feed_type = request.form.get('feed_type', 'Manual')  
        feeding_id = request.form.get('feeding_id', '')  
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with get_db() as conn:
            c = conn.cursor()
            # Insert log with feed_type and feeding_id
            c.execute("""INSERT INTO logs 
                        (timestamp, source, weight, amount, event_type, feed_type, feeding_id) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (timestamp, source, weight, amount, event_type, feed_type, feeding_id))

            # Update daily stats if it's a feeding event
            if event_type in ['MANUAL_FEED', 'SCHEDULED_FEED', 'BUTTON_FEED']:
                today = date.today().isoformat()
                c.execute("""
                    INSERT OR REPLACE INTO daily_stats (date, total_feedings)
                    VALUES (?, COALESCE((SELECT total_feedings FROM daily_stats WHERE date = ?), 0) + 1)
                """, (today, today))
       
        return "Logged", 200
    except Exception as e:
        print(f"Error logging data: {e}")
        return "Error logging data", 500

@app.route('/trigger_feeding', methods=['POST'])
def trigger_feeding():
    source = request.form.get('source', 'Dashboard')
    amount = request.form.get('amount', 50)
   
    try:
        # Trigger ESP32 feeding
        response = requests.post(f"{ESP32_IP}/trigger_dispensing",
                               data=f"amount={amount}", timeout=5)
       
        if response.status_code == 200:
            # Log the feeding event
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with get_db() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO logs (timestamp, source, weight, amount, event_type) VALUES (?, ?, ?, ?, ?)",
                          (timestamp, source, 0, amount, 'MANUAL_FEED'))
               
                # Update daily stats
                today = date.today().isoformat()
                c.execute("""
                    INSERT OR REPLACE INTO daily_stats (date, total_feedings)
                    VALUES (?, COALESCE((SELECT total_feedings FROM daily_stats WHERE date = ?), 0) + 1)
                """, (today, today))
           
            # Trigger camera capture after 5 seconds
            def trigger_camera_delayed():
                import time
                time.sleep(5)
                try:
                    requests.get(f"{ESP_CAM_IP}/trigger_capture", timeout=3)
                except:
                    pass
           
            import threading
            threading.Thread(target=trigger_camera_delayed, daemon=True).start()
           
            return "Feeding triggered", 200
    except Exception as e:
        print(f"Error triggering feeding: {e}")
        return f"Error: {str(e)}", 500
   
    return "Failed to trigger feeding", 500

@app.route('/set_schedule', methods=['POST'])
def set_schedule():
    """Save and send schedule to ESP32"""
    try:
        data = request.get_json()
        feeder_id = data.get('feeder_id', 1)
        grams = data.get('grams')
        time_str = data.get('time')
        days = data.get('days', [])
        
        # Parse time (format: "HH:MM AM/PM")
        import re
        match = re.match(r'(\d+):(\d+)\s*(AM|PM)', time_str)
        if not match:
            return jsonify({'error': 'Invalid time format'}), 400
        
        hour = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3)
        
        # Convert to 24-hour format
        if period == 'PM' and hour != 12:
            hour += 12
        elif period == 'AM' and hour == 12:
            hour = 0
        
        # Get ESP32 IP for this feeder
        with get_db() as conn:
            c = conn.cursor()
            c.execute("SELECT esp32_ip, esp32_port FROM feeders WHERE feeder_id = ?", (feeder_id,))
            feeder = c.fetchone()
            
            if not feeder:
                return jsonify({'error': 'Feeder not found'}), 404
            
            esp32_ip = feeder[0]
            esp32_port = feeder[1]
        
        # Send schedule to ESP32
        try:
            esp32_url = f"http://{esp32_ip}:{esp32_port}/set_schedule"
            params = {
                'index': 0,  # Using first schedule slot
                'hour': hour,
                'minute': minute,
                'amount': grams,
                'enabled': 1
            }
            
            response = requests.get(esp32_url, params=params, timeout=5)
            
            if response.status_code == 200:
                print(f"✓ Schedule sent to ESP32: {hour}:{minute:02d} - {grams}g")
                
                # Save to database for reference
                with get_db() as conn:
                    c = conn.cursor()
                    c.execute("""INSERT INTO feeding_schedules 
                                (feeder_id, schedule_name, hour, minute, amount_g, days_of_week, is_enabled)
                                VALUES (?, ?, ?, ?, ?, ?, 1)""",
                             (feeder_id, f"Schedule {hour}:{minute:02d}", hour, minute, grams, ','.join(map(str, days))))
                
                return jsonify({
                    'success': True,
                    'message': f'Schedule set successfully: {hour}:{minute:02d} - {grams}g'
                }), 200
            else:
                return jsonify({'error': 'ESP32 returned error'}), 500
                
        except Exception as e:
            print(f"Error sending to ESP32: {e}")
            return jsonify({'error': f'Could not connect to ESP32: {str(e)}'}), 503
        
    except Exception as e:
        print(f"Error setting schedule: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/set_dispense_amount', methods=['POST'])
def set_dispense_amount():
    amount = request.args.get('amount', 50)
    try:
        amount_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dispense_amount.txt')
        with open(amount_file, 'w') as f:
            f.write(str(amount))
        return "Amount set", 200
    except Exception as e:
        print(f"Error setting amount: {e}")
        return "Error setting amount", 500

@app.route('/get_dispense_amount')
def get_dispense_amount():
    try:
        amount_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dispense_amount.txt')
        with open(amount_file, 'r') as f:
            amount = int(f.read().strip())
        return jsonify({'amount': amount})
    except:
        return jsonify({'amount': 50})

@app.route('/delete_log/<int:log_id>', methods=['DELETE'])
def delete_log(log_id):
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM logs WHERE id = ?", (log_id,))
        return "Log deleted", 200
    except Exception as e:
        print(f"Error deleting log: {e}")
        return "Error deleting log", 500

@app.route('/delete_all_logs', methods=['DELETE'])
def delete_all_logs():
    try:
        with get_db() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM logs")
        return "All logs deleted", 200
    except Exception as e:
        print(f"Error deleting all logs: {e}")
        return "Error deleting all logs", 500

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    try:
        image_data = request.data
        feeding_id = request.headers.get('X-Feeding-ID', '')
        capture_type = request.headers.get('X-Capture-Type', '1')
        
        # Create filename with feeding_id
        if feeding_id:
            filename = f"{feeding_id}_capture{capture_type}.jpg"
        else:
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        image_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(image_path, 'wb') as f:
            f.write(image_data)

        # Update log with image path using feeding_id
        with get_db() as conn:
            c = conn.cursor()
            if feeding_id:
                c.execute("UPDATE logs SET image_path = ? WHERE feeding_id = ?", 
                         (f"/static/uploads/{filename}", feeding_id))
            else:
                c.execute("UPDATE logs SET image_path = ? WHERE id = (SELECT MAX(id) FROM logs)", 
                         (f"/static/uploads/{filename}",))

        return "Image uploaded", 200
    except Exception as e:
        print(f"Error uploading photo: {e}")
        return "Error uploading photo", 500
    

@app.route('/trigger_second_capture', methods=['POST'])
def trigger_second_capture():
    def trigger_second_camera():
        import time
        time.sleep(10)
        try:
            requests.get(f"{ESP_CAM_IP}/trigger_capture", timeout=3)
        except:
            pass
   
    import threading
    threading.Thread(target=trigger_second_camera, daemon=True).start()
    return "Second capture triggered", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)