import base64
import requests
import markdown
import os
from bs4 import BeautifulSoup
from openai import OpenAI
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from tracker_web import log_app_usage  # 필요시 활성화

# --- [수정 금지] 설정 정보 ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# WP_URL = "http://gohard.pe.kr/wp-json/wp/v2/posts/"
# WP_URL = "http://www.gohard.pe.kr/wp-json/wp/v2/posts/"
# 변경할 필살기 주소 (이 방식은 리다이렉트 없이 바로 꽂힙니다)
WP_URL = "http://gohard.pe.kr/index.php?rest_route=/wp/v2/posts/"
WP_USER = os.getenv("WP_USER")
WP_APP_PASS = os.getenv("WP_APP_PASS")

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_naver_news():
    """네이버 IT/과학 뉴스 헤드라인 하나를 가져옵니다."""
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
    
    return title, content[:1500] # GPT 토큰 절약을 위해 본문은 일부만 사용

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

def post_to_wordpress(title, content):

    # [핵심 2] 출입증(비밀번호)을 서버가 못 뺏어가게 Base64로 튼튼하게 포장
    user_credentials = f"{WP_USER}:{WP_APP_PASS}"
    base64_credentials = base64.b64encode(user_credentials.encode()).decode()

    headers = {
        'Authorization': f'Basic {base64_credentials}',
        'Content-Type': 'application/json'
    }

    """워드프레스에 임시 저장으로 업로드"""
    payload = {
        "title": title,
        "content": content,
        "status": "draft", # 안전을 위해 임시 저장
        "categories": [1]
    }
    
    # [핵심 3] allow_redirects=True로 끝까지 추적해서 꽂아넣기
    res = requests.post(WP_URL, json=payload, headers=headers, allow_redirects=True)

    # res = requests.post(
    #     WP_URL,
    #     auth=HTTPBasicAuth(WP_USER, WP_APP_PASS),
    #     json=payload
    # )
    
    if res.status_code == 201:
        # log_app_usage("naver_bot", "upload_success", {"title": title})
        print(f"✅ 성공: {title} 가 임시저장되었습니다.")
    else:
        print(f"❌ 실패: {res.status_code} - {res.text}")

if __name__ == "__main__":
    try:
        print("🚀 네이버 뉴스 수집 중...")
        n_title, n_content = fetch_naver_news()
        
        print("🤖 GPT 재가공 중 (잡학다식 개발자 버전)...")
        refined_content = rewrite_with_gpt(n_title, n_content)
        
        print("🔄 마크다운을 HTML로 변환 중...")
        # 마크다운을 워드프레스가 인식할 수 있는 HTML로 변환합니다. (표, 리스트 등 확장 기능 포함)
        html_content = markdown.markdown(refined_content, extensions=['extra'])
        
        print("📤 워드프레스 전송 중...")
        # 변환된 html_content를 워드프레스로 보냅니다.
        post_to_wordpress(n_title, html_content)
        
    except Exception as e:
        print(f"❗ 에러 발생: {e}")