import jetson_inference
import jetson_utils
import Jetson.GPIO as GPIO
import serial
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
        # self.net_objects = jetson_inference.detectNet("facenet-120", threshold=0.5)
        # self.net_poses = jetson_inference.poseNet("resnet18-hand", threshold=0.15)
        self.cam = jetson_utils.videoSource("csi://0")
        print('init은 실행한다')




    def serial(self):
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
            cnt = 0
            while True:
                if arduino.in_waiting > 0:
                    data = arduino.readline()
                    if data:
                        decoded_data = data.decode().strip()
                        if decoded_data in ["next", "prev", "smart"]:
                            print(decoded_data, cnt)
                            cnt += 1
                else:
                    # print("empty")
                    time.sleep(0.01)

        except Exception as e:
            print(e)
        finally:
            arduino.close()



    def test(self):
        motion_threshold = 150
        times = 0
        while times < 10:
            print(times)
            times += 1
            # img = self.cam.Capture()

            # if img is None:
            #     continue

            # poses = self.net_poses.Process(img, overlay="links,keypoints")
            # if len(poses) > 0:
            #     pose = poses[0]
            #     keypoints = pose.Keypoints
            #     # 손의 중심점 계산
            #     center_x = sum([key.x for key in keypoints]) / len(keypoints)
            #     center_y = sum([key.y for key in keypoints]) / len(keypoints)

            #     if self.prev_center is None:
            #         self.prev_center = (center_x, center_y)
            #         continue

            #     # 이전 프레임과의 거리 계산
            #     dx = center_x - self.prev_center[0]
            #     dy = center_y - self.prev_center[1]

            #     # Swipe 감지
            #     if abs(dx) > motion_threshold:
            #         if dx > 0:
            #             self.swipe_queue.put("next")
            #             print('next')
            #         else:
            #             self.swipe_queue.put("back")
            #             print('back')

            #     # 스마트싱스 루틴 실행
            #     if abs(dy) > motion_threshold:
            #         if dy < 0:
            #             self.swipe_queue.put("scene_play") 
            #             print('Samsung')

            #     self.prev_center = (center_x, center_y)


    def get_swipe_queue(self):
        return self.swipe_queue
    

if __name__ == "__main__":
    print('네임이 될까?')
    tracker = camera()
    tracker.serial()

