import jetson_inference
import jetson_utils
import Jetson.GPIO as GPIO
import time
import threading
from queue import Queue


class camera:
    def __init__(self, servo_pin=33):
        # 서보 모터 핀 및 초기화
        self.SERVO_PIN = servo_pin
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        self.pwm = GPIO.PWM(self.SERVO_PIN, 50)
        self.pwm.start(7.5)  # 중앙값(0도)에 해당하는 듀티 사이클 시작
        self.swipe_queue = Queue()
        self.prev_center = None
        self.net_objects = jetson_inference.detectNet("facenet-120", threshold=0.5)
        self.net_poses = jetson_inference.poseNet("resnet18-hand", threshold=0.15)
        self.cam = jetson_utils.videoSource("csi://0")
        print('init은 실행한다')


    def move_servo(self, pixel_distance, screen_width):
        print('모터가 안돌아가요')
        # Deadzone 설정 (예: 화면 너비의 5%로 설정)
        deadzone = screen_width * 0.1  # 화면 중앙에서 ±5% 이내의 변화는 무시

        # 픽셀 거리가 deadzone 이내라면 모터를 움직이지 않음
        # if abs(pixel_distance) < deadzone:
        #     # print("Within deadzone, no motor movement required.")
        #     return

        # 화면 중앙을 기준으로 최대 ±90도 회전하도록 설정
        angle = (pixel_distance / screen_width) * 180  # 비례식을 사용한 각도 계산
        angle = max(min(angle, 180), -180)  # 각도 범위 제한

        # 듀티 사이클 계산 및 설정
        DC = (angle + 180) * (10.0 / 360.0) + 2.5
        self.pwm.ChangeDutyCycle(DC)
        print("모터가 움직여요")
        # print(f"Moving servo to angle: {angle} degrees based on distance: {pixel_distance}")

        # 모션 영향 없게 초기화
        self.prev_center = None

    def test(self):
        motion_threshold = 150
        times = 0
        while times < 10:
            print(times)
            times += 1
            img = self.cam.Capture()

            if img is None:
                print('이미지 논')
                continue

            poses = self.net_poses.Process(img, overlay="links,keypoints")
            if len(poses) > 0:
                pose = poses[0]
                keypoints = pose.Keypoints
                # 손의 중심점 계산
                center_x = sum([key.x for key in keypoints]) / len(keypoints)
                center_y = sum([key.y for key in keypoints]) / len(keypoints)

                if self.prev_center is None:
                    self.prev_center = (center_x, center_y)
                    continue

                # 이전 프레임과의 거리 계산
                dx = center_x - self.prev_center[0]
                dy = center_y - self.prev_center[1]

                # Swipe 감지
                if abs(dx) > motion_threshold:
                    if dx > 0:
                        self.swipe_queue.put("next")
                        print('next')
                    else:
                        self.swipe_queue.put("back")
                        print('back')

                # 스마트싱스 루틴 실행
                if abs(dy) > motion_threshold:
                    if dy < 0:
                        self.swipe_queue.put("scene_play") 
                        print('Samsung')

                self.prev_center = (center_x, center_y)


    def detect_objects_and_poses(self):
        print('이건된다')
        flag = 0
        while flag <= 10:
            img = self.cam.Capture()
            
            # 이미지가 None인 경우 건너뛰고 다음 루프로 진행
            if img is None:
                continue
            
            detections = self.net_objects.Detect(img)
            
            # 가장 큰 객체 찾기
            largest_area = 0
            largest_center_x = img.width / 2  # 객체가 없는 경우 이미지 중앙으로 설정
            for detection in detections:
                # print('객체 인식 실패')
                if detection.ClassID == 0:
                    # print('yes')
                    area = detection.Width * detection.Height
                    if area > largest_area:
                        largest_area = area
                        largest_center_x = detection.Center[0]

            # 화면 중앙과의 거리 계산
            screen_center_x = img.width / 2
            distance_from_center = largest_center_x - screen_center_x

            # 상태 메시지 출력
            print(f"Distance from Center: {distance_from_center}")
            self.move_servo(distance_from_center, img.width)


# 객체 탐지 및 포즈 탐지를 같은 카메라에서 번갈아가며 실행
if __name__ == "__main__":
    print('네임이 될까?')
    tracker = camera()
    tracker.detect_objects_and_poses()

# 메인 스레드가 스레드 종료를 기다림
# thread.join()
