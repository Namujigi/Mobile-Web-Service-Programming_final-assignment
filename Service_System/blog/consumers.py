"""
WebSocket Consumer for real-time notifications
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    낙상 감지 알림을 위한 WebSocket Consumer
    클라이언트가 연결하면 'notifications' 그룹에 추가
"""

    async def connect(self):
        """WebSocket 연결 시 호출"""
        # 모든 클라이언트를 'notifications' 그룹에 추가
        self.group_name = 'notifications'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
    )

        await self.accept()
        print(f"✓ WebSocket connected: {self.channel_name}")

        # 연결 확인 메시지 전송
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'WebSocket 연결 성공'
        }))

    async def disconnect(self, close_code):
        """WebSocket 연결 해제 시 호출"""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        print(f"✗ WebSocket disconnected: {self.channel_name}")

    async def receive(self, text_data):
        """클라이언트로부터 메시지 수신"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'unknown')

            # 핑/퐁 메시지 처리 (연결 유지용)
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong'
                }))
        except json.JSONDecodeError:
            pass

    async def fall_notification(self, event):
        """
        낙상 알림 브로드캐스트 수신
        group_send()로부터 호출됨
        """
        # 클라이언트에게 알림 전송
        await self.send(text_data=json.dumps({
            'type': 'fall_detected',
            'post_id': event['post_id'],
            'title': event['title'],
            'text': event['text'],
            'timestamp': event['timestamp'],
            'image_url': event.get('image_url', ''),
            'video_url': event.get('video_url', '')
        }))
