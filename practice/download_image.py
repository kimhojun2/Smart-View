#download_image.py
import os
import sys
import requests
from PyQt5.QtWidgets import QApplication
from PIL import Image
import sqlite_utils
from viewer import ImageProcessor
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'sharing'))
if module_path not in sys.path:
    sys.path.append(module_path)
from firebase_admin_setup import initialize_firebase, get_firestore_client

class ImageDownloader:
    def __init__(self, user_uid):
        self.user_uid = user_uid
        self.download_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'album'))
        self.db_path = "local.db"
        self.processor = ImageProcessor(self.download_path, self.db_path)
        initialize_firebase()

    def fetch_images(self):
        db = get_firestore_client()
        user_doc_ref = db.collection('users').document(self.user_uid)
        user_doc = user_doc_ref.get()
        if user_doc.exists:
            image_urls = user_doc.to_dict().get('images', [])
            for image_url in image_urls:
                print("다운로드할 이미지 URL:", image_url)
                local_path = self.processor.download_image(image_url)
                if local_path:
                    self.processor.image_info_to_db(local_path)
        else:
            print("해당 사용자 문서를 찾을 수 없습니다.")


def read_uid_from_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    uid_file_path = os.path.abspath(os.path.join(base_dir, '..', 'sharing', 'uid.txt'))
    
    try:
        with open(uid_file_path, 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        print(f"UID 파일을 찾을 수 없습니다. 경로를 확인하세요: {uid_file_path}")
        return None

if __name__ == "__main__":
    app = QApplication(sys.argv)  # QApplication 인스턴스 생성
    user_uid = read_uid_from_file()
    if user_uid:
        downloader = ImageDownloader(user_uid)
        downloader.fetch_images()
    sys.exit(app.exec_())