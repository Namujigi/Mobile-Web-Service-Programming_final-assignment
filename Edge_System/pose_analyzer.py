"""
포즈 분석 및 낙상 감지 모듈
YOLOv8-pose의 17개 키포인트를 분석하여 낙상 여부 판단
"""

import numpy as np
import cv2
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PoseAnalyzer:
    """
    YOLOv8-pose 키포인트 인덱스:
    0: Nose, 1: Left-eye, 2: Right-eye, 3: Left-ear, 4: Right-ear,
    5: Left-shoulder, 6: Right-shoulder, 7: Left-elbow, 8: Right-elbow,
    9: Left-wrist, 10: Right-wrist, 11: Left-hip, 12: Right-hip,
    13: Left-knee, 14: Right-knee, 15: Left-ankle, 16: Right-ankle
    """

    KEYPOINT_NAMES = [
        'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
        'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
        'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
        'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
    ]

    # 주요 키포인트 그룹
    HEAD_KEYPOINTS = [0, 1, 2, 3, 4]  # 머리 부분
    TORSO_KEYPOINTS = [5, 6, 11, 12]  # 몸통 부분

    def __init__(self, config):
        self.config = config
        self.aspect_ratio_threshold = config['aspect_ratio_threshold']
        self.height_ratio_threshold = config['height_ratio_threshold']
        self.keypoint_height_threshold = config['keypoint_height_threshold']

    def analyze_pose(self, keypoints: np.ndarray, bbox: Tuple[int, int, int, int],
                     frame_height: int) -> dict:
        """
        포즈 분석하여 낙상 여부 판단

        Args:
            keypoints: (17, 3) 배열 [x, y, confidence]
            bbox: (x1, y1, x2, y2) 바운딩 박스
            frame_height: 프레임 높이

        Returns:
            분석 결과 딕셔너리
        """
        x1, y1, x2, y2 = bbox
        bbox_width = x2 - x1
        bbox_height = y2 - y1

        result = {
            'is_fall': False,
            'fall_score': 0.0,
            'reason': '',
            'bbox_aspect_ratio': 0.0,
            'body_angle': 0.0,
            'head_height_ratio': 0.0
        }

        # 1. 바운딩 박스 가로/세로 비율 분석
        if bbox_height > 0:
            aspect_ratio = bbox_width / bbox_height
            result['bbox_aspect_ratio'] = aspect_ratio

            # 가로가 세로보다 훨씬 긴 경우 (누운 자세)
            if aspect_ratio > self.aspect_ratio_threshold:
                result['fall_score'] += 0.4
                result['reason'] += 'Wide bbox; '

        # 2. 바운딩 박스 높이가 프레임 대비 낮은 위치
        bbox_center_y = (y1 + y2) / 2
        height_ratio = bbox_center_y / frame_height
        result['head_height_ratio'] = height_ratio

        if height_ratio > (1 - self.height_ratio_threshold):
            result['fall_score'] += 0.2
            result['reason'] += 'Low position; '

        # 3. 키포인트 기반 분석
        if keypoints is not None and len(keypoints) > 0:
            # 머리와 엉덩이의 상대적 위치 분석
            head_y = self._get_average_keypoint_y(keypoints, self.HEAD_KEYPOINTS)
            hip_y = self._get_average_keypoint_y(keypoints, [11, 12])

            if head_y is not None and hip_y is not None:
                # 머리와 엉덩이가 비슷한 높이에 있는 경우 (누운 자세)
                vertical_distance = abs(hip_y - head_y)

                if vertical_distance < bbox_height * 0.3:
                    result['fall_score'] += 0.3
                    result['reason'] += 'Horizontal body; '

                # 몸통 각도 계산
                shoulder_y = self._get_average_keypoint_y(keypoints, [5, 6])
                if shoulder_y is not None:
                    shoulder_x = self._get_average_keypoint_x(keypoints, [5, 6])
                    hip_x = self._get_average_keypoint_x(keypoints, [11, 12])

                    if shoulder_x is not None and hip_x is not None:
                        # 몸통이 수평에 가까운 각도
                        dx = abs(shoulder_x - hip_x)
                        dy = abs(shoulder_y - hip_y)

                        if dy > 0:
                            angle = np.degrees(np.arctan(dx / dy))
                            result['body_angle'] = angle

                            # 각도가 크면 (수평에 가까움) 낙상 가능성 증가
                            if angle > 60:
                                result['fall_score'] += 0.1
                                result['reason'] += 'Horizontal angle; '

        # 낙상 판단
        if result['fall_score'] >= 0.5:
            result['is_fall'] = True

        return result

    def _get_average_keypoint_y(self, keypoints: np.ndarray, indices: list) -> Optional[float]:
        """특정 키포인트들의 평균 Y 좌표"""
        valid_points = []
        for idx in indices:
            if idx < len(keypoints) and keypoints[idx][2] > 0.3:  # confidence > 0.3
                valid_points.append(keypoints[idx][1])

        return np.mean(valid_points) if valid_points else None

    def _get_average_keypoint_x(self, keypoints: np.ndarray, indices: list) -> Optional[float]:
        """특정 키포인트들의 평균 X 좌표"""
        valid_points = []
        for idx in indices:
            if idx < len(keypoints) and keypoints[idx][2] > 0.3:  # confidence > 0.3
                valid_points.append(keypoints[idx][0])

        return np.mean(valid_points) if valid_points else None

    @staticmethod
    def draw_skeleton(frame: np.ndarray, keypoints: np.ndarray,
                      confidence_threshold: float = 0.3) -> np.ndarray:
        """
        프레임에 스켈레톤 그리기
        """
        # 스켈레톤 연결 정의
        skeleton = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # 머리
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # 팔
            (5, 11), (6, 12), (11, 12),  # 몸통
            (11, 13), (13, 15), (12, 14), (14, 16)  # 다리
        ]

        # 키포인트 그리기
        for i, (x, y, conf) in enumerate(keypoints):
            if conf > confidence_threshold:
                cv2.circle(frame, (int(x), int(y)), 3, (0, 255, 0), -1)

        # 스켈레톤 라인 그리기
        for start_idx, end_idx in skeleton:
            if (start_idx < len(keypoints) and end_idx < len(keypoints) and
                keypoints[start_idx][2] > confidence_threshold and
                keypoints[end_idx][2] > confidence_threshold):

                start_point = (int(keypoints[start_idx][0]), int(keypoints[start_idx][1]))
                end_point = (int(keypoints[end_idx][0]), int(keypoints[end_idx][1]))
                cv2.line(frame, start_point, end_point, (0, 255, 255), 2)

        return frame
