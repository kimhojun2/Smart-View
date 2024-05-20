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

        # 스마트싱스 감지 변수 초기화
        self.open_detected = False  # 손가락 모두 펴진 동작 감지 여부
        self.last_action_time = 0  # 마지막 동작 시간
        self.action_delay = 1  # 동작 인식 후 대기 시간 (초)
        self.open_threshold = 1  # 손가락이 모두 펴진 동작 사이의 최대 시간 (초)
        self.last_open_time = 0  # 마지막 손가락 모두 펴진 시간

    def move_servo(self, pixel_distance, screen_width):
        # Deadzone 설정 (예: 화면 너비의 5%로 설정)
        deadzone = screen_width * 0.1  # 화면 중앙에서 ±5% 이내의 변화는 무시

        # 픽셀 거리가 deadzone 이내라면 모터를 움직이지 않음
        if abs(pixel_distance) < deadzone:
            # print("Within deadzone, no motor movement required.")
            return

        # 화면 중앙을 기준으로 최대 ±90도 회전하도록 설정
        angle = (pixel_distance / screen_width) * 180  # 비례식을 사용한 각도 계산
        angle = max(min(angle, 180), -180)  # 각도 범위 제한

        # 듀티 사이클 계산 및 설정
        DC = (angle + 180) * (10.0 / 360.0) + 2.5
        self.pwm.ChangeDutyCycle(DC)
        # print(f"Moving servo to angle: {angle} degrees based on distance: {pixel_distance}")

        # 모션 영향 없게 초기화
        # self.prev_center = None

    def all_fingers_open(self, keypoints):
        # 손가락 관절 키포인트 인덱스
        finger_joints = [
            (1, 4),   # 엄지
            (5, 8),   # 집게 손가락
            (9, 12),  # 중지
            (13, 16), # 약지
            (17, 20)  # 새끼 손가락
        ]

        for joint in finger_joints:
            if len(keypoints) > max(joint):
                x1, y1 = keypoints[joint[0]].x, keypoints[joint[0]].y
                x2, y2 = keypoints[joint[1]].x, keypoints[joint[1]].y
                distance = ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
                if distance < 50:  # 손가락이 펴지지 않은 경우
                    return False

        return True  # 모든 손가락이 펴진 경우

    def detect_v_sign(self, keypoints):
        # 브이(V) 모양은 검지와 중지가 펴져 있고, 나머지 손가락이 접힌 상태로 정의
        if len(keypoints) >= 21:  # 모든 키포인트가 존재하는지 확인
            index_finger_open = ((keypoints[5].x - keypoints[8].x) ** 2 + (keypoints[5].y - keypoints[8].y) ** 2) ** 0.5 > 50
            middle_finger_open = ((keypoints[9].x - keypoints[12].x) ** 2 + (keypoints[9].y - keypoints[12].y) ** 2) ** 0.5 > 50
            ring_finger_folded = ((keypoints[13].x - keypoints[16].x) ** 2 + (keypoints[13].y - keypoints[16].y) ** 2) ** 0.5 < 50
            pinky_finger_folded = ((keypoints[17].x - keypoints[20].x) ** 2 + (keypoints[17].y - keypoints[20].y) ** 2) ** 0.5 < 50

            return index_finger_open and middle_finger_open and ring_finger_folded and pinky_finger_folded
        return False
    
    def detect_objects_and_poses(self):
        # 네트워크 초기화
        # net_objects = jetson.inference.detectNet("facenet-120", threshold=0.5)
        # net_poses = jetson.inference.poseNet("resnet18-hand", threshold=0.15)
        # camera = jetson.utils.videoSource("csi://0")

        motion_threshold = 150  # 움직임을 감지할 최소 픽셀 거리

        while True:
            img = self.cam.Capture()
            
        #     # 이미지가 None인 경우 건너뛰고 다음 루프로 진행
        #     if img is None:
        #         continue
            
        #     detections = self.net_objects.Detect(img)
            
        #     # 가장 큰 객체 찾기
        #     largest_area = 0
        #     largest_center_x = img.width / 2  # 객체가 없는 경우 이미지 중앙으로 설정
        #     for detection in detections:
        #         # print('객체 인식 실패')
        #         if detection.ClassID == 0:
        #             # print('yes')
        #             area = detection.Width * detection.Height
        #             if area > largest_area:
        #                 largest_area = area
        #                 largest_center_x = detection.Center[0]

        #     # 화면 중앙과의 거리 계산
        #     screen_center_x = img.width / 2
        #     distance_from_center = largest_center_x - screen_center_x

        #     # 상태 메시지 출력
        #     # print(f"Distance from Center: {distance_from_center}")


        #     # 모터 제어 호출 부분
        #     self.move_servo(distance_from_center * (-1), img.width)

            # 포즈 탐지
            poses = self.net_poses.Process(img, overlay="links,keypoints")

            current_time = time.time()

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

                # 마지막 동작 시간으로부터 action_delay 초가 지났는지 확인
                if current_time - self.last_action_time >= self.action_delay:
                    # Swipe 감지
                    if abs(dx) > motion_threshold:
                        if dx > 0:
                            print('Swipe Right')
                            self.swipe_queue.put("next")
                        else:
                            print('Swipe Left')
                            self.swipe_queue.put("back")
                        self.last_action_time = current_time
                        continue  # Swipe 감지 후 다른 동작 무시


                    # 손가락이 모두 펴진 동작 감지
                    if self.all_fingers_open(keypoints):
                        self.open_detected = True
                        self.last_open_time = current_time
                        print("All fingers open detected")
                        self.last_action_time = current_time
                        continue  # 손가락이 모두 펴진 동작 감지 후 다른 동작 무시

                    # V 사인 감지
                    if self.open_detected and self.detect_v_sign(keypoints):
                        if current_time - self.last_open_time < self.open_threshold:
                            print("V sign detected!")
                            # 여기에서 스마트싱스 루틴 실행
                            self.swipe_queue.put("scene_play")
                            self.open_detected = False  # 초기화
                            self.last_action_time = current_time
                            continue  # V 사인 감지 후 다른 동작 무시

                self.prev_center = (center_x, center_y)

    def get_swipe_queue(self):
        return self.swipe_queue

# 객체 탐지 및 포즈 탐지를 같은 카메라에서 번갈아가며 실행
if __name__ == "__main__":
    tracker = camera()
    tracker.detect_objects_and_poses()

# 메인 스레드가 스레드 종료를 기다림
# thread.join()
