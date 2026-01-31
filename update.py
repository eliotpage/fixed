import json
import serial
import time

# Replace with the serial port of your ESP32
SERIAL_PORT = "/dev/cu.SLAB_USBtoUART"
BAUD = 115200

# Load your drawings.json
with open("static/drawings.json") as f:
    drawings = json.load(f)

# Convert to string
json_str = json.dumps(drawings)

# Open serial port
with serial.Serial(SERIAL_PORT, BAUD, timeout=1) as ser:
    time.sleep(2)  # Wait for ESP32 to reset on open
    CHUNK_SIZE = 200  # ESP-NOW/ESP32 safe chunk
    for i in range(0, len(json_str), CHUNK_SIZE):
        chunk = json_str[i:i+CHUNK_SIZE]
        ser.write((chunk + "\n").encode())
        time.sleep(0.05)  # small delay
    print("Drawings sent!")