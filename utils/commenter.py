import time
import random
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def robust_get_blog(driver, post_url, wait):
    """
    1. PostRead.naver 주소로 먼저 이동
    2. '페이지 없음' 메시지면, 다시 직링크(post_url)로 이동 시도
    3. 댓글/좋아요 영역 존재 여부 체크
    """
    postread_url = make_postread_url(post_url)
    for test_url in [postread_url, post_url]:
        driver.get(test_url)
        time.sleep(2)
        title = driver.title
        page_source = driver.page_source
        # '페이지를 확인해주세요' 안내 메시지가 있는지 체크
        if "페이지 주소를 확인해주세요" in page_source or "존재하지 않거나 삭제" in page_source:
            print(f"[WARN] {test_url} → 페이지 안내문, fallback!")
            continue
        print(f"[INFO] 정상적으로 페이지 열림: {test_url}")
        return test_url  # 성공한 주소를 반환
    print("[ERROR] 직링크/변환링크 모두 접근 실패")
    return None


def make_postread_url(post_url: str) -> str:
    """댓글/좋아요 가능한 PostRead.naver 주소로 변환."""
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
    """현재 페이지에 존재하는 모든 iframe의 id/name 출력 (디버깅용)."""
    frames = driver.find_elements(By.TAG_NAME, 'iframe')
    print("[DEBUG] 현재 페이지 iframe 리스트:")
    for f in frames:
        print("    id:", f.get_attribute('id'), "| name:", f.get_attribute('name'))

def switch_to_mainFrame_if_exists(driver, wait):
    """mainFrame이 존재하면 진입, 없으면 그냥 진행."""
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
    """
    여러 selector를 순회하면서
    - '좋아요' 버튼이 존재하면,
      - 이미 좋아요면 패스
      - 아니면 클릭
    - 하나라도 성공하면 바로 종료
    """
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
            # 'class' 속성에서 좋아요 상태 체크
            class_attr = btn.get_attribute("class") or ""
            # 네이버는 보통 'off'가 있으면 '아직 좋아요 안 누름'
            if "off" in class_attr:
                btn.click()
                time.sleep(1)
                print(f"[INFO] 좋아요 클릭 성공 → {sel}")
                return True
            else:
                print(f"[INFO] 이미 좋아요 상태(건너뜀) → {sel}")
                return False
        except Exception as e:
            # 해당 selector로 못 찾으면 다음 selector 시도
            continue
    print("[WARN] 좋아요 버튼을 어떤 selector로도 못 찾았어요.")
    return False


def is_duplicate_comment(driver, my_blog_name: str) -> bool:
    """이미 내 블로그 이름이 댓글에 달렸으면 True."""
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
    """
    1. 최신형(naverComment_201_...) 댓글창 → 2. 구형(u_cbox_text) 방식 fallback
    """
    # ─── 1) 최신형 대응 ───
    try:
        time.sleep(2)
        textarea_div = driver.find_element(By.XPATH, f"//div[@id='naverComment_201_{post_num}__write_textarea']")
        textarea_div.click()
        time.sleep(0.5)

        # 실제 textarea가 div 안에 있을 수 있음
        try:
            textarea = textarea_div.find_element(By.TAG_NAME, "textarea")
        except Exception:
            try:
                textarea = textarea_div.find_element(By.TAG_NAME, "input")
            except Exception:
                print("[ERROR] 최신형 textarea/input 못 찾음, 구형 방식 시도")
                raise Exception("신형 실패")  # 아래 구형으로 넘어감

        textarea.send_keys(comment)
        time.sleep(1)

        # 비밀댓글(옵션)
        if private_yn:
            try:
                secret_btn = driver.find_element(By.CSS_SELECTOR, "span.u_cbox_secret_tag")
                secret_btn.click()
                time.sleep(0.5)
            except Exception:
                print("[WARN] 비밀댓글 버튼 없음(신형)")

        # 등록 버튼(신형, class에 post_num 포함)
        submit_btn = driver.find_element(By.XPATH, f"//button[contains(@class, '__uis_naverComment_201_{post_num}_writeButton')]")
        submit_btn.click()
        print("[INFO] (신형) 댓글 등록 성공")
        time.sleep(2)
        return True
    except Exception as e:
        print("[WARN] (신형) 댓글 등록 실패:", e)
        # 구형 방식으로 넘어감

    # ─── 2) 구형 대응 ───
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


def comment_task_on_urls(driver, urls, my_blog_name, comment_text, private_yn=False):
    """블로그 글 리스트에 댓글/좋아요 자동화."""
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

            # 1. mainFrame 진입 (있으면)
            switched = switch_to_mainFrame_if_exists(driver, wait)

            # 2. 좋아요(공감) 클릭
            liked_or_clicked = like_if_needed(driver)
            if not liked_or_clicked:
                print("[SKIP] 좋아요 상태 확인/클릭 실패. 패스 또는 수동확인 필요")
                driver.switch_to.default_content()
                continue

            # 3. 댓글 열기 버튼(id="Comi{post_num}") 클릭 (있으면)
            post_num = url.split("/")[-1]  # 혹은 logNo 추출 로직
            try:
                element = driver.find_element(By.ID, f"Comi{post_num}")
                element.click()
                time.sleep(2)
                print(f"[INFO] 댓글 열기 버튼 클릭: Comi{post_num}")
            except Exception as e:
                print("[WARN] 댓글 열기 버튼 없음 or 클릭 실패:", e)
                # 없어도 진행 (바로 댓글창이 열려 있을 수 있음)

            # 4. 중복 댓글 체크
            if is_duplicate_comment(driver, my_blog_name):
                print(f"[SKIP] 이미 댓글이 존재합니다 → {url}")
                driver.switch_to.default_content()
                continue

            # 5. 댓글 입력 및 등록
            # try:
            #     wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "label.u_cbox_guide"))).click()
            #     textarea = driver.find_element(By.CSS_SELECTOR, "textarea.u_cbox_text")
            #     textarea.send_keys(comment_text)
            #     time.sleep(0.5)
            #     if private_yn:
            #         driver.find_element(By.CSS_SELECTOR, "span.u_cbox_secret_tag").click()
            #         time.sleep(0.5)
            #     driver.find_element(By.CSS_SELECTOR, "button.u_cbox_btn_upload").click()
            #     print(f"[INFO] 댓글 작성 완료 → {url}")
            #     time.sleep(random.uniform(2, 4))
            # except Exception as e:
            #     print("[ERROR] 댓글 작성 중 예외:", e)
            success = write_comment(driver, post_num, comment_text, private_yn)
            if success:
                print(f"[SUCCESS] 댓글 등록 완료 → {url}")
            else:
                print(f"[FAIL] 댓글 등록 실패 → {url}")

            # 6. frame 밖으로 컨텍스트 복귀
            driver.switch_to.default_content()

        except Exception as e:
            print(f"[FATAL] 예외 발생: {e}")
            print("현재 URL:", driver.current_url)
            print("페이지 소스 일부:", driver.page_source[:800])
            continue
