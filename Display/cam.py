#!/usr/bin/env python3
import jetson.inference
import jetson.utils
import Jetson.GPIO as GPIO
import time

class tracking:
    def __init__(self, servo_pin=32):
        # 서보 모터 핀 및 초기화
        SERVO_PIN = servo_pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        self.pwm = GPIO.PWM(SERVO_PIN, 50)
        self.pwm.start((1./18.)*100 + 2)  # 중앙값(0도)에 해당하는 듀티 사이클 시작
        # 네트워크 초기화
        self.net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=0.3)
        self.cam = jetson.utils.videoSource("csi://0")


    
    def move_servo(self, pixel_distance, screen_width):
        # Deadzone 설정 (예: 화면 너비의 5%로 설정)
        deadzone = screen_width * 0.1  # 화면 중앙에서 ±5% 이내의 변화는 무시

        # 픽셀 거리가 deadzone 이내라면 모터를 움직이지 않음
        if abs(pixel_distance) < deadzone:
            # print("Within deadzone, no motor movement required.")
            return

        # 화면 중앙을 기준으로 최대 ±90도 회전하도록 설정
        angle = (pixel_distance / screen_width) * 180 * -1  # 비례식을 사용한 각도 계산
        angle = max(min(angle, 180), -180)  # 각도 범위 제한
        print(f"angle======{angle}")
        # 듀티 사이클 계산 및 설정
        DC = (angle + 180) * (10.0 / 360.0) + 2.5
        # print("fuck!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.pwm.ChangeDutyCycle(DC)
        # print("dubble fuck!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!1")
        print(f"Moving servo to angle: {angle} degrees based on distance: {pixel_distance}")
        # 모션 영향 없게 초기화
        # self.prev_center = None
        
    def User_Tracking(self):

        # 캡쳐 및 객체 인식 실행
        img = self.cam.Capture()
        detections = self.net.Detect(img)

        # 가장 큰 객체 찾기
        largest_area = 0
        largest_center_x = img.width / 2
        for detection in detections:
            if detection.ClassID == 1:  # person 클래스 ID 사용
                area = detection.Width * detection.Height
                if area > largest_area:
                    largest_area = area
                    largest_center_x = detection.Center[0]

        # 인식 결과를 이미지에 박싱
        for detection in detections:
            print(f"Detected object: {self.net.GetClassDesc(detection.ClassID)} with confidence {detection.Confidence}")
            jetson.utils.cudaDrawRect(img, detection.ROI, (255, 0, 0, 150))  # 빨간색 박스

        # 이미지 파일로 저장
        jetson.utils.saveImageRGBA("detected_frame.jpg", img, img.width, img.height)


        if len(detections) == 0:
            print("겍체 X")

        # 화면 중앙과의 거리 계산
        screen_center_x = img.width / 2
        distance_from_center = largest_center_x - screen_center_x

        # 상태 메시지 출력 및 모터 제어
        print(f"Distance from Center: {distance_from_center}")
        self.move_servo(distance_from_center, img.width)

if __name__ == "__main__":
    print('네임이 될까?')
    tracker = tracking()
    tracker.User_Tracking()
