import requests
import base64

# 카테고리 이름과 ID 매핑 (워드프레스에서 확인한 ID로 수정하세요)
CATEGORY_MAP = {
    "뉴스분석": 1,
    "IT트렌드": 5,
    "경제동향": 10,
    "기타": 1
}

def post_to_wordpress(config, title, html_content, category_name="뉴스분석"):
    """워드프레스에 정해진 카테고리로 글을 발행합니다."""
    url = f"{config['url']}/wp-json/wp/v2/posts"
    category_id = CATEGORY_MAP.get(category_name, 1)
    
    credentials = f"{config['user']}:{config['app_password']}"
    token = base64.b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
    
    payload = {
        "title": title,
        "content": html_content,
        "status": "publish",
        "categories": [category_id]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            return response.json().get('link')
        return None
    except Exception as e:
        print(f"❌ 워드프레스 통신 에러: {e}")
        return None