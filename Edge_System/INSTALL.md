# 설치 가이드

## 빠른 시작

### 1. Python 설치 확인
```bash
python --version
# Python 3.8 이상 필요
```

### 2. 가상환경 생성 (권장)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 시스템 테스트
```bash
python test_system.py
```

### 5. Django 서버 설정
`config.py` 파일을 열어 Django 서버 주소를 설정하세요:
```python
DJANGO_SERVER_URL = "http://localhost:8000"  # Django 서버 주소
AUTHOR_ID = 1  # Django User ID
```

### 6. 시스템 실행
```bash
python main.py
```

## 상세 설치 가이드

### Windows

#### 1. Python 설치
1. [Python 공식 웹사이트](https://www.python.org/downloads/)에서 Python 3.8 이상 다운로드
2. 설치 시 "Add Python to PATH" 체크

#### 2. Visual C++ 재배포 패키지 설치
OpenCV 사용을 위해 필요:
- [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

#### 3. CUDA 설치 (GPU 사용 시)
1. [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) 다운로드
2. [cuDNN](https://developer.nvidia.com/cudnn) 다운로드 및 설치

#### 4. 설치 명령어
```cmd
# 가상환경 생성
python -m venv venv
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 테스트
python test_system.py
```

### Linux (Ubuntu/Debian)

#### 1. 시스템 패키지 업데이트
```bash
sudo apt update
sudo apt upgrade
```

#### 2. Python 및 필수 패키지 설치
```bash
sudo apt install python3 python3-pip python3-venv
sudo apt install python3-dev build-essential
sudo apt install libopencv-dev python3-opencv
```

#### 3. CUDA 설치 (GPU 사용 시)
```bash
# NVIDIA 드라이버 설치
sudo apt install nvidia-driver-525

# CUDA Toolkit 설치
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/12.2.0/local_installers/cuda-repo-ubuntu2204-12-2-local_12.2.0-535.54.03-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-12-2-local_12.2.0-535.54.03-1_amd64.deb
sudo cp /var/cuda-repo-ubuntu2204-12-2-local/cuda-*-keyring.gpg /usr/share/keyrings/
sudo apt-get update
sudo apt-get install cuda
```

#### 4. 설치 명령어
```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 테스트
python test_system.py
```

### macOS

#### 1. Homebrew 설치
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 2. Python 설치
```bash
brew install python@3.11
```

#### 3. 설치 명령어
```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 테스트
python test_system.py
```

## GPU 가속 설정

### NVIDIA GPU 확인
```bash
nvidia-smi
```

### PyTorch CUDA 버전 확인
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

### GPU 버전 PyTorch 설치
```bash
# CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## 카메라 설정

### USB 카메라
대부분의 USB 웹캠은 자동으로 인식됩니다:
```python
# config.py
CAMERA_SOURCE = 0  # 첫 번째 카메라
CAMERA_SOURCE = 1  # 두 번째 카메라
```

### RTSP 카메라
IP 카메라 사용 시:
```python
# config.py
CAMERA_SOURCE = "rtsp://username:password@192.168.1.100:554/stream"
```

### 카메라 테스트
```bash
python -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAIL')"
```

## Django 서버 연동

### 1. Django 서버 실행
```bash
cd ../Service_System
python manage.py runserver
```

### 2. 사용자 생성 (처음 실행 시)
```bash
python manage.py createsuperuser
```

### 3. config.py 설정
생성한 사용자의 ID를 확인하여 설정:
```python
AUTHOR_ID = 1  # 사용자 ID
```

## 트러블슈팅

### "No module named 'torch'" 오류
```bash
pip install torch torchvision
```

### "OpenCV cannot open camera" 오류
1. 다른 프로그램에서 카메라 사용 중인지 확인
2. 카메라 번호 변경 시도 (0, 1, 2)
3. 권한 확인:
   ```bash
   # Linux
   sudo usermod -a -G video $USER
   ```

### "CUDA out of memory" 오류
1. 경량 모델 사용:
   ```python
   YOLOV5_MODEL = "yolov5n.pt"  # nano 모델
   ```
2. 배치 크기 줄이기
3. 해상도 낮추기:
   ```python
   CAMERA_WIDTH = 320
   CAMERA_HEIGHT = 240
   ```

### Django 서버 연결 실패
1. 서버 실행 확인:
   ```bash
   curl http://localhost:8000
   ```
2. 방화벽 확인
3. URL 확인:
   ```python
   DJANGO_SERVER_URL = "http://127.0.0.1:8000"
   ```

## 시스템 요구사항 확인

### 최소 요구사항
- CPU: Intel i3 이상
- RAM: 4GB
- 저장공간: 2GB
- 카메라: USB 웹캠

### 권장 요구사항
- CPU: Intel i5 이상
- RAM: 8GB
- GPU: NVIDIA GTX 1050 이상
- 저장공간: 5GB
- 카메라: Full HD 웹캠 또는 IP 카메라

## 다음 단계

설치가 완료되면 [README.md](README.md)를 참고하여 시스템을 실행하세요.
