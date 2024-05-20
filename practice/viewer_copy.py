from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QThread, pyqtSignal, QEvent, QObject, QTimer
import sys
import os
from STT import SpeechToText, KeywordFinder
# from .touch_image import TouchImage
# from .mic_image import MicImage
# from .motion_sensor_image import MotionSensorImage
# from .image_load import ImageLoaderThread
import requests
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO
import threading
from cam_test_2_lbe import camera
import queue
import time
import pvporcupine
import numpy as np
import struct
import subprocess
import requests
from pvrecorder import PvRecorder


module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sharing'))
if module_path not in sys.path:
    sys.path.append(module_path)

from firebase_admin_setup import initialize_firebase, get_firestore_client
import sqlite_utils

api_key = "20e841d134e90cd157222ba545984e63"


# display_image.py
#다운로드 이미지 저장
class ImageProcessor:
    season_list = {'01':'겨울',
        '02':'겨울',
        '03':'봄',
        '04':'봄',
        '05':'여름',
        '06':'여름',
        '07':'여름',
        '08':'여름',
        '09':'가을',
        '10':'가을',
        '11':'겨울',
        '12':'겨울'}
    
    def __init__(self, download_path, db_path):
        self.download_path = download_path
        self.db = sqlite_utils.Database(db_path)
        self.index = 0

    def download_image(self, image_url):
        album_folder = self.download_path
        if not os.path.exists(album_folder):
            os.makedirs(album_folder)
        file_name = f"{self.index}.jpg"
        local_path = os.path.join(album_folder, file_name)
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"이미지 다운로드 완료: {local_path}")
            self.index += 1
            return local_path
        else:
            print("이미지를 다운로드하는 데 문제가 발생했습니다.")
            return None

    def image_info_to_db(self, image_path):
        try:
            image = Image.open(image_path)           
            info = image._getexif()
            if info:
                metadata = {TAGS.get(tag, tag): value for tag, value in info.items()}
                make_time = metadata.get('DateTimeOriginal', "정보 없음")
                month = make_time[5:7] if make_time != "정보 없음" else None
                image_weather = self.season_list.get(month, "정보 없음")
                gps_info = metadata.get('GPSInfo')
                gps_lat = gps_lon = None
                if gps_info:
                    gps_lat = self.convert_to_decimal(gps_info.get(2)) if 2 in gps_info else None
                    gps_lon = self.convert_to_decimal(gps_info.get(4)) if 4 in gps_info else None
                address = self.lat_lon_to_addr(gps_lon, gps_lat) if gps_lat and gps_lon else "정보 없음"
                image_info = {
                    "title": os.path.basename(image_path),
                    "image": image_path,
                    "season": image_weather,
                    "date": make_time,
                    "gps": (gps_lat, gps_lon),
                    "address": address
                }
                self.db["album"].insert(image_info)
                print("데이터베이스에 정보 저장 완료")
        except Exception as e:
            print(f"메타데이터 추출 및 저장 중 오류 발생: {e}")

    def convert_to_decimal(self, gps_data):
        degrees, minutes, seconds = gps_data
        return degrees + (minutes / 60.0) + (seconds / 3600.0)

    def lat_lon_to_addr(self, lon, lat):
        url = 'https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?x={longitude}&y={latitude}'.format(longitude=lon, latitude=lat)
        headers = {"Authorization": "KakaoAK " + api_key}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            return result['documents'][0]['address_name'] if result['documents'] else "No Address Found"
        else:
            return "No Data"

#firebase 별도 스레드 생성
class ImageUpdateEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, image_url):
        super().__init__(ImageUpdateEvent.EVENT_TYPE)
        self.image_url = image_url

class FirebaseThread(threading.Thread):
    def __init__(self, uid, callback):
        super().__init__()
        self.uid = uid
        self.callback = callback

    def run(self):
        db = get_firestore_client()
        user_doc = db.collection('users').document(self.uid)
        if user_doc.get().exists:
            groups = user_doc.get().to_dict().get('groups', [])
            for group_name in groups:
                self.monitor_group_images(group_name)

    def monitor_group_images(self, group_name):
        db = get_firestore_client()
        group_doc = db.collection('group').document(group_name)
        group_doc.on_snapshot(self.handle_snapshot)

    def handle_snapshot(self, doc_snapshot, changes, read_time):
        print("Snapshot received")
        for doc in doc_snapshot:
            img_url = doc.to_dict().get('img_url', None)
            if img_url:
                QtCore.QCoreApplication.postEvent(self.callback, ImageUpdateEvent(img_url))
                
# 디스플레이 조작 관련
class DisplayImage(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.images = []
        self.current_image_index = 0
        self.setupUi()
        self.installEventFilter(self)
        self.processor = ImageProcessor(os.path.abspath(os.path.join(os.path.dirname(__file__), 'album')), "local.db")
        self.image_update_timer = QTimer(self)  # 이미지 업데이트를 위한 타이머
        self.image_update_timer.timeout.connect(self.load_images)  # load_images 함수 연결
        self.image_update_timer.start(3000) #3초마다 리스트 재탐색
        
    def eventFilter(self, source, event):
        if event.type() == ImageUpdateEvent.EVENT_TYPE:
            self.update_image_from_url(event.image_url)
            return True
        return super().eventFilter(source, event)

    def setupUi(self):
        self.showFullScreen()
        self.setScaledContents(True)
        self.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)
        self.load_images()
        self.initialize_firebase()
        self.current_image_index = 0  # 현재 이미지 인덱스 초기화
        self.index = 0  # 다운로드 인덱스 초기화
        self.is_group_image_displayed = False
        
    def load_images(self):
        directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Display', 'images'))
        new_images = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        new_image_set = set(new_images)
        
        if new_image_set != set(self.images):
            added_images = list(new_image_set - set(self.images))
            removed_images = list(set(self.images) - new_image_set)
            
            # 현재 이미지 리스트 업데이트
            self.images = new_images
            print("이미지 목록 업데이트됨")

            # 현재 보고 있는 이미지의 인덱스 계산
            if self.images and self.current_image_index < len(self.images):
                # 이미지 인덱스가 범위 안에 있는 경우, 같은 이미지 유지
                current_image = self.images[self.current_image_index]
                if current_image in removed_images:
                    # 현재 보고 있는 이미지가 제거된 경우, 첫 번째 이미지 표시
                    self.current_image_index = 0
                    self.display_image(self.images[0])
                else:
                    # 현재 이미지 유지
                    self.current_image_index = self.images.index(current_image)
            elif self.images:
                # 이미지가 있지만 인덱스가 범위를 벗어나면 처음부터 시작
                self.current_image_index = 0
                self.display_image(self.images[0])
            else:
                # 이미지가 없는 경우
                self.setText("이미지가 없습니다.")
            
    def display_image(self, image_path):
        try:
            print(f"로딩 시도: {image_path}")  # 로딩 시도 로그 출력
            if image_path.lower().endswith('.gif'):
                movie = QtGui.QMovie(image_path)
                self.setMovie(movie)
                movie.start()
            else:
                pixmap = QtGui.QPixmap(image_path)
                if pixmap.isNull():
                    raise Exception("Pixmap is null, 이미지 로드 실패")
                self.original_pixmap = pixmap
                self.setPixmap(pixmap)
        except Exception as e:
            print(f"이미지 로드 실패: {e}")  # 이미지 로드 실패 로그 출력
            self.setText(f"이미지 로드 실패: {e}")  # 화면에 실패 메시지 출력
        
    def update_image_from_url(self, image_url):
        local_path = self.processor.download_image(image_url)
        if local_path:
            self.display_image(local_path)
            self.processor.image_info_to_db(local_path)

    def initialize_firebase(self):
        initialize_firebase()
        self.uid = self.read_uid_file()
        if self.uid:
            self.start_firebase_thread()

    def start_firebase_thread(self):
        self.firebase_thread = FirebaseThread(self.uid, self)
        self.firebase_thread.start()

    def read_uid_file(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sharing', 'uid.txt')
        try:
            with open(path, 'r') as file:
                return file.read().strip()
        except FileNotFoundError:
            print("UID file not found.")
            return None
        
        
    def mousePressEvent(self, event):
        QtWidgets.QApplication.instance().quit()
    # if self.is_group_image_displayed:
    #     self.display_image(self.images[self.current_image_index])
    # else:
    #     super().mousePressEvent(event)

    #키보드로 사진 전환 및 종료
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            QtWidgets.QApplication.instance().quit()
        elif event.key() == QtCore.Qt.Key_Right:
            self.next_image()
        elif event.key() == QtCore.Qt.Key_Left:
            self.previous_image()

    #다음 이미지로 전환
    def next_image(self):
        if self.images:
            self.current_image_index = (self.current_image_index + 1) % len(self.images)
            self.display_image(self.images[self.current_image_index])
    #이전 이미지로 전환
    def previous_image(self):
        if self.images:
            self.current_image_index = (self.current_image_index - 1) % len(self.images)
            self.display_image(self.images[self.current_image_index])
#음성 인식 관련
class Listen(QThread):
    def __init__(self, display):
        super().__init__()
        self.display = display
        # self.access_key = "BiQeBmnb2sGBb+/o+rlSbgRVOVR3YHdehy2oziBrO5QJLI2b09/Jgg==" #윈도우용
        self.access_key = "3QMATr0nr3dGWTEfR/450TDnGK4MRQdo2TLfYs7zAlN4/w92b880Yw==" #리눅스용
        self.current_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'wakeword')
        self.keyword_album = os.path.join(self.current_dir, '앨범아.ppn')
        self.keyword_next = os.path.join(self.current_dir, '다음사진.ppn')
        self.keyword_previous = os.path.join(self.current_dir, '이전사진.ppn')
        self.model_path = os.path.join(self.current_dir, 'porcupine_params_ko.pv')
        self.porcupine = None
        self.recorder = None

    def run(self):
        try:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keyword_paths=[self.keyword_album, self.keyword_next, self.keyword_previous],
                model_path=self.model_path
            )

            self.recorder = PvRecorder(
                frame_length=self.porcupine.frame_length,
                device_index=-1,  # Default audio device
                # buffered_frames_count=100
            )

            self.recorder.start()

            print("Listening... Press Ctrl+C to exit")

            while True:
                pcm_frame = self.recorder.read()
                if len(pcm_frame) != self.porcupine.frame_length:
                    print(f"Frame length mismatch: {len(pcm_frame)} expected {self.porcupine.frame_length}")
                    continue
                keyword_index = self.porcupine.process(pcm_frame)
                if keyword_index >= 0:
                    self.wake_word_callback(keyword_index)

        except Exception as e:
            print('Stopping...', str(e))
        finally:
            if self.porcupine:
                self.porcupine.delete()
            if self.recorder:
                self.recorder.stop()
                self.recorder.delete()

    def wake_word_callback(self, keyword_index):
        if keyword_index == 0:
            print("Album keyword detected!")
            STT_dir = os.path.dirname(os.path.abspath(__file__))
            stt_path = os.path.join(STT_dir, 'STT.py')
            stt_process = subprocess.Popen(['python', stt_path])
        elif keyword_index == 1:
            print("Next photo keyword detected!")
            self.display.next_image()
            tracking_thread = threading.Thread(target=tracker.detect_objects_and_poses)
            tracking_thread.start()
        elif keyword_index == 2:
            print("Previous photo keyword detected!")
            self.display.previous_image()
            # tracking_thread2 = threading.Thread(target=tracker.test)
            # tracking_thread2.start()

class CheckMessage:
    def __init__(self, swipe_queue, display):
        self.swipe_queue = swipe_queue
        self.display_ins = display

    def check_messages(self):
        while True:
            if not self.swipe_queue.empty():
                message = self.swipe_queue.get()
                if message == 'next':
                    print(message)
                    # display.next_image()
                elif message == 'back':
                    print(message)
                    # display.previous_image()
                # elif message == 'scene_play':
                #     # 스마트싱스 정보
                #     scene_id = 'ec22f091-90b4-4f91-8e23-a2783326bad3'  # 스마트싱스 scene ID
                #     oauth_token = '8cd2da5e-e34e-4fe5-b38d-7b48301f03fb'  # OAuth 토큰
                #     url = f'https://api.smartthings.com/scenes/{scene_id}/execute'  # API 엔드포인트

                #     # HTTP 헤더 설정
                #     headers = {
                #         'Authorization': f'Bearer {oauth_token}',
                #         'Content-Type': 'application/json'
                #     }

                #     # API 요청
                #     response = requests.post(url, headers=headers)

                #     # 응답 확인
                #     if response.status_code == 200:
                #         print("스마트싱스 실행")
                #         print(response.json())  # 성공 시 응답 내용 출력
                #     else:
                #         print("스마트싱스 실패:", response.status_code, response.text)  # 실패 시 오류 메시지 출력



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    tracker = camera()
    display = DisplayImage()
    listen_thread = Listen(display)
    listen_thread.start()
    # # swipe_queue = tracker.get_swipe_queue()
    # check_message_thread = threading.Thread(target=CheckMessage(swipe_queue, display).check_messages)
    # check_message_thread.start()
    db = sqlite_utils.Database("local.db")
    # db["album"].create({
    # "id": int,
    # "title": str,
    # "image": str,
    # "season": str,
    # "date": str,
    # "gps": tuple,
    # "address": str
    # }, pk="id")
    # touch_manager = TouchImage(display.label)
    # display.label.installEventFilter(touch_manager)
    # display.show()
    sys.exit(app.exec_())
