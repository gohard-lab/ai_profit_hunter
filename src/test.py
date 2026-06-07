import google.generativeai as genai

# 가지고 계신 키를 여기에 넣어주세요
genai.configure(api_key="AIzaSyDIQV-1U0cDtr2r5SUX70UgxUz9sc3CLk4")

try:
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("안녕? 넌 누구니? 짧게 답해줘.")
    print("✅ 성공! 제미나이 키가 맞습니다. 답변:", response.text)
except Exception as e:
    print("❌ 실패! 다른 서비스용 키이거나 만료되었습니다. 에러:", e)