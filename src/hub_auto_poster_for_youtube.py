import os
import requests
from requests.auth import HTTPBasicAuth
from supabase import create_client
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 워드프레스 설정
WP_URL = "https://your-blog.com/wp-json/wp/v2/posts"
WP_USER = os.getenv("WP_USER")
WP_APP_PW = os.getenv("WP_APP_PASSWORD") # 워드프레스 앱 비밀번호

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def post_to_wordpress(title, content, category_id, tags):
    """워드프레스 REST API를 이용한 포스팅"""
    payload = {
        "title": title,
        "content": content,
        "status": "publish",
        "categories": [category_id],
        "tags": tags
    }
    
    res = requests.post(
        WP_URL,
        json=payload,
        auth=HTTPBasicAuth(WP_USER, WP_APP_PW)
    )
    
    if res.status_code == 201:
        print(f"✅ 포스팅 성공: {title}")
        return True
    return False

def sync_new_content():
    """신규 콘텐츠(유튜브, 스트림릿 등) 감지 및 동기화 로직"""
    # 1. Supabase에서 아직 워드프레스에 올라가지 않은 데이터 조회
    # (이미 만들어두신 테이블에 'is_posted' 컬럼이 있다고 가정)
    new_apps = supabase.table("apps_registry").select("*").eq("is_posted", False).execute()

    for app in new_apps.data:
        title = f"[신규 배포] {app['app_name']}"
        body = f"""
        <h3>{app['description']}</h3>
        <p>새로운 스트림릿 앱이 배포되었습니다.</p>
        <a href="{app['url']}" target="_blank">👉 앱 바로가기</a>
        """
        
        # 워드프레스 발행 시도
        if post_to_wordpress(title, body, category_id=5, tags=["Streamlit", "Python"]):
            # 성공 시 DB 상태 업데이트
            supabase.table("apps_registry").update({"is_posted": True}).eq("id", app["id"]).execute()

if __name__ == "__main__":
    sync_new_content()