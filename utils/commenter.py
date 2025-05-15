import time
import random
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def make_postread_url(post_url: str) -> str:
    """
    일반 포스트 URL을 댓글/좋아요가 가능한
    PostRead.naver 형식으로 바꿔서 반환합니다.
    """
    parsed = urlparse(post_url)
    if "PostRead.naver" in parsed.path or "logNo=" in parsed.query:
        return post_url

    parts = parsed.path.strip("/").split("/")
    blog_id, post_id = parts[0], parts[-1]
    return f"https://blog.naver.com/PostRead.naver?blogId={blog_id}&logNo={post_id}"

def click_like(driver):
    """
    공감(좋아요) 버튼을 클릭합니다.
    여러 셀렉터를 시도한 뒤 하나라도 성공하면 리턴합니다.
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
            btn.click()
            time.sleep(1)
            print(f"[INFO] 좋아요 클릭 성공 → {sel}")
            return
        except Exception:
            continue

    print("[WARN] 좋아요 버튼을 못 찾았어요.")

def is_duplicate_comment(driver, my_blog_name: str) -> bool:
    """
    현재 댓글 목록을 스캔해서
    내 블로그 이름(my_blog_name)이 이미 href에 있으면 True 반환.
    """
    pages = driver.find_elements(By.CSS_SELECTOR, "a.u_cbox_page")
    total_pages = len(pages) or 1

    for idx in range(total_pages):
        if idx > 0:
            # 페이지네이션 클릭
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
    return False

def comment_task_on_urls(
    driver,
    urls,
    my_blog_name: str,
    comment_text: str,
    private_yn: bool = False
):
    """
    URL 리스트를 순회하며:
      1) 좋아요 클릭
      2) 중복 댓글 검사
      3) 댓글 작성 (비공개 옵션)
    """
    wait = WebDriverWait(driver, 10)

    for url in urls:
        read_url = make_postread_url(url)
        driver.get(read_url)

        # 1) 좋아요
        click_like(driver)

        # 2) 댓글 플러그인 로드
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        try:
            wait.until(
                EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe#cbox_module"))
            )
            print("[INFO] 댓글 iframe 전환 성공")
        except TimeoutException:
            print("[ERROR] 댓글 iframe 전환 실패")
            driver.switch_to.default_content()
            continue

        # 3) 중복 댓글 검사
        if is_duplicate_comment(driver, my_blog_name):
            print(f"[SKIP] 이미 댓글이 존재합니다 → {url}")
            driver.switch_to.default_content()
            continue

        # 4) 댓글 쓰기
        try:
            # 입력창 활성화
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "label.u_cbox_guide"))
            ).click()
            textarea = driver.find_element(By.CSS_SELECTOR, "textarea.u_cbox_text")
            textarea.send_keys(comment_text)
            time.sleep(0.5)

            # 비밀댓글 옵션
            if private_yn:
                driver.find_element(By.CSS_SELECTOR, "span.u_cbox_secret_tag").click()
                time.sleep(0.5)

            # 등록
            driver.find_element(By.CSS_SELECTOR, "button.u_cbox_btn_upload").click()
            print(f"[INFO] 댓글 작성 완료 → {url}")
            time.sleep(random.uniform(2, 4))

        except Exception as e:
            print("[ERROR] 댓글 작성 중 예외:", e)

        finally:
            driver.switch_to.default_content()
