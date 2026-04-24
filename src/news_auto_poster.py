import base64
import requests
import markdown
import os
import re
import random
import urllib.parse
import feedparser
from newspaper import Article
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

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

# --- [토픽 설정 정보 추가] ---
TOPIC_CONFIG = {
    "F1_모터스포츠": {
        "query": "F1 레이싱 OR WEC",
        "cat_id": [10],   # 예: F1 인사이트 카테고리 ID
        "tag_ids": [101], # 예: f1-motorsports 태그 ID (숫자로 입력)
        "prompt": "자동차 전문 기자이자 M2 오너인 개발자 입장에서 F1 기술이 양산차에 미치는 영향을 차분하고 논리적으로 분석해 줘."
    },
    "올드무비": {
        "query": '"고전 영화" OR "클래식 영화" OR "명작 재개봉" OR "레트로 영화"',
        "cat_id": [15],   # 기존에 넣으신 ID 유지
        "tag_ids": [102], # 기존에 넣으신 ID 유지
        "prompt": "영화 매니아 개발자로서 아날로그 감성이 느껴지는 올드무비의 매력과 감상을 솔직 담백하게 서술해 줘."
    },
    "레트로기기": {
        "query": '"카세트 플레이어" OR "소니 워크맨" OR "카세트 워크맨" OR "빈티지 오디오" OR "LP 플레이어"',
        "cat_id": [20],
        "tag_ids": [103],
        "prompt": "클래식 카세트 수집가로서 아날로그 기기가 주는 향수와 하드웨어적 매력을 객관적으로 설명해 줘."
    },
    "IT트렌드": {
        "query": "파이썬 개발 OR 소프트웨어 트렌드",
        "cat_id": [5],    # IT 뉴스 브리핑 카테고리 ID
        "tag_ids": [104], # it-tech-trends 태그 ID
        "prompt": "IT/과학 트렌드를 분석하는 잡학다식 개발자로서, 이 기술이 실무에 미칠 영향을 명확하게 정리해 줘."
    }
}

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

def fetch_news_by_topic(topic_info):
    """구글 뉴스 RSS를 검색하고 newspaper3k로 본문과 이미지를 스마트하게 추출합니다."""
    encoded_query = urllib.parse.quote(topic_info["query"])
    # 구글 뉴스 한국어 RSS 링크
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    feed = feedparser.parse(rss_url)

    # 🚨 여기에 진단용 엑스레이 1번 추가
    print(f"🔍 구글에서 찾아온 기사 개수: {len(feed.entries)}개")
    
    for entry in feed.entries:
        title = entry.title
        link = entry.link
        
        print(f"👉 본문 추출 시도 중: {title[:40]}...") 
        
        if is_already_posted(link):
            continue
            
        try:            
            real_url = link
            print("   ㄴ 🛡️ 헤드리스 브라우저 엔진 가동 (구글 보안망 정면 돌파 중)...")
            
            # [최종 병기] Playwright로 브라우저를 직접 띄워 구글의 자바스크립트 우회(Redirect)를 통과합니다.
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                context.add_cookies([{"name": "CONSENT", "value": "YES+cb.20210720-07-p0.en+FX+410", "domain": ".google.com", "path": "/"}])
                page = context.new_page()
                
                try:
                    # 구글 뉴스 링크 접속
                    page.goto(link, timeout=15000)
                    
                    # 브라우저의 네트워크 통신이 완전히 조용해질 때까지(이동이 끝날 때까지) 대기
                    try:
                        page.wait_for_load_state("networkidle", timeout=6000)
                    except:
                        pass # 타임아웃이 나도 멈추지 않고 계속 진행
                        
                    real_url = page.url
                    
                    # 🚨 여전히 구글 중간 경유지에 갇혀 있다면?
                    if "google.com" in real_url:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(real_url)
                        qs = urllib.parse.parse_qs(parsed.query)
                        
                        # 1. 주소창 파라미터(url= 또는 q=)에 진짜 주소가 숨어있는 경우
                        if 'url' in qs:
                            real_url = qs['url'][0]
                        elif 'q' in qs:
                            real_url = qs['q'][0]
                        else:
                            # 2. 화면에 렌더링된 "이동하기" 하이퍼링크를 강제로 찾아내기
                            links = page.evaluate("() => Array.from(document.querySelectorAll('a')).map(a => a.href)")
                            for href in links:
                                if href.startswith("http") and not any(bad in href.lower() for bad in ["google", "gstatic", "youtube", "w3.org", "schema.org"]):
                                    real_url = href
                                    break
                except Exception as e:
                    pass
                finally:
                    browser.close()
                    
            if "google.com" in real_url:
                print("   ㄴ ⚠️ 실제 언론사 주소 확보 실패. 다음으로 넘어갑니다.")
                continue

            print(f"   ㄴ 🔗 최종 도착 언론사: {real_url[:60]}...")
            
            # 4. 진짜 주소를 찾았으니 newspaper로 텍스트/이미지 추출
            article = Article(real_url, language='ko')
            article.download()
            article.parse()
            
            content = article.text.strip()[:1500]
            image_url = article.top_image
            
            if len(content) > 100: 
                return title, content, real_url, image_url
            else:
                print(f"   ㄴ ⚠️ 텍스트 부족 스킵 (길이: {len(content)}자)")
                
        except Exception as e:
            print(f"   ㄴ ⚠️ 접속 또는 추출 실패: {e}")
            continue
            
    return None, None, None, None

def rewrite_with_gpt(original_title, original_content, topic_prompt):
    """주제별 맞춤형 페르소나로 재작성"""
    prompt = f"""
    당신은 '잡학다식 개발자'라는 블로그를 운영하는 지적이고 솔직 담백한 개발자입니다.
    아래 뉴스 기사를 읽고, 독자들에게 유익한 정보를 전달하는 블로그 포스팅으로 재작성해주세요.
    
    [특별 지시사항]: {topic_prompt}
    
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

def post_to_wordpress(title, content, cat_ids, tag_ids, media_id=None, news_link=None):
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
        "categories": cat_ids,
        "tags": tag_ids
    }
    
    if media_id:
        payload['featured_media'] = media_id

    res = requests.post(WP_URL, json=payload, headers=headers, verify=False)
    
    if res.status_code == 201:
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
        # 등록된 관심사 중 하나를 랜덤으로 선택하여 실행합니다.
        topic_name = random.choice(list(TOPIC_CONFIG.keys()))
        topic_info = TOPIC_CONFIG[topic_name]
        
        log_app_usage("news_auto_poster", "bot_started", details={"action": "cron_execution", "topic": topic_name})
        print(f"🚀 [{topic_name}] 주제로 구글 뉴스 검색 수집 중...")
        
        n_title, n_content, n_link, n_image_url = fetch_news_by_topic(topic_info)
        
        if not n_title:
            print(f"🛑 [{topic_name}] 관련 새로운 뉴스가 없습니다. 종료합니다.")
            exit()
            
        media_id = None
        if n_image_url:
            print("📤 워드프레스에 이미지 업로드 중...")
            media_id = upload_image_to_wp(n_image_url)
        
        print("🤖 GPT 재가공 중 (페르소나 적용)...")
        # GPT 재가공 함수 호출 시 topic_info["prompt"]가 추가로 들어갑니다.
        refined_content = rewrite_with_gpt(n_title, n_content, topic_info["prompt"])
        
        print("🔄 마크다운을 HTML로 변환 중...")
        html_content = markdown.markdown(refined_content, extensions=['extra'])
        
        print("📤 워드프레스 전송 중...")
        post_to_wordpress(n_title, html_content, topic_info["cat_id"], topic_info["tag_ids"], media_id, n_link)
        
    except Exception as e:
        log_app_usage("news_auto_poster", "bot_error", details={"error": str(e)})
        print(f"❗ 에러 발생: {e}")