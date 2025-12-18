"""
Django signals for blog app
Post 생성 시 WebSocket 알림 전송
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Post


@receiver(post_save, sender=Post)
def notify_new_post(sender, instance, created, **kwargs):
    """
    새 게시글이 생성되면 WebSocket으로 알림 전송

    Args:
        sender: Post 모델
        instance: 생성된 Post 인스턴스
        created: True if 새로 생성된 경우
    """
    if created:  # 새로 생성된 경우에만
        channel_layer = get_channel_layer()

        # 이미지 URL 생성
        image_url = ''
        if instance.image:
            image_url = instance.image.url

        # 비디오 URL 생성
        video_url = ''
        if hasattr(instance, 'video') and instance.video:
            video_url = instance.video.url

        # 알림 데이터 준비
        notification_data = {
            'type': 'fall_notification',  # consumer의 fall_notification 메서드 호출
            'post_id': instance.pk,
            'title': instance.title,
            'text': instance.text,
            'timestamp': instance.published_date.isoformat() if instance.published_date else '',
            'image_url': image_url,
            'video_url': video_url
        }

        # 'notifications' 그룹의 모든 클라이언트에게 브로드캐스트
        async_to_sync(channel_layer.group_send)(
            'notifications',
            notification_data
        )

        print(f"✓ Notification sent for new post: {instance.title} (ID: {instance.pk})")
