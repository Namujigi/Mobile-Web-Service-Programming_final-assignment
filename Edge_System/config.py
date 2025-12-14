"""
낙상 감지 Edge System 설정 파일
"""

import os

# Django 서버 설정
DJANGO_SERVER_URL = "http://localhost:8000"  # Django 서버 주소 (실제 배포 시 변경 필요)
API_ENDPOINT = f"{DJANGO_SERVER_URL}/api_root/Post/"
AUTHOR_ID = 1  # Django User ID (실제 사용자 ID로 변경 필요)

# 카메라 설정
CAMERA_SOURCE = 0  # 0: 웹캠, 또는 RTSP URL
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
FPS = 30

# YOLO 모델 경로
YOLOV5_MODEL = "yolov5s.pt"  # YOLOv5 모델 (person detection)
YOLOV8_POSE_MODEL = "yolov8n-pose.pt"  # YOLOv8-pose 모델

# 감지 설정
PERSON_CONFIDENCE_THRESHOLD = 0.5  # 사람 감지 신뢰도 임계값
POSE_CONFIDENCE_THRESHOLD = 0.5  # 포즈 감지 신뢰도 임계값

# 낙상 감지 파라미터
FALL_DETECTION_PARAMS = {
    'aspect_ratio_threshold': 1.5,  # 가로/세로 비율 임계값 (누운 자세 판단)
    'height_ratio_threshold': 0.4,  # 바운딩 박스 높이 비율 (화면 대비)
    'keypoint_height_threshold': 0.3,  # 주요 키포인트의 높이 비율
    'fall_duration_frames': 15,  # 낙상으로 판단하기 위한 최소 프레임 수 (약 0.5초)
    'cooldown_frames': 150  # 낙상 감지 후 다음 감지까지 대기 프레임 (약 5초)
}

# 알림 설정
SAVE_FALL_IMAGES = True  # 낙상 이미지 저장 여부
FALL_IMAGES_DIR = "fall_detections"  # 낙상 이미지 저장 디렉토리

# 디버그 설정
DEBUG_MODE = True  # True: 화면에 바운딩 박스와 스켈레톤 표시
SHOW_FPS = True  # FPS 표시 여부
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR

# 디렉토리 생성
if SAVE_FALL_IMAGES and not os.path.exists(FALL_IMAGES_DIR):
    os.makedirs(FALL_IMAGES_DIR)
