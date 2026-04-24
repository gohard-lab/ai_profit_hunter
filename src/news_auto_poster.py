import base64
import requests
import markdown
import os
import re
import random
import urllib.parse
import json
import feedparser
from newspaper import Article
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from news_provider import fetch_naver_news, fetch_direct_rss, RSS_FEEDS
from tracker_exe import log_app_usage

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
    },
    # 🌍 글로벌 스포츠 및 국내 주요 리그 종합
    "글로벌_스포츠": [{"query": '"F1" OR "WEC" OR "해외축구" OR "프리미어리그" OR "챔피언스리그" OR "메이저리그" OR "MLB" OR "NBA" OR "테니스" OR "그랜드슬램" OR "프로배구" OR "V리그" OR "UFC"'}],
    
    # 🎬 할리우드/유럽 영화, 팝스타 가십 및 글로벌 엔터 트렌드
    "해외_엔터이슈": [{"query": '"할리우드" OR "해외연예" OR "팝스타" OR "빌보드" OR "아카데미 시상식" OR "칸 영화제" OR "넷플릭스 오리지널" OR "해외 가십"'}],

    # 🇰🇷 국내 주요 스포츠 및 K-엔터 (필요시 분리 사용)
    "국내_스포츠": [{"query": '"KBO" OR "프로야구" OR "K리그" OR "국가대표" OR "KBL" OR "한국시리즈"'}],
    "국내_연예": [{"query": '"K팝" OR "아이돌" OR "국내 개봉작" OR "드라마 시청률" OR "천만 영화"'}]
}

# RSS_FEEDS = {
#     # (기존 F1, IT 등 유지...)
#     "스포츠": [
#         "https://rss.donga.com/sports.xml",  # 스포츠동아
#         "https://www.chosun.com/arc/outboundfeeds/rss/category/sports/?outputType=xml" # 스포츠조선
#     ],
#     "연예_엔터": [
#         "https://rss.donga.com/ent.xml",     # 동아일보 연예
#         "https://www.chosun.com/arc/outboundfeeds/rss/category/entertainments/?outputType=xml" # 조선일보 연예
#     ]
# }

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

def fetch_news_by_topic(topic_name, search_query):
    # 1. Supabase 트래커 기록 (json 타입 details 포함)
    usage_details = json.dumps({
        "category": topic_name,
        "source": "naver_or_rss"
    }, ensure_ascii=False)
    log_app_usage("news_auto_poster_exe", f"search_{topic_name}", details=usage_details)

    print(f"🚀 [{topic_name}] 주제로 기사 수집 중...")
    
    # 2. 주제가 RSS 목록에 있으면 RSS 직행, 없으면 네이버 검색 API 사용
    if topic_name in RSS_FEEDS:
        news_items = []
        for rss_url in RSS_FEEDS[topic_name]:
            news_items.extend(fetch_direct_rss(rss_url))
    else:
        news_items = fetch_naver_news(search_query)
        
    # 3. 기사 원문 추출 (구글 우회 로직 제거됨)
    for item in news_items:
        real_url = item['link']
        title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
        
        print(f"👉 본문 추출 시도 중: {title[:40]}...")
        
        try:
            article = Article(real_url, language='ko')
            article.download()
            article.parse()
            
            content = article.text.strip()[:1500]
            if len(content) > 100:
                print("   ✅ 추출 성공!")
                # return title, content, real_url, article.top_image (기존 리턴 로직 유지)
        except Exception as e:
            print(f"   ㄴ ⚠️ 추출 실패: {e}")
            
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
        
        search_query = topic_info[0]['query']
        n_title, n_content, n_link, n_image_url = fetch_news_by_topic(topic_name, search_query)
        # n_title, n_content, n_link, n_image_url = fetch_news_by_topic(topic_info)


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