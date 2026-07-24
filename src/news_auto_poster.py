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
import feedparser
import google.generativeai as genai
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from newspaper import Article
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from news_provider import fetch_naver_news, fetch_direct_rss, RSS_FEEDS
from tracker_hub import log_app_usage 
from newspaper import Article, Config # Config 추가

# --- [설정 정보] ---
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
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

# client = OpenAI(api_key=OPENAI_API_KEY)

# 종합뉴스 카테고리 ID
TOTAL_NEWS_CAT_ID = 47

# --- [토픽 설정 정보] ---
TOPIC_CONFIG = {
    "F1_모터스포츠": {
        "query": '"FIA" OR "F1" OR "MOTOR RACING" OR "WEC" OR "Formula 1" OR "포뮬러원" OR "모터스포츠" OR "그랑프리"',
        "cat_id": 14,
        "tag_ids": [20],
        "default_media_id": 1082,
        "persona_type": "trend",  # 👈 트렌드 인사이트 분석가
        "prompt": "F1 기술이 양산차와 미래 자동차 산업에 미치는 영향을 차분하고 논리적으로 분석해 줘."
    },
    "올드무비": {
        "query": '"고전 영화" OR "클래식 영화" OR "명작 재개봉" OR "레트로 영화"',
        "cat_id": 15,
        "tag_ids": [22, 23],
        "default_media_id": 1083,
        "persona_type": "storyteller",  # 👈 친절한 스토리텔러
        "prompt": "아날로그 감성이 느껴지는 올드무비의 매력과 감상을 솔직 담백하게 서술해 줘."
    },
    "레트로": {
        "query": '"아하" OR "마이마이" OR "WALKMAN" OR "SONY" OR "PANASONIC" OR "AIWA" OR "아이와 AIWA" OR "파나소닉" OR "레트로" OR "카세트 플레이어" OR "소니 워크맨" OR "카세트 워크맨" OR "빈티지 오디오" OR "LP 플레이어"',
        "cat_id": 17,
        "tag_ids": [36, 37],
        "default_media_id": 1096,
        "persona_type": "storyteller",  # 👈 친절한 스토리텔러
        "prompt": "클래식 카세트 수집가로서 아날로그 기기가 주는 향수와 매력을 객관적으로 설명해 줘."
    },
    "IT트렌드": {
        "query": '"파이썬 개발" OR "소프트웨어 트렌드"',
        "cat_id": 7,
        "tag_ids": [25, 27],
        "default_media_id": 1089,
        "persona_type": "explorer",  # 👈 호기심 지식 탐험가
        "prompt": "어려운 개발 용어 대신 비유를 통해 이 기술 트렌드가 우리 삶에 미칠 영향을 쉽게 설명해 줘."
    },
    "글로벌_스포츠": {
        "query": '"F1" OR "WEC" OR "해외축구" OR "프리미어리그" OR "챔피언스리그" OR "메이저리그" OR "MLB" OR "NBA" OR "테니스" OR "그랜드슬램" OR "프로배구" OR "V리그" OR "UFC"',
        "cat_id": 29,
        "tag_ids": [46, 45, 28, 44],
        "default_media_id": 1091,
        "persona_type": "storyteller",  # 👈 친절한 스토리텔러
        "prompt": "경기의 핵심 포인트와 관전 요소를 흥미진진하게 분석해 줘. 가독성을 위해 불렛포인트를 활용해."
    },
    "해외_엔터이슈": {
        "query": '"할리우드" OR "해외연예" OR "팝스타" OR "빌보드" OR "아카데미 시상식" OR "칸 영화제" OR "넷플릭스 오리지널" OR "해외 가십"',
        "cat_id": 34,
        "tag_ids": [22, 23, 38],
        "default_media_id": 1086,  # 👈 엔터테인먼트 이미지 ID
        "persona_type": "storyteller",
        "prompt": "엔터테인먼트 칼럼니스트로서 현지 분위기와 비하인드 스토리를 위트 있게 서술해 줘."
    },
    "국내_스포츠": {
        "query": '"KBO" OR "프로야구" OR "K리그" OR "국가대표" OR "KBL" OR "한국시리즈"',
        "cat_id": 32,
        "tag_ids": [39, 45, 28],
        "default_media_id": 1091,
        "persona_type": "storyteller",
        "prompt": "경기의 흐름과 선수들의 활약상을 현장감 넘치게 정리해 줘."
    },
    "국내_연예": {
        "query": '"K팝" OR "아이돌" OR "국내 개봉작" OR "드라마 시청률" OR "천만 영화"',
        "cat_id": 35,
        "tag_ids": [22, 23, 42, 40],
        "default_media_id": 1099,
        "persona_type": "storyteller",
        "prompt": "최신 트렌드와 작품의 흥행 요인을 날카롭고 지적으로 분석해서 소개해 줘."
    },
    "국내이슈": {
        "query": '"민생 대책" OR "부동산 규제" OR "세금 혜택" OR "지원금 소식" OR "대통령실 발표"',
        "exclude_keywords": ["속보", "단독", "포토", "영상", "그래픽"],
        "cat_id": 68,
        "tag_ids": [70, 71, 72, 73, 74],
        "default_media_id": 1097,
        "persona_type": "explorer",  # 👈 호기심 지식 탐험가
        "prompt": "이번 소식이 일반 시민들의 지갑이나 생활에 어떤 직접적인 변화를 주는지 지적이고 솔직 담백하게 분석해 줘."
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

def fetch_trending_keywords():
    """대한민국 실시간 인기 급상승 검색어 5개를 가져옵니다."""
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=KR"
    feed = feedparser.parse(url)

    # 제목(Title)에 키워드가 들어있습니다.
    keywords = [entry.title for entry in feed.entries[:5]]

    return keywords

def fetch_news_by_topic(topic_name, search_query):
    # 1. Supabase 트래커 기록
    usage_details = json.dumps({
        "category": topic_name,
        "source": "naver_or_rss"
    }, ensure_ascii=False)
    log_app_usage("news_auto_poster", f"search_{topic_name}", details=usage_details)

    print(f"🚀 [{topic_name}] 주제로 기사 수집 중...")
    
    # 2. 뉴스 수집
    if topic_name == "F1_모터스포츠":  # 💡 F1 전용 RSS 하이패스 추가
        news_items = []
        feed = feedparser.parse("https://www.motorsport.com/rss/f1/news/")
        for entry in feed.entries[:10]:
            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.description if hasattr(entry, 'description') else ""
            })
    elif topic_name in RSS_FEEDS:
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

        if "nytimes.com" in real_url or "economist.com" in real_url:
            print(f"  ⏩ [외신 패스] 차단 가능성이 높은 사이트입니다.")
            continue
        
        # 🚨 추가된 필터링: 단독, 특종, 속보 등 위험/어그로성 기사 배제
        if any(word in title for word in ['단독', '특종', '속보', '프로모션', '할인', '출시', '이벤트']):
            print(f"  ⏩ [위험/광고 패스] 단독 보도 또는 광고성 기사입니다: {title[:30]}...")
            continue

        if is_already_posted(real_url):
            print(f"   ⏩ [중복 패스] 이미 발행된 기사입니다: {title[:30]}...")
            continue 

        # 💡 핵심 수정 포인트: RSS에서 요약본을 가져온 상태라면, 봇 차단을 피하기 위해 크롤링 건너뜀!
        if item.get('summary'):
            print(f"  ✅ RSS 요약본 추출 성공! (봇 차단 우회 완료)")
            return title, item['summary'][:1500], real_url, None
            
        print(f"👉 새 기사 본문 추출 시도 중: {title[:40]}...")
        
        config = Config()
        config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        try:
            article = Article(real_url, config=config, language='ko') 
            article.download()
            article.parse()
            
            content = article.text.strip()[:1500]
            
            # 💡 수정 포인트: 기준을 50자로 낮추고, 실패 시 이유를 명확히 출력합니다.
            if len(content) > 50:
                print(f"   ✅ 추출 성공! (본문 길이: {len(content)}자 / 이미지는 수집 X)")
                return title, content, real_url, None
            else:
                print(f"   ㄴ ⚠️ 내용 부족 패스: 텍스트가 너무 짧습니다({len(content)}자). 포토 기사나 봇 차단 화면일 확률이 높습니다.")
            
        except Exception as e:
            print(f"   ㄴ ⚠️ 추출 에러: {e}")
            
    return None, None, None, None

# 파라미터에 original_link 추가
PERSONA_MAP = {
    "explorer": (
        "당신은 세상의 흥미로운 지식을 쉽게 풀어주는 '호기심 지식 탐험가'입니다. "
        "어려운 전문 용어나 프로그램/코딩 이야기 대신, 일상적인 비유와 흥미진진한 비하인드 스토리 중심으로 독자가 한눈에 이해할 수 있게 작성하세요."
    ),
    "trend": (
        "당신은 미래 트렌드와 산업 변화를 날카롭게 읽어내는 '트렌드 인사이트 분석가'입니다. "
        "단순 사실 전달을 넘어 이 이슈가 앞으로 우리의 일상, 일자리, 산업 생태계에 어떤 영향을 미칠지 명쾌하고 지적인 통찰을 제공하세요."
    ),
    "storyteller": (
        "당신은 최신 이슈와 세상 돌아가는 이야기를 친절하게 전해주는 '친절한 스토리텔러'입니다. "
        "자극적이거나 유치한 표현 없이, 편안하게 대화하듯 차분하고 지적이며 솔직 담백하게 전달하세요."
    )
}

def rewrite_with_gpt(original_title, original_content, original_link, topic_prompt, persona_type="explorer"):
    """주제별 맞춤형 페르소나(explorer, trend, storyteller)로 재작성 및 영어 슬러그 생성"""
    
    # 전달받은 persona_type이 없거나 잘못된 경우 기본값 explorer 설정
    persona_instruction = PERSONA_MAP.get(persona_type, PERSONA_MAP["explorer"])
    
    prompt = f"""
    당신은 다방면에 지식이 깊은 '잡학다식 큐레이터'입니다. 
    단순한 기사 요약(스피닝)은 저작권 침해 위험이 있으므로 절대 금지합니다.
    아래 기사의 '핵심 팩트(사실)'만 추출한 뒤, 지정된 페르소나를 반영하여 완전히 새로운 구조의 오리지널 칼럼을 작성하세요.
    
    [페르소나 지시사항]: 
    {persona_instruction}
    
    [특별 지시사항]: 
    {topic_prompt}
    
    [작성 원칙]
    1. 말투: 차분하고 지적이며 솔직 담백하게 작성하세요. 유치한 말장난이나 과장된 표현은 절대 금지합니다.
    2. 구조: 
       - 서론: 해당 이슈의 핵심 팩트 간략 소개
       - 본론: 핵심 주제에 대한 심층 분석 및 우리 일상/현실에서의 적용점
       - 결론: 솔직한 견해 및 시사점 정리
    3. 포맷: 가독성 높은 마크다운(Markdown) 적용 (적절한 소제목, 불렛포인트 활용)
    4. 출처: 본문 맨 마지막에 아래와 같이 원문 출처를 마크다운 링크로 반드시 남기세요.
       "👉 [원문 기사 보러가기]({original_link})"
    5. SEO: 포스팅에 어울리는 SEO 친화적인 짧은 영어 URL 슬러그 생성 (예: future-of-ai-tech)

    반드시 아래 JSON 형식으로만 응답하세요:
    {{
      "content": "재작성된 마크다운 본문 전체",
      "slug": "생성된-영어-url-슬러그"
    }}
    
    원본 제목: {original_title}
    원본 본문: {original_content}
    """
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name='models/gemini-flash-latest')

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )

        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_text)
                
        return result.get("content", ""), result.get("slug", "")
    
    except Exception as e:
        print(f"❌ Gemini 재가공 중 에러 발생: {e}")
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
    
    # --- 1. 실시간 트렌드 핫이슈 처리 ---
    print("\n🔥 실시간 트렌드 뉴스 수집 시작...")
    try:
        hot_keywords = fetch_trending_keywords()
        for keyword in hot_keywords:
            topic_name = "인기" 
            log_app_usage("news_auto_poster", "trending_topic_started", details={"keyword": keyword, "category": topic_name})
            
            print(f"\n{'='*50}")
            print(f"🚀 실시간 트렌드 [{keyword}] 카테고리 작업 시작...")
            
            # 뉴스 수집 (검색어로 실시간 키워드 투입)
            n_title, n_content, n_link, n_image_url = fetch_news_by_topic(topic_name, keyword)
            
            if not n_title:
                print(f"🛑 [{keyword}] 관련된 '새로운' 뉴스가 없어 건너뜁니다.")
                continue
                
            print(f"🆕 새 뉴스 발견! 가공을 시작합니다: {n_title}")
            
            # 🚨 이미지 처리 부분 통째로 삭제 및 media_id 고정
            media_id = None

            # 실시간 트렌드는 누구나 쉽게 읽도록 'explorer'(호기심 탐험가) 적용
            print(f"🤖 AI 재가공 중 (트렌드 키워드: {keyword})...")
            base_prompt = "최신 이슈를 일반 독자들이 직관적으로 이해할 수 있게 쉽게 분석해서 작성해 주세요."
            final_text, g_slug = rewrite_with_gpt(n_title, n_content, n_link, base_prompt, persona_type="explorer")

            if not final_text:
                print(f"⚠️ [{keyword}] GEMINI 가공 실패. 건너뜁니다.")
                continue
            
            # 마크다운 -> HTML 변환
            print("🔄 HTML 변환 및 워드프레스 전송 준비...")
            html_content = markdown.markdown(final_text, extensions=['extra'])

            # 워드프레스 인기 카테고리 ID(48) 및 종합 뉴스 ID 포함
            target_categories = [48, TOTAL_NEWS_CAT_ID] 

            print(f"🔗 생성된 슬러그: {g_slug}")
            print(f"🚀 워드프레스 발행 중... (전송 ID들: {target_categories})")
            
            post_to_wordpress(
                n_title, 
                html_content, 
                target_categories, 
                [], # 트렌드는 유동적이므로 고정 태그 생략
                media_id, 
                n_link,
                slug=g_slug
            )

            delay = random.randint(30, 180) 
            print(f"💤 봇 차단 방지를 위해 {delay}초간 휴식 후 다음 트렌드로 이동합니다...")
            time.sleep(delay)
            
    except Exception as e:
        print(f"❗ 실시간 트렌드 처리 중 에러 발생: {e}")

    # --- 2. 기존 TOPIC_CONFIG (고정 관심사) 처리 ---
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
                
            n_title, n_content, n_link, n_image_url = fetch_news_by_topic(topic_name, search_query)
            
            if not n_title:
                print(f"🛑 [{topic_name}] 관련된 '새로운' 뉴스가 없어 건너뜁니다.")
                continue
                
            print(f"🆕 새 뉴스 발견! 가공을 시작합니다: {n_title}")
            
            media_id = None
            if n_image_url:
                print("📤 워드프레스에 이미지 업로드 중...")
                media_id = upload_image_to_wp(n_image_url)

            # TOPIC_CONFIG 설정에서 persona_type 및 prompt 추출
            info_dict = topic_info[0] if isinstance(topic_info, list) else topic_info
            base_prompt = info_dict.get('prompt', '전문가의 시선으로 차분하게 작성해 주세요.')
            persona_type = info_dict.get('persona_type', 'explorer')

            print(f"🤖 AI 재가공 중 (카테고리: {topic_name} / 페르소나: {persona_type})...")
            
            # 카테고리 설정값에 맞춰 동적 페르소나 적용
            final_text, g_slug = rewrite_with_gpt(n_title, n_content, n_link, base_prompt, persona_type=persona_type)

            if not final_text:
                print(f"⚠️ [{topic_name}] GEMINI 가공 실패. 건너뜁니다.")
                continue

            print("🔄 HTML 변환 및 워드프레스 전송 준비...")
            html_content = markdown.markdown(final_text, extensions=['extra'])

            target_categories = [info_dict["cat_id"], TOTAL_NEWS_CAT_ID]

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

            delay = random.randint(30, 180) 
            print(f"💤 봇 차단 방지를 위해 {delay}초간 휴식 후 다음 카테고리로 이동합니다...")
            time.sleep(delay)

        except Exception as e:
            print(f"❗ [{topic_name}] 실행 중 에러 발생: {e}")
            continue 

    print(f"\n{'='*50}")
    print("🏁 모든 카테고리 포스팅 작업이 종료되었습니다.")