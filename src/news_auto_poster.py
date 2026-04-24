import base64
import requests
import markdown
import os
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

# 백그라운드 봇 환경이므로 exe용 트래커를 사용합니다.
from tracker_exe import log_app_usage 

# --- [설정 정보] ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WP_URL = "https://gohard.pe.kr/index.php?rest_route=/wp/v2/posts/"
WP_USER = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

# Supabase 환경 변수 (.env에 설정되어 있어야 합니다)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def is_already_posted(link):
    """Supabase usage_logs 테이블을 조회하여 중복 기사인지 확인합니다."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Supabase 접속 정보가 없어 중복 체크를 건너뜁니다.")
        return False

    url = f"{SUPABASE_URL}/rest/v1/usage_logs"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    # app_name이 news_auto_poster이고, action이 post_success이며, 
    # details JSONB 컬럼 안의 'link' 값이 현재 기사 링크와 동일한 레코드를 1개만 찾습니다.
    params = {
        "select": "id",
        "app_name": "eq.news_auto_poster",
        "action": "eq.post_success",
        "details->>link": f"eq.{link}",
        "limit": "1"
    }
    
    try:
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            data = res.json()
            return len(data) > 0  # 데이터가 존재하면 이미 포스팅된 기사
        return False
    except Exception as e:
        print(f"⚠️ DB 조회 실패: {e}")
        return False

def fetch_naver_news():
    """네이버 IT/과학 뉴스에서 '아직 올리지 않은' 뉴스를 찾습니다."""
    url = "https://news.naver.com/section/105"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    
    news_items = soup.select(".sa_text_title")
    
    for item in news_items:
        title = item.text.strip()
        link = item['href']
        
        # Supabase DB 조회로 중복 검사
        if is_already_posted(link):
            print(f"⏭️ 건너뜀 (이미 포스팅됨): {title}")
            continue
            
        # 새로운 뉴스를 찾았다면 상세 내용 수집
        detail_res = requests.get(link, headers=headers)
        detail_soup = BeautifulSoup(detail_res.text, "html.parser")
        article_body = detail_soup.select_one("#newsct_article")
        
        if article_body:
            # 기사 원문 링크(link)도 함께 반환합니다.
            return title, article_body.text.strip()[:1500], link
            
    return None, None, None

def rewrite_with_gpt(original_title, original_content):
    """'잡학다식 개발자' 페르소나로 재작성"""
    prompt = f"""
    당신은 '잡학다식 개발자'라는 블로그를 운영하는 지적이고 솔직 담백한 개발자입니다.
    아래 뉴스 기사를 읽고, 독자들에게 유익한 정보를 전달하는 블로그 포스팅으로 재작성해주세요.
    
    - 말투: 차분하고 논리적이며, 불필요한 수식어는 뺍니다.
    - 형식: 마크다운(Markdown)을 사용해 가독성을 높입니다.
    - 금기: 'Tired' 같은 유치한 말장난, 오버하는 말투 절대 금지. 출처(CITE) 표기 생략.
    - 구조: 서론(이슈 소개) - 본론(핵심 분석) - 결론(개발자로서의 견해)
    
    제목: {original_title}
    본문 내용: {original_content}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def get_og_image(news_url):
    """기사 원문에서 대표 이미지(og:image) 주소를 추출합니다."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(news_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'lxml')
        
        og_image = soup.find("meta", property="og:image")
        return og_image["content"] if og_image else None
    except Exception as e:
        print(f"⚠️ 이미지 추출 실패: {e}")
        return None

def upload_image_to_wp(image_url):
    """이미지를 워드프레스 미디어 라이브러리에 업로드합니다."""
    if not image_url:
        return None
    
    try:
        img_res = requests.get(image_url, stream=True)
        img_data = img_res.content
        filename = image_url.split("/")[-1].split("?")[0]
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            filename = "news_thumbnail.jpg"

        user_credentials = f"{WP_USER}:{WP_APP_PASS}"
        base64_credentials = base64.b64encode(user_credentials.encode()).decode()
        
        media_url = "https://gohard.pe.kr/index.php?rest_route=/wp/v2/media/"
        headers = {
            'Authorization': f'Basic {base64_credentials}',
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'image/jpeg' 
        }
        
        response = requests.post(media_url, data=img_data, headers=headers, verify=False)
        
        if response.status_code == 201:
            return response.json()['id']
        return None
    except Exception as e:
        print(f"⚠️ 미디어 업로드 실패: {e}")
        return None

def post_to_wordpress(title, content, media_id=None, news_link=None):
    """글을 발행하고, 성공 시 Supabase에 링크 정보를 포함하여 기록합니다."""
    user_credentials = f"{WP_USER}:{WP_APP_PASS}"
    base64_credentials = base64.b64encode(user_credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {base64_credentials}',
        'Content-Type': 'application/json'
    }

    payload = {
        "title": title,
        "content": content,
        "status": "publish", 
        "categories": [1]
    }
    
    if media_id:
        payload['featured_media'] = media_id

    res = requests.post(WP_URL, json=payload, headers=headers, verify=False)
    
    if res.status_code == 201:
        # 트래커: details 컬럼에 link를 저장하여 다음 조회 시 중복 검증에 사용합니다.
        log_app_usage("news_auto_poster", "post_success", details={
            "title": title,
            "link": news_link,
            "has_image": bool(media_id),
            "status_code": 201
        })
        print(f"✅ 성공: {title} 가 발행되었습니다.")
    else:
        log_app_usage("news_auto_poster", "post_failed", details={
            "title": title,
            "error": res.text,
            "status_code": res.status_code
        })
        print(f"❌ 실패: {res.status_code} - {res.text}")

if __name__ == "__main__":
    try:
        log_app_usage("news_auto_poster", "bot_started", details={"action": "cron_execution"})
        
        print("🚀 네이버 뉴스 수집 중...")
        n_title, n_content, n_link = fetch_naver_news()
        
        if not n_title:
            print("🛑 새로운 뉴스가 없습니다. 종료합니다.")
            exit()
            
        print("📸 대표 이미지 찾는 중...")
        image_url = get_og_image(n_link)
        media_id = None
        if image_url:
            print("📤 워드프레스에 이미지 업로드 중...")
            media_id = upload_image_to_wp(image_url)
        
        print("🤖 GPT 재가공 중 (잡학다식 개발자 버전)...")
        refined_content = rewrite_with_gpt(n_title, n_content)
        
        print("🔄 마크다운을 HTML로 변환 중...")
        html_content = markdown.markdown(refined_content, extensions=['extra'])
        
        print("📤 워드프레스 전송 중...")
        post_to_wordpress(n_title, html_content, media_id, n_link)
        
    except Exception as e:
        log_app_usage("news_auto_poster", "bot_error", details={"error": str(e)})
        print(f"❗ 에러 발생: {e}")