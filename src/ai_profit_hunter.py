import os
import requests
import time
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from tracker_exe import log_app_usage
from supabase import create_client

# 새로 만든 모듈들 (같은 src 폴더 내에 있어야 합니다)
from wp_publisher import post_to_wordpress
from news_crawler import fetch_full_content
from ai_analyzer import generate_blog_post

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

# 1. 설정 (환경 변수에서 가져오기)
API_CONFIG = {
    "news_api_key": os.getenv("NEWS_API_KEY"),
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    "telegram_token": os.getenv("TELEGRAM_TOKEN"),
    "chat_id": os.getenv("CHAT_ID"),
    "supabase_url": os.getenv("SUPABASE_URL"),
    "supabase_key": os.getenv("SUPABASE_KEY"),
    # 🔥 워드프레스 연동을 위한 환경변수 추가
    "wp_url": os.getenv("WP_URL"), 
    "wp_user": os.getenv("WP_USER"), 
    "wp_app_password": os.getenv("WP_APP_PASSWORD")
}

# DB 연결
supabase = create_client(API_CONFIG["supabase_url"], API_CONFIG["supabase_key"])

def save_profit_data(article_data, ai_result):
    # 1. 방어막: AI 분석이 실패했다면 저장하지 않음
    if ai_result is None or not isinstance(ai_result, dict):
        print(f"❌ 분석 결과가 부실하여 DB 저장을 건너뜁니다: {article_data.get('title')}")
        return None
    
    try:
        """분석된 데이터를 Supabase에 저장합니다."""
        # 안전하게 값 가져오기 (.get 활용)
        data = {
            "title": article_data['title'],
            "category": ai_result.get('category', '기타'),
            "report": ai_result.get('report', '리포트 생성 실패'),
            "url": article_data.get('url'),
            "source": article_data.get('source', {}).get('name') if isinstance(article_data.get('source'), dict) else article_data.get('source'),
            "created_at": datetime.now().isoformat()
        }
        
        # 2. Supabase 저장 (중복 방지 upsert)
        response = supabase.table("profit_results").upsert(data, on_conflict="title").execute()
        
        # 3. 데이터 트래커 연동 (요청하신 대로 details를 JSON 타입으로 구성)
        log_app_usage("ai_profit_hunter", "data_saved", details={
            "target_title": data['title'],
            "category": data['category'],
            "source": data['source'],
            "status": "success"
        })
        
        print(f"✅ 사냥 성공 및 DB 저장 완료: {data['title']}")
        return response

    except Exception as e:
        print(f"❌ DB 저장 중 에러 발생: {e}")
        return None

def fetch_trending_news(query):
    url = f"https://newsapi.org/v2/everything?q={query}&language=ko&apiKey={API_CONFIG['news_api_key']}"
    response = requests.get(url).json()
    return response.get('articles', [])[:2] # 각 키워드당 상위 2개씩만

def ai_summarize_and_analyze(title):
    openai_api_key = API_CONFIG["openai_api_key"]
    
    # AI에게 명확한 JSON 형식을 요구하여 파싱 에러를 원천 차단합니다.
    prompt = f"""
    당신은 대한민국 최고의 시사 분석가입니다. 다음 기사 제목을 분석하세요.
    반드시 아래 JSON 형식을 지켜서 답변하세요. 다른 설명은 하지 마세요.
    
    [기사 제목]: {title}
    
    {{
        "category": "정치, 경제, 사회, IT/과학, 국제, 사건/사고 중 택 1",
        "report": "냉철한 통찰력을 담아 3~5문장으로 작성"
    }}
    """
    
    headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini", # 가성비와 속도가 좋은 mini 모델 추천
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        
        # API 응답 상태 확인
        if response.status_code != 200:
            print(f"⚠️ OpenAI API 호출 실패 (Status: {response.status_code})")
            return None
            
        result_json = response.json()
        
        # 'choices' 키가 있는지 안전하게 확인
        if 'choices' not in result_json:
            print(f"⚠️ AI 응답 형식이 올바르지 않습니다: {result_json.get('error', {}).get('message', 'Unknown Error')}")
            return None
            
        content = result_json['choices'][0]['message']['content'].strip()
        
        # JSON 파싱 (문자열에서 JSON 추출)
        # GPT가 가끔 ```json ... ``` 을 붙이는 경우를 대비해 정제
        content = content.replace('```json', '').replace('```', '').strip()
        return json.loads(content)
        
    except Exception as e:
        print(f"❌ AI 분석 중 에러 발생: {e}")
        return None

def post_to_telegram(message):
    url = f"https://api.telegram.org/bot{API_CONFIG['telegram_token']}/sendMessage"
    requests.post(url, data={"chat_id": API_CONFIG["chat_id"], "text": message})

def run_profit_bot():
    log_app_usage("ai_profit_bot", "engine_started")
    hunting_keywords = ["정치", "경제", "사회", "IT 트렌드"]
    
    for target_keyword in hunting_keywords:
        print(f"🎯 타겟 검색: {target_keyword}")
        articles = fetch_trending_news(target_keyword)
        
        for article in articles:
            # 1. AI 요약 분석 (DB 저장 및 기본 보고용)
            ai_result = ai_summarize_and_analyze(article['title'])
            
            if not ai_result:
                print(f"⏩ AI 분석 실패로 건너뜁니다: {article['title']}")
                continue
            
            # 2. DB 저장 (기존 기능 유지)
            save_profit_data(article, ai_result)
            
            # ==========================================
            # 🔥 3. 워드프레스 자동 포스팅 프로세스 시작
            # ==========================================
            wp_link = None
            # 기사 본문 긁어오기
            full_text = fetch_full_content(article['url'])
            
            if full_text:
                # SEO 블로그 포스팅 내용 생성
                blog_html = generate_blog_post(API_CONFIG["openai_api_key"], article['title'], full_text)
                
                if blog_html:
                    # 타겟 키워드에 따라 워드프레스 카테고리 지정
                    category_name = "IT트렌드" if target_keyword in ["IT 트렌드", "IT/과학"] else "경제동향"
                    
                    wp_config = {
                        "url": API_CONFIG["wp_url"],
                        "user": API_CONFIG["wp_user"],
                        "app_password": API_CONFIG["wp_app_password"]
                    }
                    
                    # 워드프레스 서버로 발행 요청
                    wp_link = post_to_wordpress(wp_config, article['title'], blog_html, category_name)
                    
                    if wp_link:
                        # 트래커에 블로그 발행 기록 남기기
                        log_app_usage("ai_profit_hunter", "blog_published", details={
                            "title": article['title'],
                            "category": category_name,
                            "url": wp_link
                        })
            
            # ==========================================
            # 4. 텔레그램 전송 (상황에 맞게 메시지 변경)
            # ==========================================
            if wp_link:
                # 블로그 발행에 성공했을 때
                msg = f"📢 [워드프레스 발행 성공!]\n[{ai_result.get('category', '기타')}] {article['title']}\n\n👉 본문 보기: {wp_link}"
            else:
                # 블로그 발행은 실패했거나 건너뛰었지만 요약은 성공했을 때 (기존 방식)
                msg = f"📢 [{ai_result.get('category', '기타')}] {article['title']}\n\n{ai_result.get('report', '리포트 없음')}"
            
            post_to_telegram(msg)
            
            print(f"✅ 전체 공정 완료: {article['title'][:15]}...")
            time.sleep(3) # API 및 워드프레스 서버 과부하 방지

if __name__ == "__main__":
    run_profit_bot()