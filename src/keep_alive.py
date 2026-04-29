import requests
from datetime import datetime

# 깨우고 싶은 Streamlit 앱 주소들을 리스트에 넣으세요
STREAMLIT_APPS = [
    "https://carcostsimulator-e9prevei4pq9cap535vfp8.streamlit.app/",
    "https://drivingdashboard-t8exrwypqvsce3gdq3cksd.streamlit.app/",
    "https://f1-race-analyzer-9pbapphbkgmo6rguympwshf.streamlit.app/",
    "https://kcarcrawler-5ryuwuw8izgjmqphppweyv.streamlit.app/",
    "https://schoolzonefinesim.streamlit.app/",
    # 여기에 운영 중인 다른 URL들을 추가하세요
]

def wake_up_apps():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] Streamlit 앱 깨우기 작업 시작...")

    # 일반 브라우저(크롬)에서 접속하는 것처럼 속이는 헤더 정보
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for url in STREAMLIT_APPS:
        try:
            # 헤더 정보를 함께 전송하여 봇이 아닌 척합니다.
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                print(f" ✅ 성공: {url}")
            else:
                print(f" ⚠️ 확인 필요({response.status_code}): {url}")
        except Exception as e:
            print(f" ❌ 에러 발생 ({url}): {e}")

if __name__ == "__main__":
    wake_up_apps()