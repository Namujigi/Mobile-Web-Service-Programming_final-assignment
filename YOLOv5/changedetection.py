import os
import pathlib
import cv2
import requests
from datetime import datetime

class ChangeDetection:
    result_prev = []
    HOST = 'https://namujigi.pythonanywhere.com'
    username = 'admin'
    password = 'password' # 패스워드 삭제한 후 업로드
    token = ""
    title = ""
    text = ""

    REQUIRED_FRAMES = 5 # 몇 프레임동안 탐지되어야 확정인지 Threshold
    PATIENCE_FRAMES = 2
    detection_count = [] # 각 객체별 연속 탐지 카운트
    confirmed_detection = [] # 확정된 것들
    patience_count = []
    
    def __init__(self, names, required_frames_=5, patience_frames_=2):
        self.result_prev = [0 for i in range(len(names))]
        self.REQUIRED_FRAMES = required_frames_
        self.PATIENCE_FRAMES = patience_frames_
        self.detection_count = [0 for i in range(len(names))]
        self.confirmed_detection = [0 for i in range(len(names))]
        self.patience_count = [0 for i in range(len(names))]
        
        res = requests.post(self.HOST + '/api-token-auth/', {
            'username': self.username,
            'password': self.password,
        })
        res.raise_for_status()
        self.token = res.json()['token']  # 토큰 저장
        print(self.token)

    def add(self, names, detected_current, save_dir, image):
        self.title = ""
        self.text = ""
        change_flag = 0  # 변화 감지 플래그

        for i in range(len(detected_current)):
            if detected_current[i] == 1: # 해당 객체 클래스가 탐지되었다면
                self.detection_count[i] += 1
                self.patience_count[i] = 0
            else: # 현재 프레임에서 탐지 안 됨
                if self.detection_count[i] > 0 or self.confirmed_detection[i] == 1: # 연속 탐지 프레임이 0보다 크거나, 5 연속 탐지되어 인식 확정일 때
                    self.patience_count[i] += 1 # 인내 카운트 하나 추가

                    if self.patience_count[i] > self.PATIENCE_FRAMES: # Patience Threshold를 넘어가면 객체가 없어진 것으로 판단.
                        self.detection_count[i] = 0
                        self.patience_count[i] = 0
                        self.confirmed_detection[i] = 0
                    
            if self.detection_count[i] >= self.REQUIRED_FRAMES:
                if self.confirmed_detection[i] == 0: # 새롭게 5 연속 탐지된 경우.
                    change_flag = 1
                    self.confirmed_detection[i] = 1
                    self.title = names[i]
                    self.text += names[i] + ", "
        
        self.result_prev = detected_current[:]  # 검제 검출 상태 저장
        
        if change_flag == 1:
            self.send(save_dir, image)

    def send(self, save_dir, image):
        now = datetime.now()
        now.isoformat()
        
        today = datetime.now()
        save_path = os.getcwd() / save_dir / 'detected' / str(today.year) / str(today.month) / str(today.day)
        pathlib.Path(save_path).mkdir(parents=True, exist_ok=True)
        
        full_path = save_path / '{0}-{1}-{2}-{3}.jpg'.format(today.hour, today.minute, today.second, today.microsecond)
        
        dst = cv2.resize(image, dsize=(320, 240), interpolation=cv2.INTER_AREA)
        cv2.imwrite(full_path, dst)
        
        # 인증이 필요한 요청에 아래의 headers를 붙임
        headers = {'Authorization': 'JWT ' + self.token, 'Accept': 'application/json'}
        
        # Post Create
        data = {
            'author': 1,
            'title': self.title,
            'text': self.text,
            'created_date': now,
            'published_date': now
        }
        file = {'image': open(full_path, 'rb')}
        res = requests.post(self.HOST + '/api_root/Post/', data=data, files=file, headers=headers)
        print(res)