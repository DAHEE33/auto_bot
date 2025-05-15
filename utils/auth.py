import time
import pyperclip
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from config import NAVER_ID, NAVER_PW, NAVER_LOGIN_URL

def login(driver, use_clipboard=True):
    """
    네이버 로그인 수행
    use_clipboard=True 면 pyperclip을 이용해 클립보드 방식으로 입력 (자동화 탐지 우회)
    """
    driver.get(NAVER_LOGIN_URL)
    time.sleep(1)
    id_input = driver.find_element(By.ID, "id")
    pw_input = driver.find_element(By.ID, "pw")
    if use_clipboard:
        pyperclip.copy(NAVER_ID)
        id_input.click()
        id_input.send_keys(Keys.CONTROL, 'v')
        time.sleep(0.5)
        pyperclip.copy(NAVER_PW)
        pw_input.click()
        pw_input.send_keys(Keys.CONTROL, 'v')
    else:
        id_input.send_keys(NAVER_ID)
        pw_input.send_keys(NAVER_PW)
    driver.find_element(By.ID, "log.login").click()
    time.sleep(2)