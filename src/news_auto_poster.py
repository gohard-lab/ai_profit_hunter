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

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_naver_news():
    """네이버 IT/과학 뉴스 헤드라인 하나와 링크를 가져옵니다."""
    url = "https://news.naver.com/section/105" # IT/과학 섹션
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # 가장 상단의 뉴스 기사 추출
    news_item = soup.select_one(".sa_text_title")
    title = news_item.text.strip()
    link = news_item['href']
    
    # 기사 본문 간단 수집
    detail_res = requests.get(link, headers=headers)
    detail_soup = BeautifulSoup(detail_res.text, "html.parser")
    content = detail_soup.select_one("#newsct_article").text.strip()
    
    # 이미지 추출을 위해 기사 원본 링크(link)도 같이 반환합니다.
    return title, content[:1500], link 

def rewrite_with_gpt(original_title, original_content):
    """대표님의 '잡학다식 개발자' 페르소나로 재작성"""
    prompt = f"""
    당신은 '잡학다식 개발자'라는 블로그를 운영하는 지적이고 솔직 담백한 개발자입니다.
    아래 뉴스 기사를 읽고, 독자들에게 유익한 정보를 전달하는 블로그 포스팅으로 재작성해주세요.
    
    - 말투: 차분하고 논리적이며, 불필요한 수식어(최고, 대박 등)는 뺍니다.
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
    """추출한 이미지를 워드프레스 미디어 라이브러리에 업로드합니다."""
    if not image_url:
        return None
    
    try:
        # 1. 이미지 다운로드
        img_res = requests.get(image_url, stream=True)
        img_data = img_res.content
        filename = image_url.split("/")[-1].split("?")[0]
        if not filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            filename = "news_thumbnail.jpg"

        # 2. 워드프레스 미디어 API로 전송
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

def post_to_wordpress(title, content, media_id=None):
    """재작성된 글과 업로드된 이미지를 묶어서 워드프레스에 발행합니다."""
    user_credentials = f"{WP_USER}:{WP_APP_PASS}"
    base64_credentials = base64.b64encode(user_credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {base64_credentials}',
        'Content-Type': 'application/json'
    }

    payload = {
        "title": title,
        "content": content,
        "status": "draft", 
        "categories": [1]
    }
    
    # 미디어 ID가 존재하면 특성 이미지로 추가
    if media_id:
        payload['featured_media'] = media_id

    res = requests.post(WP_URL, json=payload, headers=headers, verify=False)
    
    if res.status_code == 201:
        # 트래커: 포스팅 성공 기록 (이미지 유무 포함)
        log_app_usage("news_auto_poster", "post_success", details={
            "title": title,
            "has_image": bool(media_id),
            "status_code": 201
        })
        print(f"✅ 성공: {title} 가 임시저장되었습니다.")
    else:
        # 트래커: 포스팅 실패 기록
        log_app_usage("news_auto_poster", "post_failed", details={
            "title": title,
            "error": res.text,
            "status_code": res.status_code
        })
        print(f"❌ 실패: {res.status_code} - {res.text}")

if __name__ == "__main__":
    try:
        # 트래커: 봇 작동 시작 기록
        log_app_usage("news_auto_poster", "bot_started", details={"action": "cron_execution"})
        
        print("🚀 네이버 뉴스 수집 중...")
        n_title, n_content, n_link = fetch_naver_news()
        
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
        post_to_wordpress(n_title, html_content, media_id)
        
    except Exception as e:
        # 트래커: 실행 중 크리티컬 에러 기록
        log_app_usage("news_auto_poster", "bot_error", details={"error": str(e)})
        print(f"❗ 에러 발생: {e}")