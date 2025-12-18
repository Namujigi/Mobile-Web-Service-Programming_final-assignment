"""
YOLO 모델 다운로드 스크립트
YOLOv11n-pose 및 YOLOv8n-pose 모델을 자동으로 다운로드합니다.
"""

import os
import sys
import requests
from pathlib import Path
from tqdm import tqdm

# 모델 다운로드 URL
MODELS = {
    'yolov11n-pose.pt': {
        'url': 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov11n-pose.pt',
        'size': '6.0 MB',
        'description': 'YOLOv11n-pose (최신, 권장)'
    },
    'yolov8n-pose.pt': {
        'url': 'https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n-pose.pt',
        'size': '6.4 MB',
        'description': 'YOLOv8n-pose (안정적)'
    },
    'yolov5s.pt': {
        'url': 'https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5s.pt',
        'size': '14.1 MB',
        'description': 'YOLOv5s (사람 감지용, V1에서만 사용)'
    }
}


def download_file(url: str, destination: str) -> bool:
    """
    파일 다운로드 (진행 바 표시)
    """
    try:
        print(f"다운로드 중: {url}")

        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(destination, 'wb') as file, tqdm(
            desc=os.path.basename(destination),
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as progress_bar:
            for data in response.iter_content(chunk_size=1024):
                size = file.write(data)
                progress_bar.update(size)

        print(f"✓ 다운로드 완료: {destination}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ 다운로드 실패: {e}")
        return False
    except Exception as e:
        print(f"✗ 오류 발생: {e}")
        return False


def download_model(model_name: str, force: bool = False) -> bool:
    """
    특정 모델 다운로드
    """
    if model_name not in MODELS:
        print(f"✗ 알 수 없는 모델: {model_name}")
        print(f"사용 가능한 모델: {', '.join(MODELS.keys())}")
        return False

    model_info = MODELS[model_name]
    destination = Path(model_name)

    # 이미 존재하는지 확인
    if destination.exists() and not force:
        print(f"✓ 모델이 이미 존재합니다: {model_name}")
        print(f"  강제 다운로드하려면: python download_models.py {model_name} --force")
        return True

    print(f"\n모델 다운로드: {model_name}")
    print(f"설명: {model_info['description']}")
    print(f"크기: {model_info['size']}")
    print(f"URL: {model_info['url']}\n")

    success = download_file(model_info['url'], str(destination))

    if success:
        file_size = destination.stat().st_size / (1024 * 1024)
        print(f"✓ 저장 위치: {destination.absolute()}")
        print(f"✓ 파일 크기: {file_size:.2f} MB\n")

    return success


def download_all_models(force: bool = False):
    """
    모든 모델 다운로드
    """
    print("="*60)
    print("YOLO 모델 다운로드 시작")
    print("="*60)

    success_count = 0
    total_count = len(MODELS)

    for model_name in MODELS.keys():
        if download_model(model_name, force):
            success_count += 1

    print("="*60)
    print(f"다운로드 완료: {success_count}/{total_count} 모델")
    print("="*60)

    return success_count == total_count


def check_models():
    """
    다운로드된 모델 확인
    """
    print("\n현재 다운로드된 모델:")
    print("-"*60)

    for model_name, info in MODELS.items():
        path = Path(model_name)
        if path.exists():
            size = path.stat().st_size / (1024 * 1024)
            print(f"✓ {model_name:<20} ({size:.2f} MB)")
            print(f"  {info['description']}")
        else:
            print(f"✗ {model_name:<20} (다운로드 필요)")
            print(f"  {info['description']}")
        print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description='YOLO 모델 다운로드')
    parser.add_argument('model', nargs='?', help='다운로드할 모델 (예: yolov11n-pose.pt)')
    parser.add_argument('--all', action='store_true', help='모든 모델 다운로드')
    parser.add_argument('--force', action='store_true', help='기존 파일 덮어쓰기')
    parser.add_argument('--check', action='store_true', help='다운로드된 모델 확인')

    args = parser.parse_args()

    # tqdm이 없으면 설치 안내
    try:
        import tqdm
    except ImportError:
        print("tqdm이 설치되지 않았습니다. 진행 바 없이 다운로드합니다.")
        print("진행 바를 보려면: pip install tqdm")
        print()

    if args.check:
        check_models()
        return

    if args.all:
        download_all_models(args.force)
    elif args.model:
        download_model(args.model, args.force)
    else:
        # 기본: YOLOv11n-pose만 다운로드
        print("="*60)
        print("YOLOv11n-pose 다운로드 (권장 모델)")
        print("="*60)
        print()
        download_model('yolov11n-pose.pt', args.force)
        print()
        print("다른 모델 다운로드:")
        print("  python download_models.py yolov8n-pose.pt")
        print("  python download_models.py --all")
        print()
        print("다운로드된 모델 확인:")
        print("  python download_models.py --check")


if __name__ == "__main__":
    main()
