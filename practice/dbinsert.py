import sqlite_utils

db = sqlite_utils.Database("local.db")

row_data = {
    "id": 2,
    "title": "4.jpg",
    "image": "/home/jetson/Desktop/khj/Display/album/4.jpg",
    "season": "겨울",
    "date": "2023:07:30 14:29:11",
    "gps": "[37.542938888888884, 127.05265]",  # GPS 좌표는 문자열로 저장
    "address": "서울특별시 성동구 성수동2가",
    "tags": "고양이"
}

# 행 추가
db["album"].insert(row_data)