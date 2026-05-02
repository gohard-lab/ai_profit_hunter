import requests
import feedparser
import urllib.parse

# 네이버 API 설정 (발급받은 키 입력)
NAVER_CLIENT_ID = "RrIS0dFbO7xQTobADWnv"
NAVER_CLIENT_SECRET = "1FS0eaK1KW"

def fetch_naver_news(query):
    """네이버 API를 통해 뉴스 검색 결과를 가져옵니다."""
    encText = urllib.parse.quote(query)
    # 검색어와 가장 연관성 높은 기사를 가져온다.
    # url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=sim"
    # "최신 날짜"를 우선으로 가져온다.
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=date"
    
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

# 워드프레스 실제 카테고리명과 100% 일치하도록 세팅된 RSS 리스트
RSS_FEEDS = {
    "국내이슈 분석": [
        # 대한민국 정책, 정치, 해외정치, 국제동향
        "https://news.google.com/rss/search?q=정치+OR+해외정치+OR+국제동향+OR+주요정책&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "자동차 & 테크": [
        # 일반 자동차 소식, 모터쇼, 신차
        "https://news.google.com/rss/search?q=자동차+OR+신차+OR+모터쇼+OR+SDV&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "F1 인사이트": [
        # 하드코어 모터스포츠 타격용
        "https://news.google.com/rss/search?q=WEC+OR+F1+OR+포뮬러원+OR+FIA+OR+NASCAR+OR+나스카+OR+르망24&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "글로벌 스포츠": [
        # 해외축구 및 해외 스포츠 중심
        "https://news.google.com/rss/search?q=메이저리그+OR+복싱+OR+UFC+OR+해외스포츠+OR+프리미어리그+OR+EPL+OR+분데스리가+OR+라리가&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "국내 스포츠": [
        # 국내 야구, 축구
        "https://news.google.com/rss/search?q=KBO+OR+프로야구+OR+K리그&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "민생경제": [
        "https://news.google.com/rss/search?q=경제+OR+부동산+OR+주식+OR+지원금&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "IT 뉴스 브리핑": [
        "https://news.hada.io/rss", 
        "https://news.google.com/rss/search?q=IT+OR+테크+OR+소프트웨어&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "종합 뉴스": [
        # 대중적인 주요 헤드라인 (연합뉴스, SBS)
        "https://www.yonhapnewstv.co.kr/category/news/headline/feed/",
        "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01&plink=RSSREADER"
    ],
    "국내 연예": [
        "https://news.google.com/rss/search?q=연예+OR+K팝+OR+국내드라마&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "해외 엔터이슈": [
        "https://news.google.com/rss/search?q=할리우드+OR+넷플릭스+OR+빌보드&hl=ko&gl=KR&ceid=KR:ko"
    ],
    "F1_모터스포츠": [
        "https://www.motorsport.com/rss/f1/news/",  # 모터스포츠닷컴 F1 (차량 기술 및 에어로다이내믹 분석 탁월)
        "https://www.autosport.com/rss/f1/news/",    # 오토스포츠 F1 (오랜 전통과 깊이 있는 취재)
        "https://feeds.bbci.co.uk/sport/formula1/rss.xml" # BBC 스포츠 F1 (공신력 및 정확한 팩트 체크)
    ],
}