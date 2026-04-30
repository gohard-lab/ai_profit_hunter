import time
import base64
import requests
import markdown
import os
import re
import random
import urllib.parse
import json
import feedparser
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from newspaper import Article
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from news_provider import fetch_naver_news, fetch_direct_rss, RSS_FEEDS
from tracker_exe import log_app_usage 

# --- [설정 정보] ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WP_URL = "https://gohard.pe.kr/index.php?rest_route=/wp/v2/posts/"
# 수정 제안: 뒤에 붙은 'posts/'를 떼고 기본 경로만 설정
# 이렇게 해두면 봇이 자동으로 뒤에 /posts를 붙여서 .../wp/v2/posts로 완성해 줌.
# WP_URL = "https://gohard.pe.kr/index.php?rest_route=/wp/v2"
WP_USER = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

# Supabase 환경 변수
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 종합뉴스 카테고리 ID
TOTAL_NEWS_CAT_ID = 47

# --- [토픽 설정 정보] ---
TOPIC_CONFIG = {
    "F1_모터스포츠": {
        "query": '"FIA" OR "F1" OR "MOTOR RACING" OR "WEC"',
        "cat_id": 14,
        "tag_ids": [20],
        "prompt": "자동차 전문 기자이자 M2 오너인 개발자 입장에서 F1 기술이 양산차에 미치는 영향을 차분하고 논리적으로 분석해 줘."
    },
    "올드무비": {
        "query": '"고전 영화" OR "클래식 영화" OR "명작 재개봉" OR "레트로 영화"',
        "cat_id": 15,
        "tag_ids": [22, 23],
        "prompt": "영화 매니아 개발자로서 아날로그 감성이 느껴지는 올드무비의 매력과 감상을 솔직 담백하게 서술해 줘."
    },
    "레트로기기": {
        "query": '"카세트 플레이어" OR "소니 워크맨" OR "카세트 워크맨" OR "빈티지 오디오" OR "LP 플레이어"',
        "cat_id": 17,
        "tag_ids": [36, 37],
        "prompt": "클래식 카세트 수집가로서 아날로그 기기가 주는 향수와 하드웨어적 매력을 객관적으로 설명해 줘."
    },
    "IT트렌드": {
        "query": '"파이썬 개발" OR "소프트웨어 트렌드"',
        "cat_id": 7,
        "tag_ids": [25, 27],
        "prompt": "IT/과학 트렌드를 분석하는 잡학다식 개발자로서, 이 기술이 실무에 미칠 영향을 명확하게 정리해 줘."
    },
    "글로벌_스포츠": {
        "query": '"F1" OR "WEC" OR "해외축구" OR "프리미어리그" OR "챔피언스리그" OR "메이저리그" OR "MLB" OR "NBA" OR "테니스" OR "그랜드슬램" OR "프로배구" OR "V리그" OR "UFC"',
        "cat_id": 29,
        "tag_ids": [46, 45, 28, 44],
        "prompt": "글로벌 스포츠 전문 기자로서 경기의 핵심 포인트와 관전 요소를 데이터 중심으로 흥미진진하게 분석해 줘. 가독성을 위해 불렛포인트를 활용해."
    },
    "해외_엔터이슈": {
        "query": '"할리우드" OR "해외연예" OR "팝스타" OR "빌보드" OR "아카데미 시상식" OR "칸 영화제" OR "넷플릭스 오리지널" OR "해외 가십"',
        "cat_id": 34,
        "tag_ids": [38],
        "prompt": "할리우드 소식에 정통한 엔터테인먼트 칼럼니스트로서 현지 분위기와 비하인드 스토리를 포함해 솔직 담백하고 위트 있게 서술해 줘."
    },
    "국내_스포츠": {
        "query": '"KBO" OR "프로야구" OR "K리그" OR "국가대표" OR "KBL" OR "한국시리즈"',
        "cat_id": 32,
        "tag_ids": [39, 45, 28],
        "prompt": "국내 스포츠 팬들의 열정을 대변하는 분석가로서 경기의 흐름과 선수들의 활약상을 현장감 넘치게 정리해 줘."
    },
    "국내_연예": {
        "query": '"K팝" OR "아이돌" OR "국내 개봉작" OR "드라마 시청률" OR "천만 영화"',
        "cat_id": 35,
        "tag_ids": [42, 40],
        "prompt": "대한민국 대중문화 평론가로서 최신 트렌드와 작품의 흥행 요인을 날카롭고 지적으로 분석해서 독자들에게 소개해 줘."
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
    
    # 💡 수정 포인트: action을 'post_success'로 명확히 고정합니다.
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
            return len(data) > 0
        return False
    except Exception as e:
        print(f"⚠️ DB 조회 실패: {e}")
        return False

def fetch_news_by_topic(topic_name, search_query):
    # 1. Supabase 트래커 기록
    usage_details = json.dumps({
        "category": topic_name,
        "source": "naver_or_rss"
    }, ensure_ascii=False)
    log_app_usage("news_auto_poster", f"search_{topic_name}", details=usage_details)

    print(f"🚀 [{topic_name}] 주제로 기사 수집 중...")
    
    # 2. 뉴스 수집
    if topic_name in RSS_FEEDS:
        news_items = []
        for rss_url in RSS_FEEDS[topic_name]:
            news_items.extend(fetch_direct_rss(rss_url))
    else:
        news_items = fetch_naver_news(search_query)
        
    # 💡 핵심 수정 포인트: 중복 체크를 '리스트 루프' 안으로 이동!
    # 이렇게 하면 1번 뉴스가 중복이어도 포기하지 않고 2번 뉴스를 시도합니다.
    for item in news_items:
        real_url = item['link']
        title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
        
        # 여기서 먼저 중복 검사
        if is_already_posted(real_url):
            print(f"   ⏩ [중복 패스] 이미 발행된 기사입니다: {title[:30]}...")
            continue # 다음 뉴스로 넘어감
            
        print(f"👉 새 기사 본문 추출 시도 중: {title[:40]}...")
        
        try:
            article = Article(real_url, language='ko')
            article.download()
            article.parse()
            
            content = article.text.strip()[:1500]
            if len(content) > 100:
                print("   ✅ 추출 성공!")
                # 성공하면 즉시 반환 (루프 종료)
                return title, content, real_url, article.top_image
            
        except Exception as e:
            print(f"   ㄴ ⚠️ 추출 실패: {e}")
            
    # 모든 기사가 중복이거나 추출 실패일 때만 None 반환
    return None, None, None, None

def rewrite_with_gpt(original_title, original_content, topic_prompt):
    """주제별 맞춤형 페르소나로 재작성 및 영어 슬러그 생성"""
    prompt = f"""
    당신은 '잡학다식 개발자'라는 블로그를 운영하는 지적이고 솔직 담백한 개발자입니다.
    아래 뉴스 기사를 읽고, 독자들에게 유익한 정보를 전달하는 블로그 포스팅을 작성하세요.
    
    [특별 지시사항]: {topic_prompt}
    
    - 말투: 차분하고 논리적이며, 불필요한 수식어는 뺍니다.
    - 형식: 본문은 마크다운(Markdown)을 사용해 가독성을 높입니다.
    - 금기: 유치한 말장난, 오버하는 말투 절대 금지. 출처(CITE) 표기 생략.
    - 구조: 서론(이슈 소개) - 본론(핵심 분석) - 결론(개발자로서의 견해)
    - 추가 작업: 이 포스팅에 어울리는 SEO 친화적인 짧은 영어 URL 슬러그를 생성하세요. (예: apple-vision-pro-review)

    반드시 아래 JSON 형식으로만 응답하세요:
    {{
      "content": "재작성된 마크다운 본문 전체",
      "slug": "생성된-영어-url-슬러그"
    }}
    
    원본 제목: {original_title}
    원본 본문: {original_content}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={ "type": "json_object" },
            messages=[{"role": "user", "content": prompt}]
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("content", ""), result.get("slug", "")
    except Exception as e:
        print(f"❌ GPT 재가공 중 에러 발생: {e}")
        return None, None
    
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

def post_to_wordpress(title, content, cat_ids, tag_ids, media_id=None, news_link=None, slug=None):
    """글을 발행하고, 성공 시 Supabase에 링크 정보를 포함하여 기록합니다."""
    user_credentials = f"{WP_USER}:{WP_APP_PASS}"
    base64_credentials = base64.b64encode(user_credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {base64_credentials}',
        'Content-Type': 'application/json'
    }

    # 💡 수정 포인트: payload에 "slug": slug 를 반드시 추가해야 합니다!
    payload = {
        "title": title,
        "content": content,
        "status": "publish", 
        "categories": cat_ids,
        "tags": tag_ids,
        "slug": slug
    }
    
    if media_id:
        payload['featured_media'] = media_id

    res = requests.post(WP_URL, json=payload, headers=headers, verify=False)
    
    if res.status_code == 201:
        # 💡 수정 포인트: 로그를 하나로 통일하고 완벽한 데이터를 남깁니다.
        log_app_usage("news_auto_poster", "post_success", details={
            "title": title,
            "link": news_link,     # 중복 체크의 핵심 기준!
            "slug": slug,          # 생성된 영문 주소 기록
            "cat_ids": cat_ids,    # 배포된 카테고리 ID들 기록
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
    for topic_name in TOPIC_CONFIG.keys():
        try:
            topic_info = TOPIC_CONFIG[topic_name]
            log_app_usage("news_auto_poster", "topic_started", details={"topic": topic_name})
            
            print(f"\n{'='*50}")
            print(f"🚀 [{topic_name}] 카테고리 작업 시작...")
            
            info_dict = topic_info[0] if isinstance(topic_info, list) else topic_info
            search_query = info_dict['query']
            
            base_prompt = info_dict.get('prompt', '전문가의 시선으로 차분하게 작성해 주세요.')
            if "게임" in topic_name or "고전" in topic_name:
                base_prompt += " 만약 관련 유튜브 영상이나 에뮬레이터 코드가 있다면 HTML iframe 형태로 본문 하단에 포함해줘."

            if " OR " in search_query:
                keywords = [k.replace('"', '').strip() for k in search_query.split(" OR ")]
                search_query = random.choice(keywords)
                
            # 2. 뉴스 수집 엔진 가동 (중복 체크는 이미 이 안에서 끝납니다)
            n_title, n_content, n_link, n_image_url = fetch_news_by_topic(topic_name, search_query)
            
            # 여기서 못 가져왔다는 건, 새로운 뉴스가 아예 없다는 뜻입니다.
            if not n_title:
                print(f"🛑 [{topic_name}] 관련된 '새로운' 뉴스가 없어 건너뜁니다.")
                continue
                
            print(f"🆕 새 뉴스 발견! 가공을 시작합니다: {n_title}")
            
            # 3. 이미지 처리
            media_id = None
            if n_image_url:
                print("📤 워드프레스에 이미지 업로드 중...")
                media_id = upload_image_to_wp(n_image_url)

            # 4. 제미니(Gemini) AI 재가공
            print(f"🤖 AI 재가공 중 (페르소나: {topic_name})...")
            final_text, g_slug = rewrite_with_gpt(n_title, n_content, base_prompt)

            if not final_text:
                print(f"⚠️ [{topic_name}] GPT 가공 실패. 건너뜁니다.")
                continue
            
            # 5. 마크다운 -> HTML 변환
            print("🔄 HTML 변환 및 워드프레스 전송 준비...")
            html_content = markdown.markdown(final_text, extensions=['extra'])

            target_categories = [info_dict["cat_id"], TOTAL_NEWS_CAT_ID]

            # 6. 워드프레스 발행
            print(f"🔗 생성된 슬러그: {g_slug}")
            print(f"🚀 워드프레스 발행 중... (전송 ID들: {target_categories})")
            
            post_to_wordpress(
                n_title, 
                html_content, 
                target_categories, 
                info_dict["tag_ids"], 
                media_id, 
                n_link,
                slug=g_slug
            )

            # 💡 수정 포인트: 중복되던 트래커 기록 코드를 삭제했습니다. 
            # (post_to_wordpress 함수 내부에서 완벽하게 기록합니다.)

            delay = random.randint(30, 180) 
            print(f"💤 봇 차단 방지를 위해 {delay}초간 휴식 후 다음 카테고리로 이동합니다...")
            time.sleep(delay)

        except Exception as e:
            print(f"❗ [{topic_name}] 실행 중 에러 발생: {e}")
            continue 

    print(f"\n{'='*50}")
    print("🏁 모든 카테고리 포스팅 작업이 종료되었습니다.")