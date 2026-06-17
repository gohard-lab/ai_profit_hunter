import requests
import time
from datetime import datetime

# 깨우고 싶은 Streamlit 앱 주소들을 리스트에 넣으세요
STREAMLIT_APPS = [
    "https://carcostsimulator-e9prevei4pq9cap535vfp8.streamlit.app/",
    "https://drivingdashboard-t8exrwypqvsce3gdq3cksd.streamlit.app/",
    "https://f1-race-analyzer-9pbapphbkgmo6rguympwshf.streamlit.app/",
    "https://kcarcrawler-5ryuwuw8izgjmqphppweyv.streamlit.app/",
    "https://schoolzonefinesim.streamlit.app/",
    "https://cheiridrivingdashboard-cgpdknof3nnvufwaeyzkhr.streamlit.app/",
    "https://quattrosimulator-kbsulzwvq8ucrcpph6rfg5.streamlit.app/",
    "https://aitextdetector-lhbmnzgpagsda9nebjhpuj.streamlit.app/",
    "https://pwnedcredentialchecker-hmugyj9xsfalvzvrn4bfxi.streamlit.app/",
    # 여기에 운영 중인 다른 URL들을 추가하세요
]

def wake_up_apps():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] Streamlit 앱 수면 방지 Ping 작업 시작...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0"
    }

    for url in STREAMLIT_APPS:
        try:
            # 💡 핵심: 찌를 때마다 꼬리표(현재 시간)를 다르게 달아서 무조건 새로고침 시키기
            bypass_cache_url = f"{url}?ping={int(time.time())}"
            
            response = requests.get(bypass_cache_url, headers=headers, timeout=60)
            
            if response.status_code == 200:
                if "This app has gone to sleep" in response.text or "Zzzz" in response.text:
                    print(f" 💤 이미 잠듦 (직접 브라우저에서 버튼 클릭 필요): {url}")
                else:
                    print(f" ✅ 정상 작동 중 (수면 타이머 연장됨): {url}")
            else:
                print(f" ⚠️ 접속 오류({response.status_code}): {url}")
                
        except requests.exceptions.ReadTimeout:
            print(f" ⏳ 타임아웃 (서버가 응답을 지연 중이며, 깨어나는 중일 수 있음): {url}")
        except Exception as e:
            print(f" ❌ 기타 에러 발생 ({url}): {e}")

if __name__ == "__main__":
    wake_up_apps()