import time
from datetime import datetime
from playwright.sync_api import sync_playwright

# 깨우고 싶은 Streamlit 앱 주소 리스트
STREAMLIT_APPS = [
    "https://quattrosimulator-kbsulzwvq8ucrcpph6rfg5.streamlit.app/",
    "https://aitextdetector-lhbmnzgpagsda9nebjhpuj.streamlit.app/",
    "https://faceswapdefender-upsnzcakgyfsgtdhuw4c5n.streamlit.app/", 
    "https://pwnedcredentialchecker-hmugyj9xsfalvzvrn4bfxi.streamlit.app/",
    "https://carcostsimulator-e9prevei4pq9cap535vfp8.streamlit.app/",
    "https://drivingdashboard-t8exrwypqvsce3gdq3cksd.streamlit.app/",
    "https://f1-race-analyzer-9pbapphbkgmo6rguympwshf.streamlit.app/",
    "https://kcarcrawler-5ryuwuw8izgjmqphppweyv.streamlit.app/",
    "https://schoolzonefinesim-jamadbprromvbbwwzhgeui.streamlit.app/",
    "https://cheiridrivingdashboard-cgpdknof3nnvufwaeyzkhr.streamlit.app/",
    "https://tapewaveformanalyzer-94v6hmwzuzzsvbse3qmdxe.streamlit.app/",
    "https://voicefrequencyanalyzer-67zfryfptjxwdjofkymjyw.streamlit.app/",
    "https://moviebepcalculator-77dp957j9snypavp86bgsb.streamlit.app/",
]

def wake_up_apps():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{now}] Streamlit 앱 수면 방지 Playwright 브라우저 작업 시작...")

    # 브라우저 자동화 컨텍스트 가동
    with sync_playwright() as p:
        # 헤드리스 크롬 가상 브라우저 구동
        browser = p.chromium.launch(headless=True)
        
        for url in STREAMLIT_APPS:
            # 안전 순회 루프: 하나의 앱이 터져도 다음 앱 작업 지속
            try:
                # 고유 유저 에이전트 서명을 탑재한 브라우저 세션 개설
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Polymath-Engine-Ping/1.0"
                )
                page = context.new_page()
                
                # 캐시 우회용 실시간 고유 쿼리 스트링 주입
                bypass_cache_url = f"{url}?ping={int(time.time())}"
                
                print(f" 🚀 가상 브라우저 접속 시도: {url}")
                
                # 실제 브라우저 렌더링 및 페이지 이동 (제한시간 60초)
                response = page.goto(bypass_cache_url, timeout=60000)
                
                # 핵심: 스팀릿 실시간 웹소켓 세션이 완전히 체결되도록 5초 강제 대기
                page.wait_for_timeout(5000)
                
                if response and response.status == 200:
                    content = page.content()
                    # 렌더링된 돔 트리 본문 내부의 수면 안내 텍스트 검증
                    if "This app has gone to sleep" in content or "Zzzz" in content:
                        print(f" 💤 가짜 성공 방지: 페이지는 열렸으나 앱이 잠겨 있음 (수동 클릭 필요): {url}")
                    else:
                        print(f" ✅ 실제 웹소켓 트래픽 활성화 및 수면 타이머 연장 완료: {url}")
                else:
                    status_code = response.status if response else "No Response"
                    print(f" ⚠️ 접속 제한 또는 페이지 오류({status_code}): {url}")
                
                # 다음 루프를 위해 현재 브라우저 탭 세션 안전 종료
                context.close()
                
            except Exception as e:
                # 에러 발생 시 예외를 잡아내고 다음 인덱스의 앱으로 강제 이동
                print(f" ❌ 에러 발생 및 건너뛰기 ({url}): {e}")
                continue
                
        # 모든 앱 순회 완료 후 브라우저 엔진 전체 종료
        browser.close()

if __name__ == "__main__":
    wake_up_apps()


    

# import requests
# import time
# from datetime import datetime

# # 깨우고 싶은 Streamlit 앱 주소들을 리스트에 넣으세요
# STREAMLIT_APPS = [
#     "https://quattrosimulator-kbsulzwvq8ucrcpph6rfg5.streamlit.app/",
#     "https://aitextdetector-lhbmnzgpagsda9nebjhpuj.streamlit.app/",
#     "https://faceswapdefender-8vnc2kab6pxahang3yuaqb.streamlit.app/",
#     "https://pwnedcredentialchecker-hmugyj9xsfalvzvrn4bfxi.streamlit.app/",  # 여기에 운영 중인 다른 URL들을 추가하세요
#     "https://carcostsimulator-e9prevei4pq9cap535vfp8.streamlit.app/",
#     "https://drivingdashboard-t8exrwypqvsce3gdq3cksd.streamlit.app/",
#     "https://f1-race-analyzer-9pbapphbkgmo6rguympwshf.streamlit.app/",
#     "https://kcarcrawler-5ryuwuw8izgjmqphppweyv.streamlit.app/",
#     "https://schoolzonefinesim-jamadbprromvbbwwzhgeui.streamlit.app/",
#     "https://cheiridrivingdashboard-cgpdknof3nnvufwaeyzkhr.streamlit.app/",
# ]

# def wake_up_apps():
#     now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#     print(f"[{now}] Streamlit 앱 수면 방지 Ping 작업 시작...")

#     # Modified headers to include a unique identifiable signature for tracker blocking
#     headers = {
#         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Polymath-Engine-Ping/1.0"
#     }

#     for url in STREAMLIT_APPS:
#         try:
#             # 💡 핵심: 찌를 때마다 꼬리표(현재 시간)를 다르게 달아서 무조건 새로고침 시키기
#             bypass_cache_url = f"{url}?ping={int(time.time())}"
            
#             response = requests.get(bypass_cache_url, headers=headers, timeout=60)
            
#             if response.status_code == 200:
#                 if "This app has gone to sleep" in response.text or "Zzzz" in response.text:
#                     print(f" 💤 이미 잠듦 (직접 브라우저에서 버튼 클릭 필요): {url}")
#                 else:
#                     print(f" ✅ 정상 작동 중 (수면 타이머 연장됨): {url}")
#             else:
#                 print(f" ⚠️ 접속 오류({response.status_code}): {url}")
                
#         except requests.exceptions.ReadTimeout:
#             print(f" ⏳ 타임아웃 (서버가 응답을 지연 중이며, 깨어나는 중일 수 있음): {url}")
#         except Exception as e:
#             print(f" ❌ 기타 에러 발생 ({url}): {e}")

# if __name__ == "__main__":
#     wake_up_apps()