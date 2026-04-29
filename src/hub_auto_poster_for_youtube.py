import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from supabase import create_client
from googleapiclient.discovery import build
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")
WP_URL = f"{os.getenv('WP_URL')}/wp-json/wp/v2/posts"
WP_USER = os.getenv("WP_USER")
WP_APP_PW = os.getenv("WP_APP_PASSWORD")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Constants for this specific bot
APP_NAME = "youtube_hub_sync"

# 워드프레스 ID는 관리자 페이지에서 확인 후 숫자로 수정.
TAG_MAP = {
    "Streamlit": 54,
    "수집": 62,
    "크롤링": 55,
    "Supabase": 56,
    "M2": 65,
    "F1": 58,
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

def post_to_wordpress(title, description, video_id):
    """Post YouTube content to WordPress via REST API"""
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Global/Standard content structure
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
    # 자동으로 관련 태그들만 골라냅니다
    target_tags = get_dynamic_tags(title, description)

    payload = {
        "title": title,
        "content": content,
        "status": "publish",
        "categories": [5],  # 유튜브 카테고리 고정
        "tags": target_tags # 자동으로 선별된 태그
    }
    
    res = requests.post(WP_URL, json=payload, auth=HTTPBasicAuth(WP_USER, WP_APP_PW), timeout=20)
    return res.status_code == 201

def main():
    print(f"[{datetime.now()}] Starting YouTube Hub Sync...")
    videos = get_latest_videos()
    
    for video in videos:
        v_id = video['id']['videoId']
        v_title = video['snippet']['title']
        
        # 1. Check for duplicates using app_name and content_id
        check = supabase.table("usage_logs") \
            .select("id") \
            .eq("app_name", APP_NAME) \
            .eq("content_id", v_id) \
            .execute()
        
        if not check.data:
            print(f"New video found: {v_title}")
            # 2. Attempt to post to WordPress
            if post_to_wordpress(v_title, video['snippet']['description'], v_id):
                # 3. Log success to usage_logs
                supabase.table("usage_logs").insert({
                    "app_name": APP_NAME,
                    "content_id": v_id,
                    "action": "wp_post_success",
                    "details": {"title": v_title, "source": "youtube"}
                }).execute()
                
                # Telegram Notification (Omitted for brevity)
                send_telegram_msg(f"🚀 <b>Posted:</b> {v_title}")
        else:
            print(f"Already synced: {v_title}")

if __name__ == "__main__":
    main()