#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#STT.py
from PyQt5.QtCore import QObject
from PyQt5 import  QtWidgets, QtCore
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import requests
import io
from datetime import datetime
import re
import sqlite_utils
import cv2
import sys
import time
from queue import Queue
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel
import Jetson.GPIO as GPIO
import vlc
import os
import Jetson.GPIO as GPIO
import time


class SpeechToText(QtCore.QObject):
    image_signal = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    restart_listener = QtCore.pyqtSignal()
    def __init__(self, display, on_complete=None):
        super().__init__()
        self.display = display
        self.image_signal.connect(self.display.display_image, QtCore.Qt.QueuedConnection)
        self.on_complete = on_complete
        self.running = True
        self.setup_gpio()
        # 네이버 클로바 API 정보
        self.client_id = "vh65ko3r7j"
        self.client_secret = "3SRnacV8fqpfFGsmIlYaIgJDce9H1NytIfs4Hl2j"
        self.fs = 48000  # 샘플링 레이트
        self.duration = 5  # 녹음할 시간 (초)
        self.missed_count = 0  # 연속으로 인식 실패한 횟수
        self.max_misses = 2  # 최대 허용 실패 횟수
        self.device_index = self.set_device_by_name('USB Audio')
        # self.device_index = device_index
        self.stream = None
        self.queue = Queue()
        
        # VLC setup
        self.vlc_instance = vlc.Instance('--aout=pulse')
        self.player = self.vlc_instance.media_player_new()
        self.voice_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'voice')
        self.exit_voice = os.path.join(self.voice_dir, 'exit.mp3')
        self.yes_voice = os.path.join(self.voice_dir, 'yes.mp3')
        self.one_more_voice = os.path.join(self.voice_dir, 'one_more_time.mp3')
        self.no_photo_voice = os.path.join(self.voice_dir, 'no_photo.mp3')
        self.no_sound_voice = os.path.join(self.voice_dir, 'no_sound.mp3')
        self.smartthings_voice = os.path.join(self.voice_dir, 'smartthings.mp3')
        
        self.korean_regions = [
            "강남", "서초", "종로", "명동", "이태원", "동대문", "홍대", "신촌", "이화", "서대문", "마포",
            "용산", "성동", "광진", "중랑", "성북", "강북", "도봉", "노원", "은평", "양천", "강서",
            "구로", "금천", "영등포", "동작", "관악", "송파", "강동", "해운대", "동래", "부산진",
            "남구", "서구", "영도", "부산", "인천", "미추홀", "연수", "남동", "부평", "계양", "경주",
            "전주", "광주", "대전", "울산", "세종", "수원", "성남", "용인", "부천", "청주", "안산",
            "제주", "포항", "창원", "강릉", "강원도", "역삼", "송도", "광명", "김포", "잠실", "용인", "주문진", "보성", "서울",
        ]
        self.object_list = [
            "자전거", "자동차", "오토바이", "비행기", "버스", "기차", "트럭", "보트",
            "신호등", "소화전", "도로 표지판", "정지 표지판", "주차 미터기", "벤치",
            "새", "고양이", "개", "말", "소", "코끼리", "곰", "얼룩말", "기린",
            "모자", "배낭", "우산", "신발", "안경", "핸드백", "넥타이", "여행가방",
            "프리스비", "스키", "스노우보드", "스포츠 공", "연", "야구 배트",
            "야구 글러브", "스케이트보드", "서핑보드", "테니스 라켓",
            "병", "접시", "와인 잔", "컵", "포크", "나이프", "숟가락", "그릇",
            "바나나", "사과", "샌드위치", "오렌지", "브로콜리", "당근", "핫도그", "피자", "도넛", "케이크",
            "의자", "소파", "화분", "침대", "거울", "식탁", "창문", "책상", "화장실", "문",
            "TV", "노트북", "마우스", "리모컨", "키보드", "휴대폰", "전자레인지", "오븐", "토스터", "싱크대", "냉장고", "믹서기",
            "책", "시계", "꽃병", "가위", "테디 베어", "헤어 드라이어", "칫솔"
        ]
    
    def run(self):
        while self.running:
            audio_data = self.record_audio()
            recognized_text = self.send_audio_to_stt(audio_data)
            if recognized_text:
                keywords = self.extract_keywords(recognized_text)
                if keywords:
                    self.find_image(keywords)
                else:
                    print("검색 결과가 없습니다.")
            else:
                print("인식된 것 없음.")
                self.missed_count += 1
                if self.missed_count >= self.max_misses:
                    print(f"{self.max_misses}회 연속 대화 없음으로 프로그램을 종료합니다.")
                    self.play_sound(self.no_sound_voice)
                    self.running = False
                    self.exit_program()
                else:
                    self.play_sound(self.one_more_voice)

            # time.sleep(5)
        self.finished.emit()
        # self.exit_program()

    # 디바이스 이름으로 오디오 입력 디바이스 설정
    def set_device_by_name(self, device_name):
        devices = sd.query_devices()
        device_id = None
        for i, dev in enumerate(devices):
            if device_name in dev['name']:
                device_id = i
                break
        if device_id is not None:
            # sd.default.device = device_id
            print(device_id)
            pass
        else:
            print("Device not found!")
        return device_id
    
    def setup_gpio(self):
        GPIO.setwarnings(False)
        
        self.led_pin = 15  # Jetson Nano의 사용할 GPIO 핀 번호
        GPIO.setmode(GPIO.BOARD)  # 핀 번호 지정 방식 설정
        GPIO.setup(self.led_pin, GPIO.OUT)
        GPIO.setup(7, GPIO.OUT)
        GPIO.output(7, GPIO.HIGH)

        
    # delay 선택해서 스마트싱스 루틴 실행
    def send_zigbee(self, delay):
        GPIO.output(7, GPIO.LOW)                                                                           

        print("지그비 신호 송신")
        time.sleep(delay)
        GPIO.output(7, GPIO.HIGH)

        print("지그비 신호 중단")
        
    def record_audio(self):
        print("녹음을 시작합니다...")
        GPIO.output(self.led_pin, GPIO.HIGH)
        recording = sd.rec(int(self.duration * self.fs), samplerate=self.fs, channels=1, dtype='int16', device=self.device_index)
        sd.wait()
        GPIO.output(self.led_pin, GPIO.LOW)
        print("녹음이 완료되었습니다.")
        return recording

    def send_audio_to_stt(self, audio_data):
        """녹음된 오디오를 Clova STT API로 전송하고 결과를 출력합니다."""
        lang = "Kor"
        url = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt?lang={}".format(lang)
        headers = {
            "X-NCP-APIGW-API-KEY-ID": self.client_id,
            "X-NCP-APIGW-API-KEY": self.client_secret,
            "Content-Type": "application/octet-stream"
        }
        bio = io.BytesIO()
        write(bio, self.fs, audio_data.astype(np.int16))
        bio.seek(0)
        response = requests.post(url, data=bio.read(), headers=headers)
        bio.close()
        
        if response.status_code == 200:
            json_response = response.json()
            text = json_response.get('text', '')
            if text:
                print("인식 결과:", text)
                self.extract_control(text)  # 종료 로직 호출
                self.extract_smartthings(text)  # 스마트싱스 제어 로직 호출
                self.missed_count = 0
                return text
            else:
                print("인식된 것 없음")
                return None
        else:
            print("Error:", response.text)
            self.missed_count += 1
            return None
    
    #앨범 제어 로직
    def extract_control(self, text):
        if '종료' in text or '아니야' in text:
            print("종료 키워드가 감지되었습니다. 처리 중...")
            self.play_sound(self.exit_voice)
            # 종료 전 필요한 작업을 처리하도록 설정
            self.running = False
            self.exit_program()
            
            # if self.on_complete:
            #     self.on_complete()
            # else:
            #     self.exit_program()
    
    #스마트 싱스 제어 로직
    def extract_smartthings(self, text):
        if '루틴' in text or 'routine' in text or '자동화' in text:
            print("스마트싱스로직")
            self.send_zigbee(1.2)
            self.play_sound(self.smartthings_voice)
            self.running = False
            self.exit_program()

        elif '불 켜' in text or '켜줘' in text:
            print("스마트싱스로직2")
            self.send_zigbee(1.2)
            self.play_sound(self.smartthings_voice)
            self.running = False
            self.exit_program()      


    def extract_keywords(self, text):
        keywords = [None, None, None]  # 날짜, 지역, 객체 순서로 초기화

    # 날짜 정보 추출
        date_info = self.parse_date_from_text(text)
        if date_info:
            keywords[0] = date_info
        
        # 지역명 검색
        for region in self.korean_regions:
            if region in text:
                keywords[1] = region
                break  # 첫 번째 일치하는 지역을 찾으면 중단
        
        # 객체 검색
        for object in self.object_list:
            if object in text:
                keywords[2] = object
                break  # 첫 번째 일치하는 객체를 찾으면 중단
        
        print(keywords)
        return keywords
        
    
    def parse_date_from_text(self, text):
            now = datetime.now()
            current_year = now.year
            current_month = now.month
            current_day = now.day
            
            if '오늘' in text:
                return "{year}:{month:02d}:{day:02d}".format(year=current_year, month=current_month, day=current_day)


            # 년, 월, 일
            full_date_match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', text)
            if full_date_match:
                year = int(full_date_match.group(1))
                month = int(full_date_match.group(2))
                day = int(full_date_match.group(3))
                return "{year}:{month:02d}:{day:02d}".format(year=year, month=month, day=day)

            # 년, 월
            year_month_match = re.search(r'(\d{4})년\s*(\d{1,2})월', text)
            if year_month_match:
                year = int(year_month_match.group(1))
                month = int(year_month_match.group(2))
                return "{year}:{month:02d}".format(year=year, month=month)

            # 년도
            year_match = re.search(r'(\d{4})년', text)
            if year_match:
                year = int(year_match.group(1))
                return str(year)

            # 작년,재작년
            relative_year_month_match = re.search(r'(올해|작년|재작년)\s*(\d{1,2})월', text)
            if relative_year_month_match:
                relative_term = relative_year_month_match.group(1)
                month = int(relative_year_month_match.group(2))
                year = current_year - 1 if relative_term == '작년' else current_year - 2
                return "{year}:{month:02d}".format(year=year, month=month)
            
            
            # "작년", "재작년" 단독으로 사용된 경우
            if '올해' in text:
                return str(current_year)
            if '작년' in text:
                return str(current_year - 1)
            if '재작년' in text:
                return str(current_year - 2)

            return None

    def extract_regions(self, text):
        for region in self.korean_regions:
            if re.search(region, text):
                return region
        return None

    def find_image(self, keywords):
        # SQLite 연결
        try:
            db = sqlite_utils.Database("local.db")

            # 쿼리 구성
            conditions = []
            for idx, keyword in enumerate(keywords):
                if idx == 0 and keyword is not None:
                    conditions.append("date LIKE '%{keyword}%'".format(keyword=keyword))
                elif idx == 1 and keyword is not None:
                    conditions.append("address LIKE '%{keyword}%'".format(keyword=keyword))
                elif idx == 2 and keyword is not None:
                    conditions.append("tags LIKE '%{keyword}%'".format(keyword=keyword))

            if not conditions:
                print("올바른 키워드를 입력하세요.")
                self.play_sound(self.one_more_voice)
                return

            query = "SELECT * FROM album WHERE " + " AND ".join(conditions)

            # 데이터베이스에서 검색
            results = db.query(query) if query else []  # 제너레이터
            result_found = False

            for result in results:
                result_found = True
                image_path = result['image']
                print("검색 결과:", image_path)
                self.image_signal.emit(image_path)
                print("경로 생성 완료")
                self.running = False
                self.play_sound(self.yes_voice)
                self.exit_program()
                self.finished.emit()

            if not result_found:
                print("검색 결과가 없습니다.")
                self.play_sound(self.no_photo_voice)

        except sqlite_utils.db.NotFoundError as e:
            print(f"Database error: {e} - 테이블이나 컬럼을 찾을 수 없습니다.")
            self.play_sound(self.no_photo_voice)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            self.play_sound(self.no_photo_voice)
    
    def play_sound(self, audio_file):
        """Play a given audio file using VLC"""
        if self.player.is_playing():
            self.player.stop()  # Stop any currently playing audio
        media = self.vlc_instance.media_new(audio_file)
        self.player.set_media(media)
        self.player.play()
        # Wait for the audio to start playing
        while self.player.get_state() != vlc.State.Playing:
            time.sleep(0.1)
        # Wait for the audio to finish playing
        while self.player.get_state() == vlc.State.Playing:
            time.sleep(0.1)
    
    def stop(self):
        self.running = False
        self.finished.emit()
        print(1)
        self.restart_listener.emit()
    
    def exit_program(self):
        print("STT processing complete. Exiting...")
        self.stop()
        sys.exit()
        
    def cleanup(self):
        try:
            self.recorder.stop()
            self.recorder.delete()
        except Exception as e:
            print(f"Failed to stop or delete recorder: {e}")
        try:
            self.porcupine.delete()
        except Exception as e:
            print(f"Failed to delete Porcupine instance: {e}")

if __name__ == "__main__":

    # stt = SpeechToText(on_complete=lambda: print("Cleanup complete"))
    # stt.run()
    app = QtWidgets.QApplication(sys.argv)
    from viewer import DisplayImage
    display_instance = DisplayImage()  # DisplayImage 인스턴스 생성
    stt_instance = SpeechToText()
    stt_instance.image_signal.connect(display_instance.display_image)  # 신호 연결
    stt_instance.run()  # STT 실행
    sys.exit(app.exec_())