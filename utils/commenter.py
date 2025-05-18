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

def click_like(driver):
    """공감(좋아요) 버튼 클릭."""
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
            btn.click()
            time.sleep(1)
            print(f"[INFO] 좋아요 클릭 성공 → {sel}")
            return
        except Exception:
            continue
    print("[WARN] 좋아요 버튼을 못 찾았어요.")

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

            # 2. 댓글 열기 버튼(id="Comi{post_num}") 클릭 (있으면)
            post_num = url.split("/")[-1]  # 혹은 logNo 추출 로직
            try:
                element = driver.find_element(By.ID, f"Comi{post_num}")
                element.click()
                time.sleep(2)
                print(f"[INFO] 댓글 열기 버튼 클릭: Comi{post_num}")
            except Exception as e:
                print("[WARN] 댓글 열기 버튼 없음 or 클릭 실패:", e)
                # 없어도 진행 (바로 댓글창이 열려 있을 수 있음)

            # 3. 중복 댓글 체크
            if is_duplicate_comment(driver, my_blog_name):
                print(f"[SKIP] 이미 댓글이 존재합니다 → {url}")
                driver.switch_to.default_content()
                continue

            # 4. 댓글 입력 및 등록
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "label.u_cbox_guide"))).click()
                textarea = driver.find_element(By.CSS_SELECTOR, "textarea.u_cbox_text")
                textarea.send_keys(comment_text)
                time.sleep(0.5)
                if private_yn:
                    driver.find_element(By.CSS_SELECTOR, "span.u_cbox_secret_tag").click()
                    time.sleep(0.5)
                driver.find_element(By.CSS_SELECTOR, "button.u_cbox_btn_upload").click()
                print(f"[INFO] 댓글 작성 완료 → {url}")
                time.sleep(random.uniform(2, 4))
            except Exception as e:
                print("[ERROR] 댓글 작성 중 예외:", e)

            # 5. 좋아요(공감) 클릭 (선택)
            try:
                click_like(driver)
            except Exception as e:
                print("[WARN] 좋아요 클릭 예외:", e)

            # 6. frame 밖으로 컨텍스트 복귀
            driver.switch_to.default_content()

        except Exception as e:
            print(f"[FATAL] 예외 발생: {e}")
            print("현재 URL:", driver.current_url)
            print("페이지 소스 일부:", driver.page_source[:800])
            continue
