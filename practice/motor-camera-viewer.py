#!/usr/bin/env python3
import sys
import os
import threading
import requests
from PyQt5 import QtWidgets, QtGui, QtCore
from PIL import Image, ExifTags
import jetson.inference
import jetson.utils
import Jetson.GPIO as GPIO
import sqlite_utils

# Initialize GPIO for servo control
SERVO_PIN = 33
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(7.5)  # Start at the middle position

def move_servo(pixel_distance, screen_width):
    # Define deadzone and calculate servo movement
    deadzone = screen_width * 0.1
    if abs(pixel_distance) < deadzone:
        return
    angle = (pixel_distance / screen_width) * 180
    angle = max(min(angle, 90), -90)
    duty_cycle = (angle + 90) / 18 + 2.5
    pwm.ChangeDutyCycle(duty_cycle)

class ImageProcessor:
    season_list = {'01': 'Winter', '02': 'Winter', '03': 'Spring', '04': 'Spring',
                   '05': 'Summer', '06': 'Summer', '07': 'Summer', '08': 'Summer',
                   '09': 'Fall', '10': 'Fall', '11': 'Winter', '12': 'Winter'}
    
    def __init__(self, download_path, db_path):
        self.download_path = download_path
        self.db = sqlite_utils.Database(db_path)
        self.index = 0

    def download_image(self, image_url):
        album_folder = self.download_path
        os.makedirs(album_folder, exist_ok=True)
        file_name = f"{self.index}.jpg"
        local_path = os.path.join(album_folder, file_name)
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            self.index += 1
            return local_path
        return None

    def image_info_to_db(self, image_path):
        image = Image.open(image_path)
        info = image._getexif()
        if info:
            metadata = {ExifTags.TAGS.get(tag, tag): value for tag, value in info.items()}
            make_time = metadata.get('DateTimeOriginal', "Unknown")
            month = make_time[5:7] if make_time != "Unknown" else None
            weather = self.season_list.get(month, "Unknown")
            gps_info = metadata.get('GPSInfo')
            gps_lat = gps_lon = None
            if gps_info:
                gps_lat = self.convert_to_decimal(gps_info.get(2)) if 2 in gps_info else None
                gps_lon = self.convert_to_decimal(gps_info.get(4)) if 4 in gps_info else None
            address = self.lat_lon_to_addr(gps_lon, gps_lat) if gps_lat and gps_lon else "Unknown"
            image_info = {
                "title": os.path.basename(image_path),
                "image": image_path,
                "season": weather,
                "date": make_time,
                "gps": (gps_lat, gps_lon),
                "address": address
            }
            self.db["album"].insert(image_info)

    def convert_to_decimal(self, gps_data):
        degrees, minutes, seconds = gps_data
        return degrees + (minutes / 60) + (seconds / 3600)

    def lat_lon_to_addr(self, lon, lat):
        # Dummy implementation for latitude/longitude to address conversion
        return f"Address for ({lat}, {lon})"

class DisplayImage(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.index = 0
        self.images = []
        self.load_images()
        self.showFullScreen()
        self.setScaledContents(True)
        self.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)

    def load_images(self):
        directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Display', 'images'))
        self.images = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        self.display_image(self.images[0])

    def display_image(self, image_path):
        pixmap = QtGui.QPixmap(image_path)
        self.setPixmap(pixmap)

    def next_image(self):
        self.index = (self.index + 1) % len(self.images)
        self.display_image(self.images[self.index])

    def previous_image(self):
        self.index = (self.index - 1) % len(self.images)
        self.display_image(self.images[self.index])

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Right:
            self.next_image()
        elif event.key() == QtCore.Qt.Key_Left:
            self.previous_image()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    display = DisplayImage()
    display.show()

    camera = jetson.utils.videoSource("csi://0")  # Camera source
    object_tracker = ObjectTracker(camera, SERVO_PIN)
    object_tracker.start()

    sys.exit(app.exec_())
