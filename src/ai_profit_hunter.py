import os
import requests
import time
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from tracker_exe import log_app_usage
from supabase import create_client

# .env 파일 로드 (로컬 테스트용)
load_dotenv()

# 1. 설정 (환경 변수에서 가져오기)
API_CONFIG = {
    "news_api_key": os.getenv("NEWS_API_KEY"),
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    "telegram_token": os.getenv("TELEGRAM_TOKEN"),
    "chat_id": os.getenv("CHAT_ID"),
    "supabase_url": os.getenv("SUPABASE_URL"),
    "supabase_key": os.getenv("SUPABASE_KEY")
}

# DB 연결
supabase = create_client(API_CONFIG["supabase_url"], API_CONFIG["supabase_key"])

def save_profit_data(article_data, ai_result):
    """분석된 데이터를 Supabase에 저장합니다."""
    data = {
        "title": article_data['title'],
        "category": ai_result['category'],
        "report": ai_result['report'],
        "url": article_data.get('url'),
        "source": article_data.get('source', {}).get('name'),
        "created_at": datetime.now().isoformat()
    }
    
    # 중복 방지를 위해 upsert 사용 (title 기준)
    response = supabase.table("profit_results").upsert(data, on_conflict="title").execute()
    
    # 트래커 실행 (상세 정보 JSON 포함)
    log_app_usage("ai_profit_bot", "data_saved", details={
        "category": ai_result['category'],
        "source": data['source']
    })
    return response

def fetch_trending_news(query):
    url = f"https://newsapi.org/v2/everything?q={query}&language=ko&apiKey={API_CONFIG['news_api_key']}"
    response = requests.get(url).json()
    return response.get('articles', [])[:2] # 각 키워드당 상위 2개씩만

def ai_summarize_and_analyze(title):
    openai_api_key = API_CONFIG["openai_api_key"]
    prompt = f"""
    당신은 대한민국 최고의 시사 분석가입니다. 다음 기사 제목을 분석하여 사건의 본질을 꿰뚫는 '카테고리'와 '한글 리포트'를 작성하세요.
    [기사 제목]: {title}
    카테고리: [정치, 경제, 사회, IT/과학, 국제, 사건/사고] 중 택 1
    ###
    리포트: 냉철한 통찰력을 담아 3~5문장으로 작성.
    """
    headers = {"Authorization": f"Bearer {openai_api_key}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
        content = response.json()['choices'][0]['message']['content']
        parts = content.split('###')
        return {
            "category": parts[0].replace('카테고리:', '').strip(),
            "report": parts[1].replace('리포트:', '').strip()
        }
    except:
        return {"category": "기타", "report": "분석 실패"}

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
            # 1. AI 분석
            ai_result = ai_summarize_and_analyze(article['title'])
            
            # 2. DB 저장 (추가됨)
            save_profit_data(article, ai_result)
            
            # 3. 텔레그램 전송
            msg = f"📢 [{ai_result['category']}] {article['title']}\n\n{ai_result['report']}"
            post_to_telegram(msg)
            
            print(f"✅ 저장 및 전송 완료: {article['title'][:15]}...")
            time.sleep(2) # API 과부하 방지

if __name__ == "__main__":
    run_profit_bot()