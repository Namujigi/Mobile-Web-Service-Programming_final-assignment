# Django REST API 토큰 설정 가이드

## 왜 필요한가?

Django 블로그가 Admin만 접근 가능하도록 보호되었기 때문에, Edge System이 낙상 감지 시 자동으로 게시글을 작성하려면 **Admin 인증 토큰**이 필요합니다.

## 🔧 설정 단계

### 1. Django에서 Token Authentication 활성화

#### Service_System/mysite/settings.py 수정

```python
INSTALLED_APPS = [
    # ... 기존 앱들
    'rest_framework',
    'rest_framework.authtoken',  # 이 줄 추가
    'blog',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',  # 이 줄 추가
        'rest_framework.authentication.SessionAuthentication',
    ],
}
```

#### 데이터베이스 마이그레이션

```bash
cd Service_System
python manage.py migrate
```

### 2. Admin 토큰 생성

Django shell에서 토큰 생성:

```bash
cd Service_System
python manage.py shell
```

Python shell에서 실행:

```python
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

# admin 사용자 가져오기 (없으면 생성)
try:
    admin = User.objects.get(username='admin')
except User.DoesNotExist:
    admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin비밀번호')

# 토큰 생성 또는 가져오기
token, created = Token.objects.get_or_create(user=admin)

# 토큰 출력
print(f"✓ Admin Token: {token.key}")

if created:
    print("  새 토큰이 생성되었습니다.")
else:
    print("  기존 토큰을 사용합니다.")
```

출력 예시:
```
✓ Admin Token: 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
  새 토큰이 생성되었습니다.
```

### 3. Edge System 환경 변수 설정

#### .env 파일 생성

```bash
cd Edge_System
cp .env.example .env
```

#### .env 파일 편집

```ini
# Django 서버 URL
DJANGO_SERVER_URL=http://localhost:8000

# Django Admin 사용자 ID
AUTHOR_ID=1

# Django REST API Token (위에서 생성한 토큰)
API_TOKEN=9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

⚠️ **중요**: `.env` 파일은 `.gitignore`에 포함되어 있어 GitHub에 올라가지 않습니다!

### 4. python-dotenv 설치

```bash
cd Edge_System
pip install python-dotenv
```

또는:

```bash
pip install -r requirements.txt
```

### 5. 테스트

#### Django 서버 실행
```bash
cd Service_System
python manage.py runserver
```

#### Edge System 실행
```bash
cd Edge_System
python main.py
```

정상 작동하면 다음과 같이 표시됩니다:
```
✓ Loaded environment variables from C:\...\Edge_System\.env
Using device: cuda
Loading yolov11n-pose.pt
...
```

## 🔐 보안 주의사항

### ✅ 해야 할 것:
- `.env` 파일에 토큰 저장
- `.env`를 `.gitignore`에 추가 (이미 완료)
- `.env.example` 파일만 GitHub에 업로드

### ❌ 하지 말아야 할 것:
- 토큰을 코드에 하드코딩
- `.env` 파일을 GitHub에 업로드
- 토큰을 다른 사람과 공유

## 🧪 API 테스트

### curl로 테스트

**인증 없이 (실패):**
```bash
curl http://localhost:8000/api_root/Post/
```
응답: `403 Forbidden`

**토큰 인증 (성공):**
```bash
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
     http://localhost:8000/api_root/Post/
```
응답: 게시글 목록 JSON

**POST 요청 (게시글 작성):**
```bash
curl -X POST http://localhost:8000/api_root/Post/ \
     -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
     -F "author=1" \
     -F "title=테스트 게시글" \
     -F "text=낙상 테스트" \
     -F "published_date=2025-12-18T10:00:00"
```

## ❓ 문제 해결

### "API_TOKEN not set" 경고

**원인**: `.env` 파일이 없거나 `API_TOKEN`이 비어있음

**해결**:
```bash
cd Edge_System
cp .env.example .env
# .env 파일 편집하여 토큰 입력
```

### "403 Forbidden" 오류

**원인**: 토큰이 잘못되었거나 만료됨

**해결**:
```python
# Django shell에서 토큰 재생성
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
admin = User.objects.get(username='admin')
Token.objects.filter(user=admin).delete()
token = Token.objects.create(user=admin)
print(f"New Token: {token.key}")
```

### "Connection refused" 오류

**원인**: Django 서버가 실행되지 않음

**해결**:
```bash
cd Service_System
python manage.py runserver
```

## 📚 참고 자료

- [Django REST Framework - Token Authentication](https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication)
- [python-dotenv 문서](https://pypi.org/project/python-dotenv/)

## 🚀 배포 시 주의사항

### PythonAnywhere 배포

1. PythonAnywhere에서 `.env` 파일 생성
2. Web 탭에서 환경 변수 설정
3. 또는 Files 탭에서 `.env` 파일 업로드

### Docker 배포

```dockerfile
# .env 파일을 복사하지 않고 환경 변수로 전달
ENV API_TOKEN=your_token_here
```

또는:

```bash
docker run -e API_TOKEN=your_token_here edge_system
```
