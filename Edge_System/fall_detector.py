"""
YOLOv5 + YOLOv8-pose를 활용한 낙상 감지 시스템
"""

import cv2
import torch
import numpy as np
from datetime import datetime
import logging
from typing import Optional, Tuple
from pathlib import Path

from pose_analyzer import PoseAnalyzer

logger = logging.getLogger(__name__)


class FallDetector:
    """낙상 감지 메인 클래스"""

    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

        # YOLO 모델 로드
        self.person_detector = None
        self.pose_detector = None
        self.load_models()

        # 포즈 분석기 초기화
        self.pose_analyzer = PoseAnalyzer(config.FALL_DETECTION_PARAMS)

        # 낙상 감지 상태
        self.fall_frame_count = 0
        self.cooldown_count = 0
        self.last_fall_time = None

    def load_models(self):
        """YOLO 모델 로드"""
        try:
            # YOLOv5 로드 (사람 감지)
            logger.info(f"Loading YOLOv5 model: {self.config.YOLOV5_MODEL}")
            self.person_detector = torch.hub.load('ultralytics/yolov5', 'custom',
                                                  path=self.config.YOLOV5_MODEL,
                                                  force_reload=False)
            self.person_detector.to(self.device)
            self.person_detector.conf = self.config.PERSON_CONFIDENCE_THRESHOLD

            # YOLOv8-pose 로드
            logger.info(f"Loading YOLOv8-pose model: {self.config.YOLOV8_POSE_MODEL}")
            from ultralytics import YOLO
            self.pose_detector = YOLO(self.config.YOLOV8_POSE_MODEL)
            self.pose_detector.to(self.device)

            logger.info("Models loaded successfully")

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise

    def detect_persons(self, frame: np.ndarray) -> list:
        """
        YOLOv5로 프레임에서 사람 감지

        Returns:
            List of bounding boxes [(x1, y1, x2, y2, confidence), ...]
        """
        results = self.person_detector(frame)
        persons = []

        # Class 0 = person in COCO dataset
        for det in results.xyxy[0]:
            if int(det[5]) == 0:  # person class
                x1, y1, x2, y2, conf = det[:5].cpu().numpy()
                persons.append((int(x1), int(y1), int(x2), int(y2), float(conf)))

        return persons

    def estimate_pose(self, frame: np.ndarray) -> Optional[list]:
        """
        YOLOv8-pose로 포즈 추정

        Returns:
            List of pose data [(bbox, keypoints), ...]
            bbox: (x1, y1, x2, y2)
            keypoints: (17, 3) array [x, y, confidence]
        """
        results = self.pose_detector(frame, conf=self.config.POSE_CONFIDENCE_THRESHOLD,
                                     verbose=False)

        pose_data = []
        for result in results:
            if result.keypoints is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                keypoints = result.keypoints.data.cpu().numpy()

                for box, kpts in zip(boxes, keypoints):
                    x1, y1, x2, y2 = box[:4]
                    pose_data.append({
                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                        'keypoints': kpts
                    })

        return pose_data if pose_data else None

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, bool, dict]:
        """
        프레임 처리 및 낙상 감지

        Returns:
            (processed_frame, is_fall_detected, fall_info)
        """
        frame_height, frame_width = frame.shape[:2]
        is_fall_detected = False
        fall_info = {}

        # Cooldown 체크
        if self.cooldown_count > 0:
            self.cooldown_count -= 1
            if self.config.DEBUG_MODE:
                cv2.putText(frame, f"Cooldown: {self.cooldown_count}",
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            return frame, False, {}

        # 포즈 추정
        pose_data = self.estimate_pose(frame)

        if pose_data:
            for data in pose_data:
                bbox = data['bbox']
                keypoints = data['keypoints']

                # 포즈 분석
                analysis = self.pose_analyzer.analyze_pose(keypoints, bbox, frame_height)

                # 디버그 모드: 바운딩 박스 및 스켈레톤 표시
                if self.config.DEBUG_MODE:
                    color = (0, 0, 255) if analysis['is_fall'] else (0, 255, 0)
                    x1, y1, x2, y2 = bbox

                    # 바운딩 박스
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    # 스켈레톤
                    frame = self.pose_analyzer.draw_skeleton(frame, keypoints)

                    # 낙상 점수 표시
                    text = f"Fall Score: {analysis['fall_score']:.2f}"
                    cv2.putText(frame, text, (x1, y1 - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # 낙상 감지
                if analysis['is_fall']:
                    self.fall_frame_count += 1

                    if self.fall_frame_count >= self.config.FALL_DETECTION_PARAMS['fall_duration_frames']:
                        # 낙상 확정
                        is_fall_detected = True
                        fall_info = {
                            'timestamp': datetime.now(),
                            'bbox': bbox,
                            'analysis': analysis,
                            'frame': frame.copy()
                        }

                        # 상태 초기화 및 쿨다운 시작
                        self.fall_frame_count = 0
                        self.cooldown_count = self.config.FALL_DETECTION_PARAMS['cooldown_frames']
                        self.last_fall_time = datetime.now()

                        logger.warning(f"FALL DETECTED! Reason: {analysis['reason']}")

                        if self.config.DEBUG_MODE:
                            cv2.putText(frame, "!!! FALL DETECTED !!!",
                                      (50, 50), cv2.FONT_HERSHEY_SIMPLEX,
                                      1.5, (0, 0, 255), 3)
                        break
                else:
                    # 낙상이 아니면 카운트 리셋
                    self.fall_frame_count = 0

        return frame, is_fall_detected, fall_info

    def save_fall_image(self, fall_info: dict) -> str:
        """낙상 이미지 저장"""
        if not self.config.SAVE_FALL_IMAGES:
            return None

        timestamp = fall_info['timestamp'].strftime("%Y%m%d_%H%M%S")
        filename = f"fall_{timestamp}.jpg"
        filepath = Path(self.config.FALL_IMAGES_DIR) / filename

        cv2.imwrite(str(filepath), fall_info['frame'])
        logger.info(f"Fall image saved: {filepath}")

        return str(filepath)

    def get_fall_description(self, fall_info: dict) -> str:
        """낙상 정보를 텍스트로 변환"""
        analysis = fall_info['analysis']
        timestamp = fall_info['timestamp'].strftime("%Y-%m-%d %H:%M:%S")

        description = f"""
낙상 감지 보고

발생 시각: {timestamp}

감지 상세:
- 낙상 점수: {analysis['fall_score']:.2f}
- 바운딩 박스 가로/세로 비율: {analysis['bbox_aspect_ratio']:.2f}
- 몸통 각도: {analysis['body_angle']:.1f}도
- 위치 비율: {analysis['head_height_ratio']:.2f}

감지 근거: {analysis['reason']}

위험도: {'높음' if analysis['fall_score'] > 0.7 else '중간'}
        """

        return description.strip()
