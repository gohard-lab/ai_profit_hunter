import requests
from datetime import datetime

# 깨우고 싶은 Streamlit 앱 주소들을 리스트에 넣으세요
STREAMLIT_APPS = [
    "https://carcostsimulator-e9prevei4pq9cap535vfp8.streamlit.app/",
    "https://drivingdashboard-t8exrwypqvsce3gdq3cksd.streamlit.app/",
    "https://f1-race-analyzer-9pbapphbkgmo6rguympwshf.streamlit.app/",
    "https://kcarcrawler-5ryuwuw8izgjmqphppweyv.streamlit.app/",
    "https://schoolzonefinesim.streamlit.app/",
    "https://cheiridrivingdashboard-cgpdknof3nnvufwaeyzkhr.streamlit.app/,"
    # 여기에 운영 중인 다른 URL들을 추가하세요
]

def wake_up_apps():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] Streamlit 앱 깨우기 작업 시작...")

    # 일반 브라우저(크롬)에서 접속하는 것처럼 속이는 헤더 정보
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    success_count = 0
    fail_count = 0

    for url in STREAMLIT_APPS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # 응답받은 HTML 텍스트 안에 수면 상태를 의미하는 키워드가 있는지 검사
                if "This app has gone to sleep" in response.text or "Zzzz" in response.text:
                    print(f" 💤 잠들어 있음 (브라우저에서 직접 깨워주세요!): {url}")
                    fail_count += 1
                else:
                    print(f" ✅ 정상 작동 중: {url}")
                    success_count += 1
            else:
                print(f" ⚠️ 접속 오류({response.status_code}): {url}")
                fail_count += 1
        except Exception as e:
            print(f" ❌ 에러 발생 ({url}): {e}")

if __name__ == "__main__":
    wake_up_apps()