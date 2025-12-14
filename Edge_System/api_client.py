"""
Django REST API 통신 모듈
"""

import requests
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DjangoAPIClient:
    """Django REST API 클라이언트"""

    def __init__(self, config):
        self.config = config
        self.api_endpoint = config.API_ENDPOINT
        self.author_id = config.AUTHOR_ID

    def create_fall_post(self, title: str, description: str,
                        image_path: Optional[str] = None) -> bool:
        """
        낙상 감지 게시글 생성

        Args:
            title: 게시글 제목
            description: 게시글 내용
            image_path: 이미지 파일 경로 (선택)

        Returns:
            성공 여부
        """
        try:
            # 게시글 데이터 준비
            data = {
                'author': self.author_id,
                'title': title,
                'text': description,
                'published_date': datetime.now().isoformat()
            }

            files = {}
            if image_path and Path(image_path).exists():
                files['image'] = open(image_path, 'rb')

            # POST 요청
            logger.info(f"Sending POST request to {self.api_endpoint}")
            response = requests.post(
                self.api_endpoint,
                data=data,
                files=files,
                timeout=10
            )

            # 파일 닫기
            if files:
                files['image'].close()

            # 응답 확인
            if response.status_code in [200, 201]:
                logger.info(f"Post created successfully: {response.json()}")
                return True
            else:
                logger.error(f"Failed to create post. Status: {response.status_code}, "
                           f"Response: {response.text}")
                return False

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error: Cannot connect to {self.api_endpoint}")
            return False

        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return False

        except Exception as e:
            logger.error(f"Error creating post: {e}")
            return False

    def create_fall_alert(self, fall_info: dict, image_path: Optional[str] = None) -> bool:
        """
        낙상 알림 게시글 생성

        Args:
            fall_info: 낙상 정보 딕셔너리
            image_path: 낙상 이미지 경로

        Returns:
            성공 여부
        """
        timestamp = fall_info['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        analysis = fall_info['analysis']

        # 제목 생성
        title = f"[긴급] 낙상 감지 알림 - {timestamp}"

        # 내용 생성
        description = f"""
낙상이 감지되었습니다!

발생 시각: {timestamp}

감지 상세 정보:
- 낙상 점수: {analysis['fall_score']:.2f}
- 바운딩 박스 가로/세로 비율: {analysis['bbox_aspect_ratio']:.2f}
- 몸통 각도: {analysis['body_angle']:.1f}도
- 감지 근거: {analysis['reason']}

위험도: {'높음' if analysis['fall_score'] > 0.7 else '중간'}

즉시 확인이 필요합니다!
        """

        return self.create_fall_post(title, description.strip(), image_path)

    def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            response = requests.get(self.config.DJANGO_SERVER_URL, timeout=5)
            logger.info(f"Connection test successful. Status: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
