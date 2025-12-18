"""
낙상 감지 Edge System 설정 파일
YOLOv11n-pose 단독 사용
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment variables from {env_path}")
else:
    print(f"⚠ .env file not found at {env_path}")
    print("  Using default values. Create .env file for production.")

# Django 서버 설정 (.env에서 로드)
DJANGO_SERVER_URL = os.getenv('DJANGO_SERVER_URL', 'http://localhost:8000')
API_ENDPOINT = f"{DJANGO_SERVER_URL}/api_root/Post/"
AUTHOR_ID = int(os.getenv('AUTHOR_ID', '1'))

# API 인증 토큰 (.env에서 로드)
API_TOKEN = os.getenv('API_TOKEN', '')

if not API_TOKEN:
    print("⚠ Warning: API_TOKEN not set in .env file")
    print("  Admin authentication required. See .env.example for setup instructions.")

# 카메라 설정
CAMERA_SOURCE = 0 # USB 웹캠 사용
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
FPS = 30

# YOLO 모델 경로 (YOLOv11n-pose 단독 사용)
YOLO_POSE_MODEL = "yolov11n-pose.pt"  # YOLOv11-pose 모델

# 감지 설정
POSE_CONFIDENCE_THRESHOLD = 0.5  # 포즈 감지 신뢰도 임계값
KEYPOINT_CONFIDENCE_THRESHOLD = 0.3  # 개별 키포인트 신뢰도

# 낙상 감지 파라미터
FALL_DETECTION_PARAMS = {
    # 바운딩 박스 기반 분석
    'aspect_ratio_threshold': 1.5,  # 가로/세로 비율 임계값 (누운 자세)
    'bbox_height_ratio_threshold': 0.4,  # 바운딩 박스 높이 비율 (화면 하단 40%)

    # 키포인트 기반 분석
    'keypoint_height_threshold': 0.6,  # 주요 키포인트의 높이 비율 (화면 하단 60%)
    'horizontal_threshold': 0.3,  # 머리-엉덩이 수직 거리 비율
    'body_angle_threshold': 45,  # 몸통 각도 임계값 (도)

    # 시간 기반 필터링
    'fall_duration_frames': 15,  # 낙상 확정 최소 프레임 수 (약 0.5초 (30fps 기준))
    'cooldown_frames': 150,  # 낙상 감지 후 쿨다운 (약 5초 (30fps 기준))

    # 낙상 점수 가중치 (합계 = 1.0)
    'weights': {
        'aspect_ratio': 0.35,      # 가로/세로 비율 가중치
        'low_position': 0.20,      # 낮은 위치 가중치
        'horizontal_body': 0.25,   # 수평 자세 가중치
        'body_angle': 0.20         # 몸통 각도 가중치
    },

    # 낙상 점수 임계값
    'fall_score_threshold': 0.6  # 이 점수 이상이면 낙상으로 판단
}

# 알림 설정
SAVE_FALL_IMAGES = True  # 낙상 이미지 저장 여부
FALL_IMAGES_DIR = "fall_detections"  # 낙상 이미지 저장 디렉토리
SAVE_FALL_VIDEOS = True  # 낙상 비디오 저장 여부
FALL_VIDEOS_DIR = "fall_videos"  # 낙상 비디오 저장 디렉토리

# 비디오 녹화 설정
VIDEO_BUFFER_SECONDS = 7  # 낙상 감지 전 버퍼 시간 (초)
VIDEO_RECORD_AFTER_SECONDS = 5  # 낙상 감지 후 녹화 시간 (초)
VIDEO_CODEC = 'mp4v'  # 비디오 코덱 (mp4v, H264, XVID)
VIDEO_FPS = 30  # 비디오 FPS

# 디버그 설정
DEBUG_MODE = True  # True: 화면에 바운딩 박스와 스켈레톤 표시
SHOW_FPS = True  # FPS 표시 여부
SHOW_FALL_SCORE = True  # 낙상 점수 실시간 표시
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR

# 성능 최적화
USE_HALF_PRECISION = False  # FP16 사용 (GPU 메모리 절약, 속도 향상)
IMGSZ = 640  # 입력 이미지 크기 (640, 480, 320 등)

# 디렉토리 생성
if SAVE_FALL_IMAGES and not os.path.exists(FALL_IMAGES_DIR):
    os.makedirs(FALL_IMAGES_DIR)

if SAVE_FALL_VIDEOS and not os.path.exists(FALL_VIDEOS_DIR):
    os.makedirs(FALL_VIDEOS_DIR)
