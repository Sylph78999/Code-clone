"""
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
    
    print("\n" + "="*60)
    print("CURRENT SYSTEM IP CONFIGURATION")
    print("="*60)
    
    # Get RPI Server
    rpi_url = get_rpi_server_url()
    print(f"\n🖥️  RPI Server: {rpi_url}")
    
    # Get all feeders
    cursor.execute('SELECT feeder_id, feeder_name, esp32_ip, esp32_port, esp_cam_ip, esp_cam_port, is_online FROM feeders')
    feeders = cursor.fetchall()
    
    print(f"\n📡 Feeder Modules ({len(feeders)}):")
    for feeder in feeders:
        status = "🟢 Online" if feeder[6] else "🔴 Offline"
        print(f"\n  {feeder[1]} (ID: {feeder[0]}) - {status}")
        print(f"    ESP32 Main: http://{feeder[2]}:{feeder[3]}")
        print(f"    ESP32-CAM:  http://{feeder[4]}:{feeder[5]}")
    
    conn.close()
    print("\n" + "="*60 + "\n")

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


if __name__ == "__main__":
    
    list_all_ips()
    
   