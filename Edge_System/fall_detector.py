"""
YOLOv11n-pose 단독 사용 낙상 감지 시스템
YOLOv11-pose만으로 사람 감지 + 포즈 추정 + 낙상 감지
"""

import cv2
import torch
import numpy as np
from datetime import datetime
import logging
from typing import Optional, Tuple, List
from pathlib import Path

from pose_analyzer import PoseAnalyzer

logger = logging.getLogger(__name__)


class FallDetector:
    """YOLOv11-pose 단독 사용 낙상 감지 클래스"""

    def __init__(self, config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

        # YOLO-pose 모델 로드 (사람 감지 + 포즈 추정 동시 수행)
        self.pose_model = None
        self.load_model()

        # 포즈 분석기 초기화
        self.pose_analyzer = PoseAnalyzer(config.FALL_DETECTION_PARAMS)

        # 낙상 감지 상태
        self.fall_frame_count = 0
        self.cooldown_count = 0
        self.last_fall_time = None

    def load_model(self):
        """YOLO-pose 모델 로드"""
        try:
            from ultralytics import YOLO

            logger.info(f"Loading {self.config.YOLO_POSE_MODEL}")
            self.pose_model = YOLO(self.config.YOLO_POSE_MODEL)
            self.pose_model.to(self.device)

            # Half precision 사용 (GPU 메모리 절약)
            if self.config.USE_HALF_PRECISION and self.device.type == 'cuda':
                logger.info("Using half precision (FP16)")

            logger.info("Model loaded successfully")
            logger.info(f"Model info: {self.pose_model.info()}")

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

    def detect_and_estimate_pose(self, frame: np.ndarray) -> Optional[List[dict]]:
        """
        YOLO-pose로 사람 감지 + 포즈 추정 동시 수행

        단 하나의 모델로:
        1. 프레임에서 사람 감지 (바운딩 박스)
        2. 각 사람의 17개 키포인트 추정

        Returns:
            List of dict: [{'bbox': (x1,y1,x2,y2), 'keypoints': (17,3), 'conf': float}, ...]
        """
        try:
            # YOLO-pose 추론
            results = self.pose_model(
                frame,
                conf=self.config.POSE_CONFIDENCE_THRESHOLD,
                imgsz=self.config.IMGSZ,
                half=self.config.USE_HALF_PRECISION,
                verbose=False
            )

            detections = []

            for result in results:
                # 사람이 감지되고 키포인트가 있는 경우
                if result.keypoints is not None and len(result.keypoints) > 0:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    keypoints = result.keypoints.data.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()

                    for box, kpts, conf in zip(boxes, keypoints, confidences):
                        x1, y1, x2, y2 = box[:4]
                        detections.append({
                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                            'keypoints': kpts,  # (17, 3) [x, y, confidence]
                            'conf': float(conf)
                        })

            return detections if detections else None

        except Exception as e:
            logger.error(f"Error in detection: {e}")
            return None

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

        # 사람 감지 + 포즈 추정 (단일 모델에서 동시 수행!)
        detections = self.detect_and_estimate_pose(frame)

        if detections:
            for detection in detections:
                bbox = detection['bbox']
                keypoints = detection['keypoints']
                conf = detection['conf']

                # 포즈 분석 (낙상 여부 판단)
                analysis = self.pose_analyzer.analyze_pose(keypoints, bbox, frame_height)

                # 디버그 모드: 시각화
                if self.config.DEBUG_MODE:
                    color = (0, 0, 255) if analysis['is_fall'] else (0, 255, 0)
                    x1, y1, x2, y2 = bbox

                    # 바운딩 박스
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    # 감지 신뢰도 표시
                    cv2.putText(frame, f"Conf: {conf:.2f}",
                              (x1, y1 - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    # 스켈레톤
                    frame = self.pose_analyzer.draw_skeleton(
                        frame, keypoints, self.config.KEYPOINT_CONFIDENCE_THRESHOLD
                    )

                    # 낙상 점수 표시
                    if self.config.SHOW_FALL_SCORE:
                        score_text = f"Fall Score: {analysis['fall_score']:.2f}"
                        cv2.putText(frame, score_text, (x1, y1 - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # 낙상 감지 로직
                if analysis['is_fall']:
                    self.fall_frame_count += 1

                    # 연속 프레임 검증
                    if self.fall_frame_count >= self.config.FALL_DETECTION_PARAMS['fall_duration_frames']:
                        # 낙상 확정!
                        is_fall_detected = True
                        fall_info = {
                            'timestamp': datetime.now(),
                            'bbox': bbox,
                            'confidence': conf,
                            'analysis': analysis,
                            'frame': frame.copy(),
                            'keypoints': keypoints
                        }

                        # 상태 초기화
                        self.fall_frame_count = 0
                        self.cooldown_count = self.config.FALL_DETECTION_PARAMS['cooldown_frames']
                        self.last_fall_time = datetime.now()

                        logger.warning(f"FALL DETECTED! Confidence: {conf:.2f}, "
                                     f"Fall Score: {analysis['fall_score']:.2f}, "
                                     f"Reason: {analysis['reason']}")

                        if self.config.DEBUG_MODE:
                            cv2.putText(frame, "!!! FALL DETECTED !!!",
                                      (50, 50), cv2.FONT_HERSHEY_SIMPLEX,
                                      1.5, (0, 0, 255), 3)
                        break
                else:
                    # 낙상이 아니면 카운트 리셋
                    self.fall_frame_count = max(0, self.fall_frame_count - 1)

        else:
            # 사람이 감지되지 않으면 카운트 리셋
            self.fall_frame_count = 0

        # 현재 낙상 의심 상태 표시
        if self.config.DEBUG_MODE and self.fall_frame_count > 0:
            threshold = self.config.FALL_DETECTION_PARAMS['fall_duration_frames']
            cv2.putText(frame, f"Fall Suspicion: {self.fall_frame_count}/{threshold}",
                      (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

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
        conf = fall_info['confidence']

        # details 필드가 있으면 사용, 없으면 기본 필드 사용
        if 'details' in analysis:
            details = analysis['details']
            aspect_ratio = details.get('bbox_aspect_ratio', 0.0)
            body_angle = details.get('body_angle', 0.0)
            head_height_ratio = details.get('head_height_ratio', 0.0)
        else:
            aspect_ratio = analysis.get('bbox_aspect_ratio', 0.0)
            body_angle = analysis.get('body_angle', 0.0)
            head_height_ratio = analysis.get('head_height_ratio', 0.0)

        description = f"""
낙상 감지 보고

발생 시각: {timestamp}

감지 정보:
- 사람 감지 신뢰도: {conf:.2f}
- 낙상 점수: {analysis['fall_score']:.2f}

상세 분석:
- 바운딩 박스 가로/세로 비율: {aspect_ratio:.2f}
- 몸통 각도: {body_angle:.1f}도
- 위치 비율: {head_height_ratio:.2f}

감지 근거: {analysis['reason']}

위험도: {'높음' if analysis['fall_score'] > 0.7 else '중간' if analysis['fall_score'] > 0.5 else '낮음'}

모델: {self.config.YOLO_POSE_MODEL}
        """

        return description.strip()

    def get_model_info(self) -> dict:
        """모델 정보 반환"""
        return {
            'model_name': self.config.YOLO_POSE_MODEL,
            'device': str(self.device),
            'half_precision': self.config.USE_HALF_PRECISION,
            'input_size': self.config.IMGSZ,
            'capabilities': ['person_detection', 'pose_estimation', 'fall_detection']
        }
