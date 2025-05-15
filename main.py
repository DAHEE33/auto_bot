import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from config import CHROMEDRIVER_PATH, BLOG_ID, COMMENT_TEXT
from utils.auth import login
from utils.target_selector import get_targets
from utils.commenter import comment_task_on_urls

# (필요시) 메인에서 추가 딜레이 설정
MIN_DELAY_SEC = 1
MAX_DELAY_SEC = 3

def setup_driver():
    opts = Options()
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("detach", True)

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=opts)
    driver.maximize_window()
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"}
    )
    return driver

def main():
    driver = setup_driver()
    login(driver, use_clipboard=True)

    # 이웃 새글 작성자/URL 추출
    targets = get_targets(driver, limit=1)
    print("🎯 추출된 대상:", targets)

    # URL 리스트만 뽑아서 한 번에 처리
    urls = [t["post_url"] for t in targets]

    # 좋아요 + 댓글 자동화 (비밀댓글 옵션은 기본 False)
    comment_task_on_urls(driver, urls, BLOG_ID, COMMENT_TEXT)

    # (선택) 추가 딜레이
    delay = random.uniform(MIN_DELAY_SEC, MAX_DELAY_SEC)
    print(f"[DELAY] 마무리 대기 {delay:.1f}초…")
    time.sleep(delay)

    print("✅ 전체 작업 완료!")
    driver.quit()

if __name__ == "__main__":
    main()
