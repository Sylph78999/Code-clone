from flask import Flask, render_template, request, url_for
import sqlite3, os, requests
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ESP32_IP = "http://192.168.254.4"  # <-- Replace with your actual ESP32 IP

# ========= Camera Trigger Flag =========
camera_trigger = False

# ========================
# DATABASE INITIALIZATION
# ========================
def init_db():
    with sqlite3.connect("feeder.db") as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source TEXT,
            weight INTEGER,
            image_path TEXT
        )''')
        conn.commit()

init_db()

# ================
# ROUTES
# ================
@app.route('/')
def home():
    conn = sqlite3.connect("feeder.db")
    c = conn.cursor()
    c.execute("SELECT weight, timestamp FROM logs ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
    conn.close()
    
    if result:
        current_weight = result[0]
        last_updated = result[1]
    else:
        current_weight = "No data"
        last_updated = "N/A"
    
    return render_template('index.html', weight=current_weight, last_updated=last_updated)

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect("feeder.db")
    c = conn.cursor()
    c.execute("SELECT * FROM logs ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return render_template('dashboard.html', logs=rows)

@app.route('/log_data', methods=['POST'])
def log_data():
    weight = request.form.get('weight')
    source = request.form.get('source', 'ESP32')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = sqlite3.connect("feeder.db")
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, source, weight) VALUES (?, ?, ?)", 
              (timestamp, source, weight))
    conn.commit()
    conn.close()
    
    return "Logged", 200

@app.route('/upload_image', methods=['POST'])
def upload_image():
    image_data = request.data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}.jpg"
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    
    with open(image_path, 'wb') as f:
        f.write(image_data)
    
    conn = sqlite3.connect("feeder.db")
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, source, weight, image_path) VALUES (?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'ESP32-CAM', 0, image_path))
    conn.commit()
    conn.close()
    
    return "Image Uploaded", 200

@app.route('/trigger_feed', methods=['POST'])
def trigger_feed():
    try:
        r = requests.get(f"{ESP32_IP}/trigger_servo", timeout=6)
        success = r.status_code == 200
        return f"Servo_triggered: {success}"
    except Exception as e:
        return f"error: {str(e)}"

# ======= CAMERA TRIGGER ENDPOINTS =======
@app.route('/trigger_camera', methods=['GET'])
def trigger_camera():
    global camera_trigger
    if camera_trigger:
        camera_trigger = False
        return "true"
    else:
        return "false"

@app.route('/set_trigger', methods=['POST'])
def set_trigger():
    global camera_trigger
    camera_trigger = True
    return "Camera trigger set", 200

# ======= SYSTEM INFO PAGE =======
@app.route('/system-info')
def system_info():
    # Keep the function name as system_info
    info = {
        "ESP32_IP": ESP32_IP,
        "Upload_Folder": UPLOAD_FOLDER,
        "Database": os.path.abspath("feeder.db"),
        "Last_Updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return render_template("system-info.html", info=info)

@app.route('/test')
def test():
    return "testing route is working!"

# ========= Run Server =========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)