#!/usr/bin/env python3
import jetson.inference
import jetson.utils
import Jetson.GPIO as GPIO
import time

class ObjectTracker:
    def __init__(self, servo_pin=33):
        # 서보 모터 핀 및 초기화
        self.SERVO_PIN = servo_pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        self.pwm = GPIO.PWM(self.SERVO_PIN, 50)
        self.pwm.start(7.5)  # 중앙값(0도)에 해당하는 듀티 사이클 시작

    def move_servo(self, pixel_distance, screen_width):
        # Deadzone 설정 (예: 화면 너비의 5%로 설정)
        deadzone = screen_width * 0.1  # 화면 중앙에서 ±5% 이내의 변화는 무시

        # 픽셀 거리가 deadzone 이내라면 모터를 움직이지 않음
        if abs(pixel_distance) < deadzone:
            print("Within deadzone, no motor movement required.")
            return

        # 화면 중앙을 기준으로 최대 ±90도 회전하도록 설정
        angle = (pixel_distance / screen_width) * 180  # 비례식을 사용한 각도 계산
        angle = max(min(angle, 180), -180)  # 각도 범위 제한

        # 듀티 사이클 계산 및 설정
        DC = (angle + 180) * (10.0 / 360.0) + 2.5
        self.pwm.ChangeDutyCycle(DC)
        print(f"Moving servo to angle: {angle} degrees based on distance: {pixel_distance}")

    def run_tracking(self):
        # 네트워크 초기화
        net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.5)
        camera = jetson.utils.videoSource("csi://0")

        while True:
            img = camera.Capture()
            detections = net.Detect(img)
            
            # 가장 큰 객체 찾기
            largest_area = 0
            largest_center_x = 0
            for detection in detections:
                if detection.ClassID == 1:
                    print('yes')
                    area = detection.Width * detection.Height
                    if area > largest_area:
                        largest_area = area
                        largest_center_x = detection.Center[0]
                else:
                    largest_center_x = img.width / 2
                    print('no')
                    continue

            # 화면 중앙과의 거리 계산
            screen_center_x = img.width / 2
            distance_from_center = largest_center_x - screen_center_x

            # 상태 메시지 출력
            print(f"Distance from Center: {distance_from_center}")

            # 모터 제어 호출 부분
            self.move_servo(distance_from_center * (-1), img.width)

if __name__ == "__main__":
    tracker = ObjectTracker()
    tracker.run_tracking()
