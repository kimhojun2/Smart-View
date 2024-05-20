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

    def detect_clap(self, keypoints):
        # 손바닥의 인덱스
        palm_left_idx = 0
        palm_right_idx = 0

        for i, key in enumerate(keypoints):
            if key.ID == 0:  # 손바닥 인덱스 확인
                if key.name == 'palm_left':
                    palm_left_idx = i
                elif key.name == 'palm_right':
                    palm_right_idx = i

        palm_left = keypoints[palm_left_idx]
        palm_right = keypoints[palm_right_idx]

        # 두 손바닥 사이의 거리 계산
        distance = ((palm_left.x - palm_right.x) ** 2 + (palm_left.y - palm_right.y) ** 2) ** 0.5
        return distance < self.min_distance
    
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

                # # 스마트싱스 루틴 실행
                # if abs(dy) > motion_threshold:
                #     if dy < 0:
                #         self.swipe_queue.put("scene_play")
                #         print('Samsung')

                # 박수 감지
                if self.detect_clap(keypoints):
                    current_time = time.time()
                    if current_time - self.last_clap_time < self.clap_threshold:
                        self.clap_count += 1
                        print(f"Clap {self.clap_count}")
                        if self.clap_count == 2:
                            print("Double clap detected!")
                            self.swipe_queue.put("scene_play")
                            # 여기에서 스마트싱스 루틴 실행
                            self.clap_count = 0  # 다시 초기화하여 다음 박수 두 번을 감지
                    else:
                        self.clap_count = 1  # 첫 번째 박수 감지
                    self.last_clap_time = current_time

                self.prev_center = (center_x, center_y)


    def get_swipe_queue(self):
        return self.swipe_queue


# 객체 탐지 및 포즈 탐지를 같은 카메라에서 번갈아가며 실행
if __name__ == "__main__":
    tracker = camera()
    tracker.detect_objects_and_poses()

# 메인 스레드가 스레드 종료를 기다림
# thread.join()
