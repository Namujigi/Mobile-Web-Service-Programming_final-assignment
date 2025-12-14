# 고령자 낙상 감지 Edge System

YOLOv5 + YOLOv8-pose를 활용한 실시간 고령자 낙상 감지 시스템입니다.

## 시스템 개요

카메라를 통해 실시간으로 고령자의 움직임을 모니터링하고, 낙상이 감지되면 자동으로 Django 서버에 알림을 전송하여 보호자가 신속하게 대응할 수 있도록 합니다.

## 주요 기능

- **실시간 사람 감지**: YOLOv5를 사용하여 프레임에서 사람을 감지
- **포즈 추정**: YOLOv8-pose를 사용하여 17개 키포인트 기반 포즈 추정
- **낙상 감지**: 다중 알고리즘을 통한 낙상 판단
  - 바운딩 박스 가로/세로 비율 분석
  - 신체 키포인트 높이 분석
  - 몸통 각도 분석
- **자동 알림**: 낙상 감지 시 Django 서버로 HTTP POST 요청
- **이미지 저장**: 낙상 순간 이미지 자동 저장
- **실시간 시각화**: 디버그 모드에서 바운딩 박스 및 스켈레톤 표시

## 낙상 감지 알고리즘

### 1. 바운딩 박스 비율 분석
사람의 바운딩 박스 가로/세로 비율이 1.5 이상인 경우 누운 자세로 판단합니다.

### 2. 위치 분석
바운딩 박스의 중심이 프레임 하단 40% 이내에 위치하면 낮은 위치로 판단합니다.

### 3. 키포인트 분석
- 머리와 엉덩이의 상대적 수직 거리 측정
- 몸통(어깨-엉덩이)의 각도 계산
- 수평에 가까운 각도(60도 이상)일 경우 낙상으로 판단

### 4. 연속 프레임 검증
15프레임(약 0.5초) 이상 낙상 조건이 유지되어야 낙상으로 확정합니다.

### 5. 쿨다운 메커니즘
낙상 감지 후 150프레임(약 5초) 동안 재감지를 방지하여 중복 알림을 방지합니다.

## 디렉토리 구조

```
Edge_System/
├── main.py                 # 메인 실행 스크립트
├── config.py               # 시스템 설정
├── fall_detector.py        # 낙상 감지 핵심 로직
├── pose_analyzer.py        # 포즈 분석 모듈
├── api_client.py           # Django API 통신 모듈
├── requirements.txt        # Python 의존성
├── README.md               # 본 문서
└── fall_detections/        # 낙상 이미지 저장 디렉토리 (자동 생성)
```

## 설치 방법

### 1. Python 환경 준비
Python 3.8 이상이 필요합니다.

```bash
python --version
```

### 2. 의존성 설치

```bash
cd Edge_System
pip install -r requirements.txt
```

### 3. YOLO 모델 다운로드

시스템을 처음 실행하면 자동으로 모델이 다운로드됩니다:
- YOLOv5s (사람 감지)
- YOLOv8n-pose (포즈 추정)

또는 수동으로 다운로드:

```bash
# YOLOv5
wget https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt

# YOLOv8-pose
pip install ultralytics
# 첫 실행 시 자동 다운로드됨
```

## 설정

`config.py` 파일에서 다음 설정을 수정하세요:

### Django 서버 설정
```python
DJANGO_SERVER_URL = "http://localhost:8000"  # Django 서버 주소
AUTHOR_ID = 1  # Django User ID
```

### 카메라 설정
```python
CAMERA_SOURCE = 0  # 0: 기본 웹캠, 또는 RTSP URL
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
FPS = 30
```

### 낙상 감지 파라미터
```python
FALL_DETECTION_PARAMS = {
    'aspect_ratio_threshold': 1.5,      # 가로/세로 비율 임계값
    'height_ratio_threshold': 0.4,      # 높이 비율 임계값
    'keypoint_height_threshold': 0.3,   # 키포인트 높이 임계값
    'fall_duration_frames': 15,         # 낙상 판단 최소 프레임
    'cooldown_frames': 150              # 쿨다운 프레임
}
```

## 실행 방법

### 기본 실행 (웹캠 사용)
```bash
python main.py
```

### RTSP 카메라 사용
```bash
python main.py --camera "rtsp://username:password@ip:port/stream"
```

### 디버그 모드
```bash
python main.py --debug
```

### 종료
실행 중 `q` 키를 누르면 시스템이 종료됩니다.

## Django 서버 연동

### 1. Django 서버 실행
먼저 Service_System의 Django 서버를 실행해야 합니다:

```bash
cd ../Service_System
python manage.py runserver
```

### 2. API 엔드포인트
Edge System은 다음 엔드포인트로 POST 요청을 전송합니다:
- URL: `http://localhost:8000/api_root/Post/`
- Method: POST
- Data:
  - `author`: 사용자 ID
  - `title`: 게시글 제목
  - `text`: 낙상 상세 정보
  - `image`: 낙상 이미지 (파일)
  - `published_date`: 발생 시각

### 3. 연결 테스트
시스템 시작 시 자동으로 Django 서버 연결을 테스트합니다.
연결 실패 시 오프라인 모드로 동작하며, 이미지만 로컬에 저장됩니다.

## 낙상 감지 예시

낙상이 감지되면 다음과 같이 Django 서버로 게시글이 생성됩니다:

**제목**: `[긴급] 낙상 감지 알림 - 2025-12-15 14:30:45`

**내용**:
```
낙상이 감지되었습니다!

발생 시각: 2025-12-15 14:30:45

감지 상세 정보:
- 낙상 점수: 0.85
- 바운딩 박스 가로/세로 비율: 2.3
- 몸통 각도: 75.2도
- 감지 근거: Wide bbox; Low position; Horizontal body;

위험도: 높음

즉시 확인이 필요합니다!
```

## 시스템 요구사항

### 하드웨어
- CPU: Intel i5 이상 또는 동급 (GPU 권장)
- RAM: 4GB 이상 (8GB 권장)
- GPU: NVIDIA GPU (CUDA 지원) - 선택사항이지만 실시간 처리 성능 향상
- 카메라: USB 웹캠 또는 RTSP 지원 IP 카메라

### 소프트웨어
- OS: Windows 10/11, Ubuntu 20.04 이상, macOS 11 이상
- Python: 3.8 이상
- CUDA: 11.7 이상 (GPU 사용 시)

## 성능 최적화

### GPU 사용
NVIDIA GPU가 있는 경우 자동으로 CUDA를 사용합니다.
```python
# config.py에서 확인
import torch
print(torch.cuda.is_available())  # True면 GPU 사용 가능
```

### 모델 경량화
더 빠른 처리를 위해 경량 모델 사용:
- `yolov5n.pt` (nano) 대신 `yolov5s.pt` (small) 사용
- `yolov8n-pose.pt` (nano) 사용 중

### 해상도 조정
```python
# config.py
CAMERA_WIDTH = 640  # 낮추면 더 빠름 (예: 320)
CAMERA_HEIGHT = 480  # 낮추면 더 빠름 (예: 240)
```

## 트러블슈팅

### 1. 카메라가 열리지 않음
```
RuntimeError: Failed to open camera
```
- 카메라가 제대로 연결되어 있는지 확인
- 다른 프로그램에서 카메라를 사용 중인지 확인
- `config.CAMERA_SOURCE` 값 확인 (0, 1, 2 등 다른 번호 시도)

### 2. Django 서버 연결 실패
```
Connection error: Cannot connect to http://localhost:8000
```
- Django 서버가 실행 중인지 확인
- `config.DJANGO_SERVER_URL` 주소 확인
- 방화벽 설정 확인

### 3. 모델 로드 실패
```
Error loading models
```
- 인터넷 연결 확인 (모델 자동 다운로드)
- PyTorch 및 ultralytics 설치 확인
- CUDA/GPU 드라이버 확인 (GPU 사용 시)

### 4. 낮은 FPS
- GPU 사용 확인
- 카메라 해상도 낮추기
- 경량 모델 사용
- 디버그 모드 비활성화

## 로그 및 디버깅

### 로그 레벨 설정
```python
# config.py
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

### 디버그 모드
디버그 모드에서는 다음 정보가 화면에 표시됩니다:
- 바운딩 박스 (녹색: 정상, 빨강: 낙상)
- 스켈레톤 (17개 키포인트 연결)
- 낙상 점수
- FPS
- 시스템 시각

## 라이센스 및 참고

### 사용 모델
- [YOLOv5](https://github.com/ultralytics/yolov5) by Ultralytics
- [YOLOv8-pose](https://github.com/ultralytics/ultralytics) by Ultralytics

### 프로젝트 정보
- 과목: 모바일/웹 서비스 프로그래밍
- 주제: 고령자 낙상 감지 시스템
- 학번: 2020105587
- 이름: 김남호

## 향후 개선 사항

- [ ] 다중 사람 동시 모니터링
- [ ] SMS/이메일 알림 기능
- [ ] 낙상 이력 통계 및 분석
- [ ] 모바일 앱 연동
- [ ] 딥러닝 기반 낙상 분류 모델 추가
- [ ] 실시간 웹 스트리밍 기능

## 문의

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해주세요.
