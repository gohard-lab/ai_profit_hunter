import requests
import json

def generate_blog_post(api_key, title, content):
    """뉴스 본문을 기반으로 고품질 블로그 포스팅을 생성합니다."""
    prompt = f"""
    당신은 IT 및 경제 전문 블로거입니다. 아래 뉴스를 바탕으로 독자에게 통찰력을 주는 블로그 글을 HTML 형식으로 작성하세요.
    
    [뉴스 제목]: {title}
    [뉴스 본문]: {content[:3000]}
    
    [작성 규칙]:
    1. 제목은 독자의 호기심을 자극하는 SEO 최적화 제목으로 변경하세요.
    2. 소제목(<h2>, <h3>)을 사용하여 내용을 논리적으로 구분하세요.
    3. 뉴스에 수치가 있다면 반드시 <table> 태그를 사용하여 표로 정리하세요.
    4. 지적이고 차분한 논조를 유지하며, 마지막엔 '잡학다식 개발자'다운 통찰을 한 문장 더하세요.
    5. 마크다운 기호 없이 순수 HTML 태그만 출력하세요.
    """
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"❌ AI 분석 에러: {e}")
        return None