import sys
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

class ImageDisplay(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        
        self.setWindowTitle("Image Display")
        self.setGeometry(100, 100, 800, 600)  # 화면 크기 설정
        
        self.label = QLabel(self)
        pixmap = QPixmap(image_path)
        self.label.setPixmap(pixmap)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setScaledContents(True)

        self.setCentralWidget(self.label)

    def mousePressEvent(self, event):
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    image_path = 'images/2.png'
    window = ImageDisplay(image_path)
    window.showFullScreen()  # 전체화면으로 표시
    sys.exit(app.exec_())
