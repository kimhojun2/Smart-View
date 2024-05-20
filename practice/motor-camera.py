#!/usr/bin/env python3
import threading
import jetson.inference
import jetson.utils
import Jetson.GPIO as GPIO
import time
from PyQt5 import QtCore

class ObjectTracker(threading.Thread):
    def __init__(self, camera, servo_pin=33):
        threading.Thread.__init__(self)
        self.camera = camera
        self.SERVO_PIN = servo_pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        self.pwm = GPIO.PWM(self.SERVO_PIN, 50)
        self.pwm.start(7.5)  # Start PWM with 7.5% duty cycle (approximately 90 degrees/neutral position)

    def move_servo(self, pixel_distance, screen_width):
        deadzone = screen_width * 0.1  # Deadzone set to 10% of the screen width
        if abs(pixel_distance) < deadzone:
            print("Within deadzone, no motor movement required.")
            return

        angle = (pixel_distance / screen_width) * 180  # Calculate the angle based on pixel distance
        angle = max(min(angle, 90), -90)  # Limit angle to ±90 degrees
        duty_cycle = (angle + 90) / 18 + 2.5  # Convert angle to PWM duty cycle
        self.pwm.ChangeDutyCycle(duty_cycle)
        print(f"Moving servo to {angle} degrees based on distance: {pixel_distance}")

    def run(self):
        net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.5)
        while True:
            img = self.camera.Capture()
            detections = net.Detect(img)
            largest_area = 0
            largest_center_x = img.width / 2  # Default to center

            for detection in detections:
                area = detection.Width * detection.Height
                if area > largest_area:
                    largest_area = area
                    largest_center_x = detection.Center[0]

            distance_from_center = largest_center_x - img.width / 2
            self.move_servo(distance_from_center, img.width)

class GestureRecognition(threading.Thread):
    def __init__(self, display_widget, camera):
        threading.Thread.__init__(self)
        self.display_widget = display_widget
        self.camera = camera
        self.net = jetson.inference.poseNet("resnet18-hand", threshold=0.15)
        self.prev_center_x = None
        self.motion_threshold = 150

    def run(self):
        while True:
            img = self.camera.Capture()
            poses = self.net.Process(img, overlay="links,keypoints")
            for pose in poses:
                center_x = sum([key.x for key in pose.Keypoints]) / len(pose.Keypoints)
                if self.prev_center_x is not None:
                    dx = center_x - self.prev_center_x
                    if abs(dx) > self.motion_threshold:
                        if dx > 0:
                            QtCore.QMetaObject.invokeMethod(self.display_widget, 'next_image', QtCore.Qt.QueuedConnection)
                        else:
                            QtCore.QMetaObject.invokeMethod(self.display_widget, 'previous_image', QtCore.Qt.QueuedConnection)
                self.prev_center_x = center_x

if __name__ == "__main__":
    from PyQt5 import QtWidgets
    app = QtWidgets.QApplication([])  # Initialize PyQt application
    camera = jetson.utils.videoSource("csi://0")
    display_widget = DisplayImage()  # Assuming DisplayImage is defined elsewhere and suitable for use here
    display_widget.show()

    tracker_thread = ObjectTracker(camera)
    gesture_thread = GestureRecognition(display_widget, camera)
    
    tracker_thread.start()
    gesture_thread.start()

    app.exec_()  # Start the PyQt event loop
    tracker_thread.join()
    gesture_thread.join()
