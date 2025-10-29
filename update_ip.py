import sqlite3

conn = sqlite3.connect('feeder.db')
cursor = conn.cursor()

# Update RPI server IP and port
cursor.execute("UPDATE system_settings SET setting_value = '192.168.254.5' WHERE setting_key = 'rpi_server_ip'")
cursor.execute("UPDATE system_settings SET setting_value = '8080' WHERE setting_key = 'rpi_server_port'")

conn.commit()
conn.close()

print("✓ Database updated!")
print("  RPI Server IP: 192.168.254.5:8080")