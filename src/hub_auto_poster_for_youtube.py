import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from supabase import create_client
from googleapiclient.discovery import build
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Load environment variables
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# 만약 여기서 하나라도 None이 나오면 401 에러가 발생합니다.
if not url or not key:
    print("Error: Supabase 환경 변수가 비어 있습니다!")
    exit()
    

# Configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
WP_URL = os.getenv('WP_URL')
WP_USER = os.getenv("WP_USER")
WP_APP_PW = os.getenv("WP_APP_PASS")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

# Constants for this specific bot
APP_NAME = "youtube_hub_sync"

# 워드프레스 ID는 관리자 페이지에서 확인 후 숫자로 수정.
TAG_MAP = {
    "streamlit": 54,
    "수집": 62,
    "크롤링": 55,
    "supabase": 56,
    "m2": 65,
    "f1": 58,
    "자동차": 59,
    "스릴러": 18,
    "미스터리": 66,
    "아날로그": 37,
    "카세트": 24,
    "오디오": 61,
    "수집": 62,
    "일기": 63,
    "튜토리얼": 74,
    "파이썬": 67,
    "잡학다식": 66
}

DEFAULT_TAGS = [53]  # '유튜브' 같은 기본 태그 ID

# Initialize Clients
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def get_dynamic_tags(title, description):
    """제목과 설명에서 키워드를 찾아 태그 ID 리스트를 반환"""
    tags = set(DEFAULT_TAGS) # 기본 태그 포함 (중복 방지 위해 set 사용)
    
    combined_text = (title + " " + description).lower()
    
    for keyword, tag_id in TAG_MAP.items():
        if keyword.lower() in combined_text:
            tags.add(tag_id)
            
    return list(tags)

def send_telegram_msg(message):
    """Send HTML formatted notification to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_latest_videos():
    """Fetch the latest videos from the YouTube channel"""
    request = youtube.search().list(
        channelId=YOUTUBE_CHANNEL_ID,
        part="snippet",
        order="date",
        maxResults=5,
        type="video"
    )
    response = request.execute()
    return response.get("items", [])

def upload_youtube_thumbnail(video_id):
    """유튜브 썸네일을 다운로드하여 워드프레스 미디어로 업로드하고 ID를 반환"""
    # 유튜브 고화질 썸네일 주소
    thumb_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    img_res = requests.get(thumb_url)
    
    if img_res.status_code != 200:
        print(f" ⚠️ 썸네일 다운로드 실패: {video_id}")
        return None
        
    # wp_media_url = f"{os.getenv('WP_URL')}/wp-json/wp/v2/media"
    wp_media_url = os.getenv('WP_URL').replace('/posts', '/media')
    headers = {
        "Content-Disposition": f"attachment; filename=youtube_{video_id}.jpg",
        "Content-Type": "image/jpeg"
    }
    
    # 워드프레스에 이미지 업로드
    wp_user = os.getenv('WP_USER')
    wp_password = os.getenv('WP_APP_PASS')
    
    upload_res = requests.post(
        wp_media_url,
        headers=headers,
        data=img_res.content,
        auth=HTTPBasicAuth(wp_user, wp_password),
        timeout=20
    )
    
    if upload_res.status_code == 201:
        return upload_res.json().get('id')
    return None

def post_to_wordpress(title, description, video_id):
    """Post YouTube content to WordPress via REST API with duplication protection"""
    
    # 1. 세션 및 재시도 횟수 0 설정 (안전장치)
    session = requests.Session()
    retries = Retry(total=0, backoff_factor=0, status_forcelist=[])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    content = f"""
    <p>{description}</p>
    <div class="wp-block-embed is-type-video is-provider-youtube">
        <figure class="wp-block-embed__wrapper">
            {video_url}
        </figure>
    </div>
    <br>
    <p>※ 본 프로그램은 더 나은 서비스 제공과 에러 수정을 위해 익명화된 최소한의 사용 통계(기능 클릭 수 등)를 수집합니다. (개인 식별 정보는 일절 수집하지 않습니다.)</p>
    """

    try:
        target_tags = get_dynamic_tags(title, description)
        media_id = upload_youtube_thumbnail(video_id)

        payload = {
            "title": title,
            "content": content,
            "status": "publish",
            "slug": video_id,   # 중복 생성 방지용 고유 키
            "categories": [53],
            "tags": target_tags
        }
        
        if media_id:
            payload["featured_media"] = media_id

        # ✅ 수정 포인트: 중복 호출 제거 및 단일 전송 설정
        print(f"🚨 [전송 시도] {title}")
        
        res = session.post(
            WP_URL, 
            json=payload, 
            auth=HTTPBasicAuth(WP_USER, WP_APP_PW), 
            timeout=40, 
            allow_redirects=False
        )

        if res.status_code not in [201, 301, 302]:
            print(f"DEBUG WP Error: {res.status_code} - {res.text}")
            return False
        
        return True

    except Exception as e:
        print(f" ❌ 데이터 구성 또는 API 호출 중 에러 발생: {e}")
        return False
    finally:
        session.close()     

def main():
    print(f"[{datetime.now()}] Starting YouTube Hub Sync...")
    videos = get_latest_videos()
    
    for video in videos:
        # 1. 안전하게 데이터 추출 (snippet 구조 대응)
        snippet = video.get('snippet', {})
        v_title = snippet.get('title') or video.get('title', 'Unknown Title')
        v_description = snippet.get('description', '')
        
        # 비디오 ID 추출 (API 응답 형태에 따라 대응)
        v_id = video.get('id', {})
        if isinstance(v_id, dict):
            v_id = v_id.get('videoId')
        else:
            v_id = video.get('id')

        if not v_id:
            print(f"DEBUG: 비디오 ID를 찾을 수 없어 건너뜁니다: {v_title}")
            continue

        print(f"DEBUG: Checking {v_title}...")

        # 2. Supabase 중복 체크 (app_name과 content_id 활용)
        try:
            check = supabase.table("usage_logs") \
                .select("id") \
                .eq("app_name", APP_NAME) \
                .eq("content_id", v_id) \
                .execute()
            
            if not check.data:
                print(f"🚀 [전송 시작] {v_title}")

                print(f"New video found: {v_title}")
                
                # 3. 워드프레스 포스팅 호출 (인자 3개: 제목, 내용, ID)
                if post_to_wordpress(v_title, v_description, v_id):
                    print(f"✅ [1차 전송 완료] {v_title}")
                
                    # 💡 핵심: 중복 전송 방지를 위해 2초간 강제 휴식
                    import time
                    time.sleep(2)

                    # 4. 성공 시 Supabase 로그 남기기
                    supabase.table("usage_logs").insert({
                        "app_name": APP_NAME,
                        "content_id": v_id,
                        "action": "wp_post_success",
                        "details": {"title": v_title, "source": "youtube"}
                    }).execute()

                    print(f"💾 [DB 기록 완료] {v_title}")
                    
                    # 5. 텔레그램 알림
                    send_telegram_msg(f"🚀 <b>Posted:</b> {v_title}")
                else:
                    print(f" ❌ 워드프레스 포스팅 실패: {v_title}")
            else:
                print(f"Already synced: {v_title}")

        except Exception as e:
            print(f"DEBUG: 처리 중 에러 발생 ({v_title}) -> {e}")

if __name__ == "__main__":
    main()