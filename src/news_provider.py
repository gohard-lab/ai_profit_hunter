import requests
import feedparser
import urllib.parse

# 네이버 API 설정 (발급받은 키 입력)
NAVER_CLIENT_ID = "RrIS0dFbO7xQTobADWnv"
NAVER_CLIENT_SECRET = "1FS0eaK1KW"

def fetch_naver_news(query):
    """네이버 API를 통해 뉴스 검색 결과를 가져옵니다."""
    encText = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=sim"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # 네이버는 제목과 요약, 원문 링크를 JSON으로 깔끔하게 줍니다.
        return response.json().get('items', [])
    return []

def fetch_direct_rss(rss_url):
    """개별 언론사의 RSS 피드에서 최신 기사를 가져옵니다."""
    feed = feedparser.parse(rss_url)
    results = []
    for entry in feed.entries:
        results.append({
            'title': entry.title,
            'link': entry.link,
            'description': entry.description if 'description' in entry else ""
        })
    return results[:10]

# 대표님의 맞춤형 RSS 리스트 (관심사 타격용)
RSS_FEEDS = {
    "F1_모터스포츠": [
        "https://www.motorgraph.com/rss/all.xml",  # 모터그래프
        "http://www.autoherald.co.kr/rss/all.xml"  # 오토헤럴드
    ],
    "IT_기술": [
        "https://zdnet.co.kr/rss/all.xml",         # 지디넷코리아
        "https://www.bloter.net/rss/all.xml"      # 블로터
    ]
}

if __name__ == "__main__":
    print("🚀 네이버 API 연동 테스트를 시작합니다...")
    
    # 대표님의 관심사인 파이썬 관련 최신 뉴스를 검색해 봅니다.
    test_keyword = "파이썬"
    results = fetch_naver_news(test_keyword)
    
    if results:
        print(f"✅ 성공! '{test_keyword}' 관련 최신 기사 3개:")
        for i, item in enumerate(results[:3], 1):
            # 네이버는 검색어에 <b> 태그를 붙여서 주므로 깔끔하게 제거합니다.
            clean_title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
            print(f"  {i}. {clean_title} \n     🔗 {item['link']}")
    else:
        print("⚠️ 검색 결과가 없습니다. API 키를 다시 한번 확인해 주세요.")