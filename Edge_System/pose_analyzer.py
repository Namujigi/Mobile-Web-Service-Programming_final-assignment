"""
포즈 분석 및 낙상 감지 모듈 V2
YOLOv8/YOLOv11-pose의 17개 키포인트를 분석하여 낙상 여부 판단
가중치 기반 점수 계산 시스템 사용
"""

import numpy as np
import cv2
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class PoseAnalyzer:
    """
    YOLO-pose 키포인트 인덱스 (COCO format):
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
    SHOULDER_KEYPOINTS = [5, 6]  # 어깨
    HIP_KEYPOINTS = [11, 12]  # 엉덩이
    KNEE_KEYPOINTS = [13, 14]  # 무릎
    ANKLE_KEYPOINTS = [15, 16]  # 발목

    # 키포인트 신뢰도 임계값
    KEYPOINT_CONF_THRESHOLD = 0.3

    def __init__(self, config: Dict):
        """
        Args:
            config: FALL_DETECTION_PARAMS 딕셔너리
        """
        self.config = config

        # 임계값 설정
        self.aspect_ratio_threshold = config.get('aspect_ratio_threshold', 1.5)
        self.bbox_height_ratio_threshold = config.get('bbox_height_ratio_threshold', 0.4)
        self.keypoint_height_threshold = config.get('keypoint_height_threshold', 0.6)
        self.horizontal_threshold = config.get('horizontal_threshold', 0.3)
        self.body_angle_threshold = config.get('body_angle_threshold', 60)

        # 가중치 설정 (V2의 핵심 개선)
        self.weights = config.get('weights', {
            'aspect_ratio': 0.35,
            'low_position': 0.20,
            'horizontal_body': 0.25,
            'body_angle': 0.20
        })

        # 낙상 점수 임계값
        self.fall_score_threshold = config.get('fall_score_threshold', 0.6)

        logger.debug(f"PoseAnalyzer initialized with threshold: {self.fall_score_threshold}")

    def analyze_pose(self, keypoints: np.ndarray, bbox: Tuple[int, int, int, int],
                     frame_height: int) -> Dict:
        """
        포즈 분석하여 낙상 여부 판단 (가중치 기반)

        Args:
            keypoints: (17, 3) 배열 [x, y, confidence]
            bbox: (x1, y1, x2, y2) 바운딩 박스
            frame_height: 프레임 높이

        Returns:
            분석 결과 딕셔너리 {
                'is_fall': bool,
                'fall_score': float,
                'reason': str,
                'details': dict
            }
        """
        x1, y1, x2, y2 = bbox
        bbox_width = x2 - x1
        bbox_height = y2 - y1

        # 결과 초기화
        result = {
            'is_fall': False,
            'fall_score': 0.0,
            'reason': '',
            'details': {
                'bbox_aspect_ratio': 0.0,
                'body_angle': 0.0,
                'head_height_ratio': 0.0,
                'horizontal_ratio': 0.0,
                'aspect_score': 0.0,
                'position_score': 0.0,
                'horizontal_score': 0.0,
                'angle_score': 0.0
            }
        }

        # 개별 점수 초기화
        aspect_score = 0.0
        position_score = 0.0
        horizontal_score = 0.0
        angle_score = 0.0

        # ========== 1. 바운딩 박스 가로/세로 비율 분석 ==========
        if bbox_height > 0:
            aspect_ratio = bbox_width / bbox_height
            result['details']['bbox_aspect_ratio'] = aspect_ratio

            # 가로가 세로보다 긴 경우 (누운 자세)
            if aspect_ratio > self.aspect_ratio_threshold:
                # 비율이 클수록 점수 증가
                aspect_score = min(1.0, (aspect_ratio - self.aspect_ratio_threshold) / 1.0)
                result['reason'] += f'Wide bbox({aspect_ratio:.2f}); '

        result['details']['aspect_score'] = aspect_score

        # ========== 2. 바운딩 박스 위치 분석 (낮은 위치) ==========
        bbox_center_y = (y1 + y2) / 2
        height_ratio = bbox_center_y / frame_height
        result['details']['head_height_ratio'] = height_ratio

        # 화면 하단에 가까울수록 낙상 가능성 증가
        if height_ratio > (1 - self.bbox_height_ratio_threshold):
            # 하단에 가까울수록 점수 증가
            position_score = (height_ratio - (1 - self.bbox_height_ratio_threshold)) / self.bbox_height_ratio_threshold
            position_score = min(1.0, position_score)
            result['reason'] += f'Low position({height_ratio:.2f}); '

        result['details']['position_score'] = position_score

        # ========== 3. 키포인트 기반 분석 ==========
        if keypoints is not None and len(keypoints) > 0:
            # 3-1. 머리와 엉덩이의 수평 거리 분석
            head_y = self._get_average_keypoint_y(keypoints, self.HEAD_KEYPOINTS)
            hip_y = self._get_average_keypoint_y(keypoints, self.HIP_KEYPOINTS)

            if head_y is not None and hip_y is not None and bbox_height > 0:
                # 수직 거리를 바운딩 박스 높이로 정규화
                vertical_distance = abs(hip_y - head_y)
                horizontal_ratio = vertical_distance / bbox_height
                result['details']['horizontal_ratio'] = horizontal_ratio

                # 머리와 엉덩이가 비슷한 높이 (수평 자세)
                if horizontal_ratio < self.horizontal_threshold:
                    horizontal_score = 1.0 - (horizontal_ratio / self.horizontal_threshold)
                    result['reason'] += f'Horizontal body({horizontal_ratio:.2f}); '

            # 3-2. 몸통 각도 분석
            shoulder_y = self._get_average_keypoint_y(keypoints, self.SHOULDER_KEYPOINTS)
            shoulder_x = self._get_average_keypoint_x(keypoints, self.SHOULDER_KEYPOINTS)
            hip_x = self._get_average_keypoint_x(keypoints, self.HIP_KEYPOINTS)

            if shoulder_y is not None and hip_y is not None and shoulder_x is not None and hip_x is not None:
                dx = abs(shoulder_x - hip_x)
                dy = abs(shoulder_y - hip_y)

                # 각도 계산 (수직에서 벗어난 정도)
                if dy > 0:
                    angle = np.degrees(np.arctan(dx / dy))
                    result['details']['body_angle'] = angle

                    # 각도가 임계값보다 크면 (수평에 가까움)
                    if angle > self.body_angle_threshold:
                        # 각도가 클수록 점수 증가
                        angle_score = min(1.0, (angle - self.body_angle_threshold) / 30.0)
                        result['reason'] += f'Horizontal angle({angle:.1f}°); '

        result['details']['horizontal_score'] = horizontal_score
        result['details']['angle_score'] = angle_score

        # ========== 4. 가중치 적용 최종 점수 계산 ==========
        weighted_score = (
            aspect_score * self.weights.get('aspect_ratio', 0.35) +
            position_score * self.weights.get('low_position', 0.20) +
            horizontal_score * self.weights.get('horizontal_body', 0.25) +
            angle_score * self.weights.get('body_angle', 0.20)
        )

        result['fall_score'] = weighted_score

        # ========== 5. 낙상 판단 ==========
        if weighted_score >= self.fall_score_threshold:
            result['is_fall'] = True
            logger.debug(f"Fall detected! Score: {weighted_score:.3f} (threshold: {self.fall_score_threshold})")
        else:
            logger.debug(f"Normal pose. Score: {weighted_score:.3f}")

        return result

    def _get_average_keypoint_y(self, keypoints: np.ndarray, indices: list) -> Optional[float]:
        """
        특정 키포인트들의 평균 Y 좌표 계산

        Args:
            keypoints: (17, 3) 키포인트 배열
            indices: 평균을 구할 키포인트 인덱스 리스트

        Returns:
            평균 Y 좌표 또는 None (유효한 키포인트가 없을 때)
        """
        valid_points = []
        for idx in indices:
            if idx < len(keypoints) and keypoints[idx][2] > self.KEYPOINT_CONF_THRESHOLD:
                valid_points.append(keypoints[idx][1])

        return np.mean(valid_points) if valid_points else None

    def _get_average_keypoint_x(self, keypoints: np.ndarray, indices: list) -> Optional[float]:
        """
        특정 키포인트들의 평균 X 좌표 계산

        Args:
            keypoints: (17, 3) 키포인트 배열
            indices: 평균을 구할 키포인트 인덱스 리스트

        Returns:
            평균 X 좌표 또는 None (유효한 키포인트가 없을 때)
        """
        valid_points = []
        for idx in indices:
            if idx < len(keypoints) and keypoints[idx][2] > self.KEYPOINT_CONF_THRESHOLD:
                valid_points.append(keypoints[idx][0])

        return np.mean(valid_points) if valid_points else None

    @staticmethod
    def draw_skeleton(frame: np.ndarray, keypoints: np.ndarray,
                      confidence_threshold: float = 0.3,
                      color_normal: Tuple[int, int, int] = (0, 255, 0),
                      color_line: Tuple[int, int, int] = (0, 255, 255)) -> np.ndarray:
        """
        프레임에 스켈레톤 그리기

        Args:
            frame: 입력 프레임
            keypoints: (17, 3) 키포인트 배열 [x, y, confidence]
            confidence_threshold: 키포인트 표시 신뢰도 임계값
            color_normal: 키포인트 색상 (BGR)
            color_line: 스켈레톤 라인 색상 (BGR)

        Returns:
            스켈레톤이 그려진 프레임
        """
        # COCO 스켈레톤 연결 정의
        skeleton_connections = [
            # 얼굴
            (0, 1), (0, 2),  # nose - eyes
            (1, 3), (2, 4),  # eyes - ears

            # 상체
            (5, 6),  # shoulders
            (5, 7), (7, 9),  # left arm
            (6, 8), (8, 10),  # right arm

            # 몸통
            (5, 11), (6, 12),  # shoulders - hips
            (11, 12),  # hips

            # 하체
            (11, 13), (13, 15),  # left leg
            (12, 14), (14, 16)   # right leg
        ]

        # 키포인트 그리기
        for i, (x, y, conf) in enumerate(keypoints):
            if conf > confidence_threshold:
                # 주요 키포인트는 크게 표시
                radius = 5 if i in [0, 5, 6, 11, 12] else 3
                cv2.circle(frame, (int(x), int(y)), radius, color_normal, -1)

                # 키포인트 번호 표시 (디버그용, 필요시 활성화)
                # cv2.putText(frame, str(i), (int(x)+5, int(y)),
                #            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        # 스켈레톤 라인 그리기
        for start_idx, end_idx in skeleton_connections:
            if (start_idx < len(keypoints) and end_idx < len(keypoints) and
                keypoints[start_idx][2] > confidence_threshold and
                keypoints[end_idx][2] > confidence_threshold):

                start_point = (int(keypoints[start_idx][0]), int(keypoints[start_idx][1]))
                end_point = (int(keypoints[end_idx][0]), int(keypoints[end_idx][1]))

                # 몸통 연결은 굵게
                thickness = 3 if (start_idx, end_idx) in [(5, 11), (6, 12), (11, 12)] else 2
                cv2.line(frame, start_point, end_point, color_line, thickness)

        return frame

    def get_analysis_summary(self, result: Dict) -> str:
        """
        분석 결과를 사람이 읽기 쉬운 형식으로 변환

        Args:
            result: analyze_pose()의 반환 결과

        Returns:
            분석 요약 문자열
        """
        details = result['details']
        summary = f"""
낙상 분석 결과:
- 최종 점수: {result['fall_score']:.3f} / {self.fall_score_threshold}
- 판정: {'낙상 감지' if result['is_fall'] else '정상'}

세부 점수:
- 가로/세로 비율: {details['aspect_score']:.3f} x {self.weights['aspect_ratio']} = {details['aspect_score'] * self.weights['aspect_ratio']:.3f}
- 낮은 위치: {details['position_score']:.3f} x {self.weights['low_position']} = {details['position_score'] * self.weights['low_position']:.3f}
- 수평 자세: {details['horizontal_score']:.3f} x {self.weights['horizontal_body']} = {details['horizontal_score'] * self.weights['horizontal_body']:.3f}
- 몸통 각도: {details['angle_score']:.3f} x {self.weights['body_angle']} = {details['angle_score'] * self.weights['body_angle']:.3f}

측정값:
- 바운딩 박스 비율: {details['bbox_aspect_ratio']:.2f}
- 몸통 각도: {details['body_angle']:.1f}°
- 높이 비율: {details['head_height_ratio']:.2f}
- 수평 비율: {details['horizontal_ratio']:.2f}

감지 근거: {result['reason']}
        """
        return summary.strip()
