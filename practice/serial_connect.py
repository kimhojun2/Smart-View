import serial
import time

arduino = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    stopbits=serial.STOPBITS_ONE,
    timeout=5,
    xonxoff=False,
    rtscts=True, 
    dsrdtr=False,
    write_timeout=2
)

try:
    while True:
        if arduino.in_waiting > 0:
            data = arduino.readline()
            if data:
                decoded_data = data.decode().strip()
                if decoded_data in ["next", "prev", "smart"]:
                    print(decoded_data)
        else:
            time.sleep(0.01)

except Exception as e:
    print(e)
finally:
    arduino.close()
