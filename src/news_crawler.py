from newspaper import Article

def fetch_full_content(url):
    """뉴스 URL에서 본문 텍스트를 깨끗하게 추출합니다."""
    try:
        article = Article(url, language='ko')
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"❌ 본문 추출 에러: {e}")
        return None