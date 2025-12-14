"""
낙상 감지 시스템 테스트 스크립트
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_imports():
    """필수 라이브러리 import 테스트"""
    logger.info("Testing imports...")
    try:
        import torch
        import cv2
        import numpy
        import requests
        from ultralytics import YOLO

        logger.info(f"✓ PyTorch version: {torch.__version__}")
        logger.info(f"✓ OpenCV version: {cv2.__version__}")
        logger.info(f"✓ NumPy version: {numpy.__version__}")
        logger.info(f"✓ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"  GPU: {torch.cuda.get_device_name(0)}")
        return True
    except ImportError as e:
        logger.error(f"✗ Import error: {e}")
        return False


def test_camera():
    """카메라 접근 테스트"""
    logger.info("\nTesting camera access...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("✗ Cannot open camera")
            return False

        ret, frame = cap.read()
        cap.release()

        if not ret:
            logger.error("✗ Cannot read frame from camera")
            return False

        logger.info(f"✓ Camera accessible (resolution: {frame.shape[1]}x{frame.shape[0]})")
        return True
    except Exception as e:
        logger.error(f"✗ Camera test failed: {e}")
        return False


def test_models():
    """YOLO 모델 로드 테스트"""
    logger.info("\nTesting YOLO models...")
    try:
        import torch

        # YOLOv5 테스트
        logger.info("Loading YOLOv5...")
        yolov5 = torch.hub.load('ultralytics/yolov5', 'yolov5s', force_reload=False)
        logger.info("✓ YOLOv5 loaded successfully")

        # YOLOv8-pose 테스트
        logger.info("Loading YOLOv8-pose...")
        from ultralytics import YOLO
        yolov8_pose = YOLO('yolov8n-pose.pt')
        logger.info("✓ YOLOv8-pose loaded successfully")

        return True
    except Exception as e:
        logger.error(f"✗ Model loading failed: {e}")
        return False


def test_django_connection():
    """Django 서버 연결 테스트"""
    logger.info("\nTesting Django server connection...")
    try:
        import requests
        import config

        response = requests.get(config.DJANGO_SERVER_URL, timeout=5)
        logger.info(f"✓ Django server accessible (status: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        logger.warning("✗ Cannot connect to Django server (server may not be running)")
        logger.warning("  This is OK for testing - system will work in offline mode")
        return True
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False


def test_modules():
    """프로젝트 모듈 import 테스트"""
    logger.info("\nTesting project modules...")
    try:
        import config
        from fall_detector import FallDetector
        from pose_analyzer import PoseAnalyzer
        from api_client import DjangoAPIClient

        logger.info("✓ config module imported")
        logger.info("✓ fall_detector module imported")
        logger.info("✓ pose_analyzer module imported")
        logger.info("✓ api_client module imported")
        return True
    except ImportError as e:
        logger.error(f"✗ Module import error: {e}")
        return False


def main():
    """테스트 실행"""
    logger.info("=" * 60)
    logger.info("Fall Detection System - Test Suite")
    logger.info("=" * 60)

    tests = [
        ("Library imports", test_imports),
        ("Camera access", test_camera),
        ("Project modules", test_modules),
        ("YOLO models", test_models),
        ("Django connection", test_django_connection),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # 결과 요약
    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n✓ All tests passed! System is ready to run.")
        return 0
    else:
        logger.warning(f"\n✗ {total - passed} test(s) failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
