import sqlite3
import os
from datetime import datetime

# Database file path
DB_PATH = 'feeder.db'

def create_database():
    """
    Creates the complete database schema for the Animal Shelter Feeding System
    WITH DYNAMIC IP MANAGEMENT - No need for separate IP database!
    """
    # Remove existing database if it exists
    if os.path.exists(DB_PATH):
        print(f"⚠️ Removing existing database: {DB_PATH}")
        os.remove(DB_PATH)

    # Create new database connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🔨 Creating database tables...")

    # ============================================
    # TABLE 1: FEEDERS/MODULES (WITH DYNAMIC IP STORAGE)
    # Stores information about each feeding module
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feeders (
        feeder_id INTEGER PRIMARY KEY AUTOINCREMENT,
        feeder_name TEXT NOT NULL DEFAULT 'Module 1',
        esp32_ip TEXT NOT NULL,
        esp32_port INTEGER DEFAULT 80,
        esp_cam_ip TEXT,
        esp_cam_port INTEGER DEFAULT 80,
        location TEXT DEFAULT 'Main Area',
        max_capacity_g INTEGER DEFAULT 5000,
        current_weight_g REAL DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        is_online BOOLEAN DEFAULT 0,
        last_online TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_offline TIMESTAMP,
        wifi_strength INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    print("✓ Created table: feeders (with IP management)")

    # ============================================
    # TABLE 2: IP CONFIGURATION HISTORY
    # Tracks IP changes for troubleshooting
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ip_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        feeder_id INTEGER NOT NULL,
        old_esp32_ip TEXT,
        new_esp32_ip TEXT,
        old_esp_cam_ip TEXT,
        new_esp_cam_ip TEXT,
        changed_by TEXT DEFAULT 'System',
        change_reason TEXT,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id)
    )
    ''')
    print("✓ Created table: ip_history")

    # ============================================
    # TABLE 3: FEEDING LOGS
    # Records all feeding events and activities
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feeder_id INTEGER DEFAULT 1,
        feeding_id TEXT UNIQUE,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source TEXT NOT NULL,
        weight INTEGER DEFAULT 0,
        amount INTEGER DEFAULT 0,
        event_type TEXT NOT NULL,
        image_path TEXT,
        duration_ms INTEGER,
        initial_weight REAL,
        final_weight REAL,
        weight_decrease REAL,
        actual_dispensed REAL,
        target_weight REAL,
        notes TEXT,
        FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id)
    )
    ''')
    print("✓ Created table: logs")

    # ============================================
    # TABLE 4: DAILY STATISTICS
    # Aggregated daily feeding statistics
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feeder_id INTEGER DEFAULT 1,
        date TEXT NOT NULL,
        total_feedings INTEGER DEFAULT 0,
        total_dispensed_g REAL DEFAULT 0,
        manual_feedings INTEGER DEFAULT 0,
        scheduled_feedings INTEGER DEFAULT 0,
        button_feedings INTEGER DEFAULT 0,
        failed_feedings INTEGER DEFAULT 0,
        average_duration_ms INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(feeder_id, date),
        FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id)
    )
    ''')
    print("✓ Created table: daily_stats")

    # ============================================
    # TABLE 5: FEEDING SCHEDULES
    # Automated feeding schedules
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS feeding_schedules (
        schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
        feeder_id INTEGER DEFAULT 1,
        schedule_name TEXT,
        hour INTEGER NOT NULL,
        minute INTEGER NOT NULL,
        amount_g REAL NOT NULL,
        days_of_week TEXT DEFAULT '0,1,2,3,4,5,6',
        is_enabled BOOLEAN DEFAULT 1,
        last_triggered TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id)
    )
    ''')
    print("✓ Created table: feeding_schedules")

    # ============================================
    # TABLE 6: SYSTEM SETTINGS
    # Global system configuration
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_settings (
        setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE NOT NULL,
        setting_value TEXT NOT NULL,
        setting_type TEXT DEFAULT 'string',
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    print("✓ Created table: system_settings")

    # ============================================
    # TABLE 7: NOTIFICATIONS
    # System notifications and alerts
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        feeder_id INTEGER DEFAULT 1,
        notification_type TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        severity TEXT DEFAULT 'info',
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (feeder_id) REFERENCES feeders(feeder_id)
    )
    ''')
    print("✓ Created table: notifications")

    # ============================================
    # TABLE 8: IMAGES
    # Photo captures from ESP32-CAM
    # ============================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS images (
        image_id INTEGER PRIMARY KEY AUTOINCREMENT,
        feeding_id TEXT,
        log_id INTEGER,
        image_path TEXT NOT NULL,
        capture_type INTEGER DEFAULT 1,
        file_size INTEGER,
        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (log_id) REFERENCES logs(id),
        FOREIGN KEY (feeding_id) REFERENCES logs(feeding_id)
    )
    ''')
    print("✓ Created table: images")

    # ============================================
    # CREATE INDEXES FOR PERFORMANCE
    # ============================================
    print("\n🔍 Creating indexes...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_feeder ON logs(feeder_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_feeding_id ON logs(feeding_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON daily_stats(date DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON feeding_schedules(is_enabled)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_images_feeding ON images(feeding_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_feeders_active ON feeders(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ip_history_feeder ON ip_history(feeder_id)')
    print("✓ Created performance indexes")

    # ============================================
    # INSERT DEFAULT DATA
    # ============================================
    print("\n📝 Inserting default data...")

    # Default feeder module with your current IPs
    cursor.execute('''
    INSERT INTO feeders (feeder_name, esp32_ip, esp32_port, esp_cam_ip, esp_cam_port, location, max_capacity_g, is_online)
    VALUES ('Module 1', '192.168.254.4', 80, '192.168.254.2', 80, 5000, 1)
    ''')

    # Default system settings including RPI server IP
    default_settings = [
        ('rpi_server_ip', '192.168.254.5', 'string', 'Raspberry Pi Flask server IP address'),
        ('rpi_server_port', '8080', 'integer', 'Flask server port'),
        ('dispense_amount', '50', 'integer', 'Default dispensing amount in grams'),
        ('buzzer_threshold', '30', 'integer', 'Low food warning threshold in grams'),
        ('camera_delay_first', '5000', 'integer', 'First camera capture delay in ms'),
        ('camera_delay_second', '30000', 'integer', 'Second camera capture delay in ms'),
        ('max_dispense_timeout', '5000', 'integer', 'Maximum dispensing timeout in ms'),
        ('auto_schedule_enabled', '1', 'boolean', 'Enable automatic scheduling'),
        ('notification_enabled', '1', 'boolean', 'Enable system notifications'),
        ('maintenance_mode', '0', 'boolean', 'System maintenance mode'),
        ('wifi_ssid', 'animal_shelter', 'string', 'WiFi network name'),
        ('ip_check_interval', '60', 'integer', 'IP connectivity check interval in seconds')
    ]

    cursor.executemany('''
    INSERT INTO system_settings (setting_key, setting_value, setting_type, description)
    VALUES (?, ?, ?, ?)
    ''', default_settings)

    # Default feeding schedules (from your ESP32 code)
    default_schedules = [
        ('Morning Feed', 8, 0, 100.0, '0,1,2,3,4,5,6', 1),
        ('Afternoon Feed', 12, 0, 150.0, '0,1,2,3,4,5,6', 1),
        ('Evening Feed', 17, 0, 200.0, '0,1,2,3,4,5,6', 1)
    ]

    cursor.executemany('''
    INSERT INTO feeding_schedules (schedule_name, hour, minute, amount_g, days_of_week, is_enabled)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', default_schedules)

    # Welcome notification
    cursor.execute('''
    INSERT INTO notifications (notification_type, title, message, severity)
    VALUES ('system', 'System Initialized', 'Animal Shelter Feeding System database created successfully! All IPs are stored in one place.', 'info')
    ''')

    # Commit changes
    conn.commit()

    # ============================================
    # VERIFY DATABASE CREATION
    # ============================================
    print("\n📊 Database Statistics:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f"✓ Total tables created: {len(tables)}")

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  - {table[0]}: {count} records")

    # Show IP configuration
    print("\n🌐 Current IP Configuration:")
    cursor.execute('''
    SELECT feeder_name, esp32_ip, esp32_port, esp_cam_ip, esp_cam_port
    FROM feeders WHERE feeder_id = 1
    ''')
    feeder = cursor.fetchone()
    print(f"  ESP32 Main: http://{feeder[1]}:{feeder[2]}")
    print(f"  ESP32-CAM: http://{feeder[3]}:{feeder[4]}")

    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'rpi_server_ip'")
    rpi_ip = cursor.fetchone()[0]
    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'rpi_server_port'")
    rpi_port = cursor.fetchone()[0]
    print(f"  RPI Server: http://{rpi_ip}:{rpi_port}")

    # Close connection
    conn.close()

    print(f"\n✅ Database '{DB_PATH}' created successfully!")
    print(f"📍 Location: {os.path.abspath(DB_PATH)}")
    print("\n" + "="*50)
    print("✨ ALL IPs ARE NOW STORED IN ONE DATABASE! ✨")
    print("No need for separate IP database files!")
    print("="*50)

def create_helper_functions_file():
    """
    Creates a Python file with helper functions for IP management
    """
    helper_code = '''"""
IP Management Helper Functions
For Animal Shelter Feeding System
"""
import sqlite3
from datetime import datetime

DB_PATH = 'feeder.db'

def get_feeder_ips(feeder_id=1):
    """Get IP addresses for a specific feeder"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    cursor.execute("""
    SELECT esp32_ip, esp32_port, esp_cam_ip, esp_cam_port
    FROM feeders
    WHERE feeder_id = ?
    """, (feeder_id,))
   
    result = cursor.fetchone()
    conn.close()
   
    if result:
        return {
            'esp32_ip': result[0],
            'esp32_port': result[1],
            'esp_cam_ip': result[2],
            'esp_cam_port': result[3],
            'esp32_url': f"http://{result[0]}:{result[1]}",
            'esp_cam_url': f"http://{result[2]}:{result[3]}"
        }
    return None

def update_feeder_ip(feeder_id, esp32_ip=None, esp_cam_ip=None, changed_by='Admin', reason='Manual Update'):
    """Update IP addresses for a feeder and log the change"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    # Get old IPs first
    cursor.execute('SELECT esp32_ip, esp_cam_ip FROM feeders WHERE feeder_id = ?', (feeder_id,))
    old_ips = cursor.fetchone()
   
    # Update IPs
    if esp32_ip:
        cursor.execute('UPDATE feeders SET esp32_ip = ?, updated_at = ? WHERE feeder_id = ?',
                      (esp32_ip, datetime.now(), feeder_id))
   
    if esp_cam_ip:
        cursor.execute('UPDATE feeders SET esp_cam_ip = ?, updated_at = ? WHERE feeder_id = ?',
                      (esp_cam_ip, datetime.now(), feeder_id))
   
    # Log IP change
    cursor.execute("""
    INSERT INTO ip_history (feeder_id, old_esp32_ip, new_esp32_ip, old_esp_cam_ip, new_esp_cam_ip, changed_by, change_reason)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (feeder_id, old_ips[0] if old_ips else None, esp32_ip,
          old_ips[1] if old_ips else None, esp_cam_ip, changed_by, reason))
   
    conn.commit()
    conn.close()
   
    print(f"✓ IP addresses updated for Feeder {feeder_id}")
    if esp32_ip:
        print(f"  ESP32: {esp32_ip}")
    if esp_cam_ip:
        print(f"  ESP-CAM: {esp_cam_ip}")

def get_rpi_server_url():
    """Get RPI server URL from settings"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'rpi_server_ip'")
    ip = cursor.fetchone()[0]
   
    cursor.execute("SELECT setting_value FROM system_settings WHERE setting_key = 'rpi_server_port'")
    port = cursor.fetchone()[0]
   
    conn.close()
    return f"http://{ip}:{port}"

def update_rpi_server_ip(new_ip, new_port=8080):
    """Update RPI server IP in settings"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    cursor.execute("UPDATE system_settings SET setting_value = ? WHERE setting_key = 'rpi_server_ip'", (new_ip,))
    cursor.execute("UPDATE system_settings SET setting_value = ? WHERE setting_key = 'rpi_server_port'", (str(new_port),))
   
    conn.commit()
    conn.close()
   
    print(f"✓ RPI Server updated: http://{new_ip}:{new_port}")

def list_all_ips():
    """Display all IPs in the system"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    print("\\n" + "="*60)
    print("CURRENT SYSTEM IP CONFIGURATION")
    print("="*60)
   
    # Get RPI Server
    rpi_url = get_rpi_server_url()
    print(f"\\n🖥️  RPI Server: {rpi_url}")
   
    # Get all feeders
    cursor.execute('SELECT feeder_id, feeder_name, esp32_ip, esp32_port, esp_cam_ip, esp_cam_port, is_online FROM feeders')
    feeders = cursor.fetchall()
   
    print(f"\\n📡 Feeder Modules ({len(feeders)}):")
    for feeder in feeders:
        status = "🟢 Online" if feeder[6] else "🔴 Offline"
        print(f"\\n  {feeder[1]} (ID: {feeder[0]}) - {status}")
        print(f"    ESP32 Main: http://{feeder[2]}:{feeder[3]}")
        print(f"    ESP32-CAM:  http://{feeder[4]}:{feeder[5]}")
   
    conn.close()
    print("\\n" + "="*60 + "\\n")

def add_new_feeder(name, esp32_ip, esp_cam_ip, location="Main Area"):
    """Add a new feeder module to the system"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
   
    cursor.execute("""
    INSERT INTO feeders (feeder_name, esp32_ip, esp_cam_ip, location)
    VALUES (?, ?, ?, ?)
    """, (name, esp32_ip, esp_cam_ip, location))
   
    feeder_id = cursor.lastrowid
    conn.commit()
    conn.close()
   
    print(f"✓ New feeder added: {name} (ID: {feeder_id})")
    print(f"  ESP32: http://{esp32_ip}")
    print(f"  ESP-CAM: http://{esp_cam_ip}")
   
    return feeder_id

# Example usage:
if __name__ == "__main__":
    # Display all IPs
    list_all_ips()
   
    # Example: Update ESP32 IP
    # update_feeder_ip(1, esp32_ip='192.168.254.10', reason='Router changed IP')
   
    # Example: Update RPI Server IP
    # update_rpi_server_ip('192.168.254.100')
   
    # Example: Add new feeder
    # add_new_feeder('Module 2', '192.168.254.5', '192.168.254.6', 'North Wing')
'''

    with open('ip_management.py', 'w') as f:
        f.write(helper_code)
   
    print("\n✅ Created helper file: ip_management.py")
    print("   Use this for easy IP management!")

def verify_database():
    """
    Verifies database integrity and displays schema
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n" + "="*50)
    print("DATABASE SCHEMA VERIFICATION")
    print("="*50 + "\n")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        print(f"\n📋 TABLE: {table_name}")
        print("-" * 50)
       
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
       
        for col in columns:
            pk = "PRIMARY KEY" if col[5] else ""
            print(f"  {col[1]:20} {col[2]:15} {pk}")

    conn.close()
    print("\n" + "="*50)
    print("✅ Database verification complete!")
    print("="*50)

# ============================================
# MAIN EXECUTION
# ============================================
if __name__ == "__main__":
    print("\n" + "="*60)
    print("ANIMAL SHELTER FEEDING SYSTEM")
    print("Database Setup Script - WITH INTEGRATED IP MANAGEMENT")
    print("="*60 + "\n")

    try:
        # Create database
        create_database()
       
        # Create helper functions file
        create_helper_functions_file()
       
        # Verify creation
        print("\nVerifying database structure...")
        verify_database()
       
        print("\n" + "="*60)
        print("✅ SETUP COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\n💡 What you got:")
        print("  1. ✅ feeder.db - Main database with IP storage")
        print("  2. ✅ ip_management.py - Helper functions for IP changes")
        print("\n📝 Next steps:")
        print("  1. Copy 'feeder.db' to your Flask app folder")
        print("  2. Update app.py to read IPs from database")
        print("  3. Run: python ip_management.py (to view/update IPs)")
        print("  4. Start your Flask app: python app.py")
        print("\n🎯 Benefits:")
        print("  ✓ All IPs in ONE place")
        print("  ✓ Easy to update without code changes")
        print("  ✓ IP change history tracking")
        print("  ✓ Support for multiple feeders")
        print("="*60 + "\n")
       
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()
