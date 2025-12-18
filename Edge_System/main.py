"""
고령자 낙상 감지 Edge System
YOLOv11n-pose 단독 사용 버전
"""

import cv2
import logging
import time
import argparse
from datetime import datetime
from collections import deque
from pathlib import Path

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
        logger.info("="*60)
        logger.info("Fall Detection System - YOLOv11n-pose Single Model")
        logger.info("="*60)

        # 카메라 소스 설정
        self.camera_source = camera_source if camera_source is not None else config.CAMERA_SOURCE

        # 낙상 감지기 초기화
        self.detector = FallDetector(config)

        # 모델 정보 출력
        model_info = self.detector.get_model_info()
        logger.info(f"Model: {model_info['model_name']}")
        logger.info(f"Device: {model_info['device']}")
        logger.info(f"Capabilities: {', '.join(model_info['capabilities'])}")

        # API 클라이언트 초기화
        self.api_client = DjangoAPIClient(config)

        # 카메라 초기화
        self.cap = None
        self.init_camera()

        # FPS 계산용
        self.fps = 0
        self.frame_count = 0
        self.start_time = time.time()

        # 통계
        self.stats = {
            'total_frames': 0,
            'total_detections': 0,
            'total_falls': 0
        }

        # 비디오 녹화용 프레임 버퍼 (낙상 감지 전 7초 저장)
        buffer_size = int(config.VIDEO_FPS * config.VIDEO_BUFFER_SECONDS)
        self.frame_buffer = deque(maxlen=buffer_size)

        # 낙상 감지 후 녹화 상태
        self.recording_fall = False
        self.fall_video_frames = []
        self.frames_after_fall = 0
        self.frames_to_record_after = int(config.VIDEO_FPS * config.VIDEO_RECORD_AFTER_SECONDS)
        self.current_fall_info = None

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

        # 실제 설정된 값 확인
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))

        logger.info(f"Camera resolution: {actual_width}x{actual_height} @ {actual_fps}fps")

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
        logger.info("Press 'q' to quit, 's' to show statistics")

        # API 연결 테스트
        if not self.api_client.test_connection():
            logger.warning("Cannot connect to Django server. System will run in offline mode.")

        try:
            while True:
                ret, frame = self.cap.read()

                if not ret:
                    logger.error("Failed to read frame from camera")
                    break

                self.stats['total_frames'] += 1

                # 낙상 감지 처리
                processed_frame, is_fall_detected, fall_info = self.detector.process_frame(frame)

                # 프레임 버퍼에 원본 프레임 저장 (낙상 감지 전 5초 보관)
                if not self.recording_fall:
                    self.frame_buffer.append(frame.copy())

                # 낙상 감지 시 처리
                if is_fall_detected and not self.recording_fall:
                    self.stats['total_falls'] += 1
                    self.recording_fall = True
                    self.current_fall_info = fall_info
                    self.frames_after_fall = 0
                    # 버퍼의 프레임들을 비디오 프레임 리스트로 복사 (낙상 전 5초)
                    self.fall_video_frames = list(self.frame_buffer)
                    logger.info(f"Started recording fall video. Buffer frames: {len(self.fall_video_frames)}")

                # 낙상 감지 후 추가 녹화
                if self.recording_fall:
                    self.fall_video_frames.append(frame.copy())
                    self.frames_after_fall += 1

                    # 낙상 후 5초 녹화 완료
                    if self.frames_after_fall >= self.frames_to_record_after:
                        logger.info(f"Finished recording fall video. Total frames: {len(self.fall_video_frames)}")
                        self.handle_fall_detection(self.current_fall_info, self.fall_video_frames)
                        # 녹화 상태 초기화
                        self.recording_fall = False
                        self.fall_video_frames = []
                        self.current_fall_info = None

                # FPS 표시
                if config.SHOW_FPS:
                    fps = self.calculate_fps()
                    cv2.putText(processed_frame, f"FPS: {fps:.1f}",
                              (10, processed_frame.shape[0] - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 시스템 정보 표시
                if config.DEBUG_MODE:
                    model_name = config.YOLO_POSE_MODEL.replace('.pt', '')
                    info_text = f"{model_name} - {datetime.now().strftime('%H:%M:%S')}"
                    cv2.putText(processed_frame, info_text,
                              (10, processed_frame.shape[0] - 40),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                    # 통계 표시
                    stats_text = f"Detections: {self.stats['total_detections']} | Falls: {self.stats['total_falls']}"
                    cv2.putText(processed_frame, stats_text,
                              (10, processed_frame.shape[0] - 70),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # 화면 표시
                cv2.imshow('Fall Detection System', processed_frame)

                # 키보드 입력 처리
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    logger.info("User requested quit")
                    break
                elif key == ord('s'):
                    self.print_statistics()

        except KeyboardInterrupt:
            logger.info("System interrupted by user")

        finally:
            self.cleanup()

    def handle_fall_detection(self, fall_info: dict, video_frames: list = None):
        """낙상 감지 처리"""
        logger.warning("=" * 60)
        logger.warning("FALL DETECTED!")
        logger.warning(f"Time: {fall_info['timestamp']}")
        logger.warning(f"Confidence: {fall_info['confidence']:.2f}")
        logger.warning(f"Fall Score: {fall_info['analysis']['fall_score']:.2f}")
        logger.warning(f"Reason: {fall_info['analysis']['reason']}")
        logger.warning("=" * 60)

        # 낙상 이미지 저장 (썸네일용)
        image_path = self.detector.save_fall_image(fall_info)

        # 낙상 비디오 저장 (12초)
        video_path = None
        if video_frames and config.SAVE_FALL_VIDEOS:
            video_path = self.save_fall_video(fall_info, video_frames)

        # Django 서버로 알림 전송 (이미지 + 비디오)
        try:
            success = self.api_client.create_fall_alert(fall_info, image_path, video_path)

            if success:
                logger.info("Fall alert sent to Django server successfully")
            else:
                logger.error("Failed to send fall alert to Django server")

        except Exception as e:
            logger.error(f"Error sending fall alert: {e}")

    def save_fall_video(self, fall_info: dict, video_frames: list) -> str:
        """낙상 비디오 저장 (12초)"""
        timestamp = fall_info['timestamp'].strftime("%Y%m%d_%H%M%S")
        video_filename = f"fall_{timestamp}.mp4"
        video_path = Path(config.FALL_VIDEOS_DIR) / video_filename

        try:
            # 비디오 작성기 초기화
            height, width = video_frames[0].shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*config.VIDEO_CODEC)
            video_writer = cv2.VideoWriter(
                str(video_path),
                fourcc,
                config.VIDEO_FPS,
                (width, height)
            )

            # 프레임 쓰기
            for frame in video_frames:
                video_writer.write(frame)

            video_writer.release()
            logger.info(f"Fall video saved: {video_path} ({len(video_frames)} frames)")
            return str(video_path)

        except Exception as e:
            logger.error(f"Error saving fall video: {e}")
            return None

    def print_statistics(self):
        """통계 출력"""
        logger.info("=" * 60)
        logger.info("SYSTEM STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total frames processed: {self.stats['total_frames']}")
        logger.info(f"Total detections: {self.stats['total_detections']}")
        logger.info(f"Total falls detected: {self.stats['total_falls']}")
        logger.info(f"Average FPS: {self.fps:.1f}")
        logger.info("=" * 60)

    def cleanup(self):
        """리소스 정리"""
        logger.info("Cleaning up resources...")

        # 최종 통계 출력
        self.print_statistics()

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
    parser.add_argument('--model', type=str, default='yolov11n-pose.pt',
                       choices=['yolov11n-pose.pt', 'yolov8n-pose.pt'],
                       help='YOLO-pose model to use')

    args = parser.parse_args()

    # 디버그 모드 설정
    if args.debug:
        config.DEBUG_MODE = True
        logging.getLogger().setLevel(logging.DEBUG)

    # 모델 설정
    config.YOLO_POSE_MODEL = args.model
    logger.info(f"Using model: {config.YOLO_POSE_MODEL}")

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
