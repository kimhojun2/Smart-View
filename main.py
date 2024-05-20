# main.py
import os
import sys
from PyQt5 import QtWidgets

# 디스플레이 이미지 창 불러오기
sys.path.append(os.path.join(os.path.dirname(__file__), 'Display'))
from Display.viewer import DisplayImage

# QR창 불러오기
sys.path.append(os.path.join(os.path.dirname(__file__), 'sharing'))
from sharing.qr_recognize import QRRecognizer


def run_qr_recognize():
    recognizer = QRRecognizer()
    recognizer.run()

def run_display_image():
    app = QtWidgets.QApplication(sys.argv)
    display = DisplayImage()
    display.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    # 현재 작업 디렉토리와 파일 경로 확인
    current_directory = os.getcwd()
    uid_path = os.path.join(current_directory, "Desktop", "khj", "sharing", "uid.txt")
    print("현재 작업 디렉토리:", current_directory)
    print("UID 파일 경로:", uid_path)
    # run_display_image()
    if os.path.exists(uid_path):
        print("UID 파일이 존재합니다. 이미지 디스플레이를 시작합니다.")
        run_display_image()
    else:
        print("UID 파일이 존재하지 않습니다. QR 코드 스캐너를 시작합니다.")
        run_qr_recognize()
        if os.path.exists(uid_path):
            print("UID 파일이 생성되었습니다. 이미지 디스플레이를 시작합니다.")
            run_display_image()
        else:
            print("UID 파일이 생성되지 않았습니다. 프로그램을 종료합니다.")