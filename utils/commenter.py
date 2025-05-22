import time
import random
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from config import SUMMARY_SENT_COUNT

# === 핵심문장 추출: 자체 구현 (Textrankr, Pororo 미사용) ===
from konlpy.tag import Okt
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

def summarize_extract(text, num_sentences=None):
    if not num_sentences:
        num_sentences = SUMMARY_SENT_COUNT
    okt = Okt()
    import re
    # 문장 단위로 분리
    sentences = re.split(r'(?<=[.!?]) +', text)
    # 혹시 2문장 이하일 때 예외처리
    if len(sentences) <= num_sentences:
        return text
    def tokenizer(sent):
        return [w for w, t in okt.pos(sent, norm=True, stem=True)]
    vectorizer = TfidfVectorizer(tokenizer=tokenizer, min_df=1)
    X = vectorizer.fit_transform(sentences)
    scores = np.array(X.sum(axis=1)).ravel()
    topn = np.argsort(scores)[::-1][:num_sentences]
    summary = [sentences[i] for i in sorted(topn)]
    return ' '.join(summary)

def extract_post_text(driver):
    try:
        container = driver.find_element(By.CSS_SELECTOR, "div.se-main-container")
        text = container.text.strip()
        return text
    except Exception as e:
        print("[ERROR] 본문 추출 실패:", e)
        return ""

# ----- 이하 코드는 기존 commenter.py 유지 (정리만) -----

def robust_get_blog(driver, post_url, wait):
    postread_url = make_postread_url(post_url)
    for test_url in [postread_url, post_url]:
        driver.get(test_url)
        time.sleep(2)
        page_source = driver.page_source
        if "페이지 주소를 확인해주세요" in page_source or "존재하지 않거나 삭제" in page_source:
            print(f"[WARN] {test_url} → 페이지 안내문, fallback!")
            continue
        print(f"[INFO] 정상적으로 페이지 열림: {test_url}")
        return test_url
    print("[ERROR] 직링크/변환링크 모두 접근 실패")
    return None

def make_postread_url(post_url: str) -> str:
    parsed = urlparse(post_url)
    if "PostRead.naver" in parsed.path or "logNo=" in parsed.query:
        return post_url
    parts = parsed.path.strip("/").split("/")
    blog_id, post_id = parts[0], parts[-1]
    return (
       f"https://blog.naver.com/PostRead.naver?"
       f"blogId={blog_id}&logNo={post_id}&viewType=pc"
   )

def print_all_frames(driver):
    frames = driver.find_elements(By.TAG_NAME, 'iframe')
    print("[DEBUG] 현재 페이지 iframe 리스트:")
    for f in frames:
        print("    id:", f.get_attribute('id'), "| name:", f.get_attribute('name'))

def switch_to_mainFrame_if_exists(driver, wait):
    print_all_frames(driver)
    try:
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
        print("[INFO] mainFrame 전환 성공")
        return True
    except TimeoutException:
        try:
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.NAME, "mainFrame")))
            print("[INFO] mainFrame(name) 전환 성공")
            return True
        except TimeoutException:
            print("[WARN] mainFrame 없음, 컨텍스트 그대로 진행")
            return False

def like_if_needed(driver):
    selectors = [
        (By.CSS_SELECTOR, "a.u_likeit_list_btn"),
        (By.CSS_SELECTOR, "a.u_likeit_list_btn._button.pcol2"),
        (By.XPATH, "//a[contains(text(),'공감')]"),
        (By.XPATH, "//button[contains(text(),'공감')]"),
    ]
    for by, sel in selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((by, sel))
            )
            class_attr = btn.get_attribute("class") or ""
            if "off" in class_attr:
                btn.click()
                time.sleep(1)
                print(f"[INFO] 좋아요 클릭 성공 → {sel}")
                return True
            else:
                print(f"[INFO] 이미 좋아요 상태(건너뜀) → {sel}")
                return False
        except Exception:
            continue
    print("[WARN] 좋아요 버튼을 어떤 selector로도 못 찾았어요.")
    return False

def is_duplicate_comment(driver, my_blog_name: str) -> bool:
    try:
        pages = driver.find_elements(By.CSS_SELECTOR, "a.u_cbox_page")
        total_pages = len(pages) or 1
        for idx in range(total_pages):
            if idx > 0:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        f"//span[@class='u_cbox_num_page' and text()='{idx+1}']"
                    ))
                ).click()
                time.sleep(1)
            items = driver.find_elements(By.CSS_SELECTOR, "ul.u_cbox_list > li")
            for li in items:
                try:
                    href = li.find_element(
                        By.CSS_SELECTOR,
                        "div.u_cbox_area div.u_cbox_info span.u_cbox_info_main a.u_cbox_name"
                    ).get_attribute("href")
                    if my_blog_name in href:
                        return True
                except Exception:
                    continue
    except Exception as e:
        print("[WARN] 중복댓글 체크 중 예외:", e)
    return False

def write_comment(driver, post_num, comment, private_yn=False):
    try:
        time.sleep(1)
        guide_label = driver.find_element(By.CSS_SELECTOR, "label.u_cbox_guide")
        guide_label.click()
        time.sleep(0.5)
        try:
            textarea = driver.find_element(By.XPATH, f"//div[@id='naverComment_201_{post_num}__write_textarea']//textarea")
        except Exception:
            try:
                textarea = driver.find_element(By.XPATH, f"//div[@id='naverComment_201_{post_num}__write_textarea' and @contenteditable='true']")
            except Exception:
                print("[ERROR] 최신형 textarea/contenteditable 못 찾음, 구형 방식 시도")
                raise Exception("신형 실패")
        textarea.send_keys(comment)
        time.sleep(1)
        if private_yn:
            try:
                secret_btn = driver.find_element(By.CSS_SELECTOR, "span.u_cbox_secret_tag")
                secret_btn.click()
                time.sleep(0.5)
            except Exception:
                print("[WARN] 비밀댓글 버튼 없음(신형)")
        submit_btn = driver.find_element(By.XPATH, f"//button[contains(@class, '__uis_naverComment_201_{post_num}_writeButton')]")
        submit_btn.click()
        print("[INFO] (신형) 댓글 등록 성공")
        time.sleep(2)
        return True
    except Exception as e:
        print("[WARN] (신형) 댓글 등록 실패:", e)
    try:
        wait = WebDriverWait(driver, 10)
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "label.u_cbox_guide"))).click()
        textarea = driver.find_element(By.CSS_SELECTOR, "textarea.u_cbox_text")
        textarea.send_keys(comment)
        time.sleep(0.5)
        if private_yn:
            driver.find_element(By.CSS_SELECTOR, "span.u_cbox_secret_tag").click()
            time.sleep(0.5)
        driver.find_element(By.CSS_SELECTOR, "button.u_cbox_btn_upload").click()
        print("[INFO] (구형) 댓글 등록 성공")
        time.sleep(2)
        return True
    except Exception as e:
        print("[ERROR] (구형) 댓글 등록 실패:", e)
        return False

# ---- 실전 자동화 흐름 (요약 결과로 댓글 등록 부분 로그) ----
def comment_task_on_urls(driver, urls, my_blog_name, comment_text, private_yn=False):
    wait = WebDriverWait(driver, 10)
    for url in urls:
        try:
            opened_url = robust_get_blog(driver, url, wait)
            if not opened_url:
                print(f"[SKIP] {url} - 열리지 않는 주소, 패스")
                continue
            time.sleep(2)
            print("==== 현재 이동한 주소:", driver.current_url)
            print("==== 현재 페이지 타이틀:", driver.title)
            switched = switch_to_mainFrame_if_exists(driver, wait)
            liked_or_clicked = like_if_needed(driver)
            if not liked_or_clicked:
                print("[SKIP] 좋아요 상태 확인/클릭 실패. 패스 또는 수동확인 필요")
                driver.switch_to.default_content()
                # continue

            post_text = extract_post_text(driver)
            if not post_text:
                print("[WARN] 본문이 비어있음. 스킵")
                continue

            # 핵심문장 추출 요약 (Textrankr/Pororo 미사용)
            summary = summarize_extract(post_text)
            print("\n" + "="*40)
            print("🟢 [원본 본문]:")
            print(post_text[:400])   # 너무 길면 400자까지만 예시
            print("\n🟣 [핵심문장 요약 결과]:")
            print(summary)
            print("="*40 + "\n")
            print(f"[임시 로그] 이 글의 댓글 후보: [추출요약] {summary}")

            # ==== 실제 댓글 등록 부분 (아래 한 줄만 주석 해제하면 바로 실전) ====
            # write_comment(driver, post_num=driver.current_url.split('logNo=')[-1], comment=summary, private_yn=private_yn)
            # =============================================================
            driver.switch_to.default_content()
        except Exception as e:
            print(f"[FATAL] 예외 발생: {e}")
            print("현재 URL:", driver.current_url)
            print("페이지 소스 일부:", driver.page_source[:800])
            continue
