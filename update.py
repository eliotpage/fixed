import serial

esp = serial.serial_for_url(
    "socket://192.168.1.42:20000",  # your Mac's IP
    baudrate=115200,
    timeout=1
)

esp.write(b"Hello ESP32\n")
print(esp.readline().decode())