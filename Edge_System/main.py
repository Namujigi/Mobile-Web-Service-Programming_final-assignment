"""
고령자 낙상 감지 Edge System
YOLOv5 + YOLOv8-pose를 활용한 실시간 낙상 감지 및 Django 서버 알림
"""

import cv2
import logging
import time
import argparse
from datetime import datetime

import config
from fall_detector import FallDetector
from api_client import DjangoAPIClient

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FallDetectionSystem:
    """낙상 감지 시스템 메인 클래스"""

    def __init__(self, camera_source=None):
        logger.info("Initializing Fall Detection System...")

        # 카메라 소스 설정
        self.camera_source = camera_source if camera_source is not None else config.CAMERA_SOURCE

        # 낙상 감지기 초기화
        self.detector = FallDetector(config)

        # API 클라이언트 초기화
        self.api_client = DjangoAPIClient(config)

        # 카메라 초기화
        self.cap = None
        self.init_camera()

        # FPS 계산용
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()

        logger.info("System initialized successfully")

    def init_camera(self):
        """카메라 초기화"""
        logger.info(f"Initializing camera: {self.camera_source}")

        self.cap = cv2.VideoCapture(self.camera_source)

        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open camera: {self.camera_source}")

        # 카메라 설정
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.FPS)

        logger.info("Camera initialized successfully")

    def calculate_fps(self):
        """FPS 계산"""
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time

        if elapsed_time >= 1.0:
            self.fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.start_time = time.time()

        return self.fps

    def run(self):
        """메인 루프 실행"""
        logger.info("Starting fall detection system...")
        logger.info("Press 'q' to quit")

        # API 연결 테스트
        if not self.api_client.test_connection():
            logger.warning("Cannot connect to Django server. System will run in offline mode.")

        try:
            while True:
                ret, frame = self.cap.read()

                if not ret:
                    logger.error("Failed to read frame from camera")
                    break

                # 낙상 감지 처리
                processed_frame, is_fall_detected, fall_info = self.detector.process_frame(frame)

                # 낙상 감지 시 처리
                if is_fall_detected:
                    self.handle_fall_detection(fall_info)

                # FPS 표시
                if config.SHOW_FPS:
                    fps = self.calculate_fps()
                    cv2.putText(processed_frame, f"FPS: {fps:.1f}",
                              (10, processed_frame.shape[0] - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 시스템 정보 표시
                if config.DEBUG_MODE:
                    info_text = f"Fall Detection System - {datetime.now().strftime('%H:%M:%S')}"
                    cv2.putText(processed_frame, info_text,
                              (10, processed_frame.shape[0] - 40),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # 화면 표시
                cv2.imshow('Fall Detection System', processed_frame)

                # 'q' 키로 종료
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logger.info("User requested quit")
                    break

        except KeyboardInterrupt:
            logger.info("System interrupted by user")

        finally:
            self.cleanup()

    def handle_fall_detection(self, fall_info: dict):
        """낙상 감지 처리"""
        logger.warning("=" * 50)
        logger.warning("FALL DETECTED!")
        logger.warning(f"Time: {fall_info['timestamp']}")
        logger.warning(f"Analysis: {fall_info['analysis']}")
        logger.warning("=" * 50)

        # 낙상 이미지 저장
        image_path = self.detector.save_fall_image(fall_info)

        # Django 서버로 알림 전송
        try:
            success = self.api_client.create_fall_alert(fall_info, image_path)

            if success:
                logger.info("Fall alert sent to Django server successfully")
            else:
                logger.error("Failed to send fall alert to Django server")

        except Exception as e:
            logger.error(f"Error sending fall alert: {e}")

    def cleanup(self):
        """리소스 정리"""
        logger.info("Cleaning up resources...")

        if self.cap is not None:
            self.cap.release()

        cv2.destroyAllWindows()
        logger.info("System shutdown complete")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='Fall Detection System')
    parser.add_argument('--camera', type=str, default=None,
                       help='Camera source (0 for webcam, or RTSP URL)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')

    args = parser.parse_args()

    # 디버그 모드 설정
    if args.debug:
        config.DEBUG_MODE = True
        logging.getLogger().setLevel(logging.DEBUG)

    # 카메라 소스 파싱
    camera_source = args.camera
    if camera_source is not None:
        try:
            camera_source = int(camera_source)
        except ValueError:
            pass  # RTSP URL 등 문자열 유지

    # 시스템 실행
    try:
        system = FallDetectionSystem(camera_source=camera_source)
        system.run()

    except Exception as e:
        logger.error(f"System error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
