import os

BASE_DIR = os.path.dirname(__file__)
CHROMEDRIVER_PATH = os.path.join(BASE_DIR, "chromedriver.exe")

# 네이버 로그인
NAVER_LOGIN_URL = "https://nid.naver.com/nidlogin.login"
NAVER_ID        = os.getenv("NAVER_ID")
NAVER_PW        = os.getenv("NAVER_PW")

# 블로그 이웃 새글 크롤링
BLOG_ID               = os.getenv("NAVER_ID")  # 내 블로그 ID
MAX_NEIGHBOR_TARGETS  = int(os.getenv("MAX_NEIGHBOR_TARGETS", "100"))
NEIGHBOR_PAGING_URL   = (
    "https://section.blog.naver.com/BlogHome.naver"
    "?directoryNo=0"
    "&groupId=0"
    "&currentPage={page}"
)

# 댓글 내용
COMMENT_TEXT = "좋은 글 잘 보고 갑니다:)"

# config.py 최하단에 추가
# ─────── 요약 결과로 뽑을 문장 수 (Textrankr 등 추출 요약용) ───────
SUMMARY_SENT_COUNT = int(os.getenv("SUMMARY_SENT_COUNT", "5"))  # 기본값 2문장
