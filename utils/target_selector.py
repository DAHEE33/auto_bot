# utils/target_selector.py
import time, re
from selenium.webdriver.common.by import By
from urllib.parse import urlparse, parse_qs
from config import BLOG_ID, MAX_NEIGHBOR_TARGETS, NEIGHBOR_PAGING_URL

def get_targets(driver, limit=None):
    if limit is None:
        limit = MAX_NEIGHBOR_TARGETS

    results = []    # [{'uid':…, 'post_url':…}, …]
    page = 1

    # ── 1) limit에 도달할 때까지 페이지를 순회 ──
    while len(results) < limit:
        # a) 페이지 번호(page)를 바꿔가며 URL 생성
        url = NEIGHBOR_PAGING_URL.format(blogId=BLOG_ID, page=page)
        print(f"[DEBUG] 페이지 {page} 로드 → {url}")
        driver.get(url)
        time.sleep(2)

        # b) 각 포스트 카드의 <a class="thumbnail_inner"> 태그를 모두 찾는다
        anchors = driver.find_elements(By.CSS_SELECTOR, "a.thumbnail_inner")
        if not anchors:
            # 더 볼 카드가 없으면 중단
            print("[DEBUG] 더 이상 이웃 새글 없음. 중단.")
            break

        # c) 각 앵커에서 post_url과 uid 추출
        for a in anchors:
            href = a.get_attribute("href") or ""
            # (1) section.blog.naver.com 링크일 때 → query의 blogId 파라
            parsed = urlparse(href)
            qs = parse_qs(parsed.query)
            uid = qs.get("blogId", [None])[0]

            # (2) 또는 blog.naver.com 직링크 형식일 때
            if not uid:
                m = re.match(r"^https?://blog\.naver\.com/([^/]+)/?.*$", href)
                if m:
                    uid = m.group(1)

            # 필터링: UID가 없거나 내 계정(BLOG_ID)이거나 이미 모은 것
            if not uid or uid == BLOG_ID or any(r["uid"] == uid for r in results):
                continue

            # (3) 결과 리스트에 담기
            results.append({ "uid": uid, "post_url": href })
            if len(results) >= limit:
                break

        page += 1

    print(f"[INFO] 총 {len(results)}개 추출 완료")
    return results
