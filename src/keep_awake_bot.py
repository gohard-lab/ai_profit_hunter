from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# 요청하신 데이터 트래커 연동 (웹용)
try:
    from tracker_web import log_app_usage
    log_app_usage("github_actions_bot", "keep_awake_run")
except ImportError:
    pass

URLS = [
    "https://carcostsimulator-e9prevei4pq9cap535vfp8.streamlit.app/",
    "https://drivingdashboard-t8exrwypqvsce3gdq3cksd.streamlit.app/",
    "https://f1-race-analyzer-9pbapphbkgmo6rguympwshf.streamlit.app/",
    "https://kcarcrawler-5ryuwuw8izgjmqphppweyv.streamlit.app/",
    "https://schoolzonefinesim.streamlit.app/",
    "https://cheiridrivingdashboard-cgpdknof3nnvufwaeyzkhr.streamlit.app/"
]

def wake_apps():
    options = Options()
    options.add_argument("--headless=new") # 에러 방지를 위해 최신 헤드리스 모드 필수,
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    for url in URLS:
        print(f"Waking up {url}...")
        try:
            driver.get(url)
            # 자바스크립트가 실행되고 실제 앱이 렌더링될 때까지 충분히 대기
            time.sleep(5) 
            print(f"-> Success: {driver.title}")
        except Exception as e:
            print(f"-> Error: {e}")
            
    driver.quit() # 헤드리스 실행 후 kill 하는 부분(메모리 정리)

if __name__ == "__main__":
    wake_apps()