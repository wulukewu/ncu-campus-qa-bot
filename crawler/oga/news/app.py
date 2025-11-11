import time
import csv
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- CSV 相關設定 ---
CSV_FOLDER = 'docs'
CSV_FILENAME = 'news.csv'
CSV_FULL_PATH = os.path.join(CSV_FOLDER, CSV_FILENAME)
CSV_HEADER = ['日期', '標題', '連結']

# --- 網站相關設定 ---
BASE_URL = "https://www.oga.ncu.edu.tw"
PAGE_URL = f"{BASE_URL}/news/5f57f0b6"

# 總資料搜集器
all_news_data = []

def parse_page_content(soup, page_num):
    """
    接收一個 BeautifulSoup 物件，解析其內容，並回傳一個包含該頁資料的 list。
    """
    page_data = []
    print(f"--- 開始解析第 {page_num} 頁 HTML ---")
    
    table_body = soup.find('tbody', class_='news-wrap-table')
    if not table_body:
        print(f"第 {page_num} 頁找不到新聞列表的容器 (tbody.news-wrap-table)。")
        return page_data

    news_items = table_body.find_all('a', class_='news-table-list')
    if not news_items:
        print(f"第 {page_num} 頁在容器中找不到任何新聞 (a.news-table-list)。")
        return page_data

    print(f"第 {page_num} 頁成功定位到 {len(news_items)} 則新聞項目。")

    for item in news_items:
        date_tag = item.find('span', class_='news-list-date')
        date = date_tag.get_text(strip=True) if date_tag else 'N/A'
        
        title_tag = item.find('span', class_='news-list-content')
        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            title = item.get('title', 'N/A').strip()
        
        link = item.get('href')
        if link and not link.startswith('http'):
            link = f"{BASE_URL}{link}"

        page_data.append([date, title, link])
    
    print(f"--- 第 {page_num} 頁解析完畢 ---")
    return page_data

# --- 主要執行腳本 ---
print(f"--- 開始使用 Selenium 爬取 (JS 載入) ---\nURL: {PAGE_URL}\n")

# --- Selenium 設定 ---
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = None

try:
    print("正在啟動瀏覽器驅動...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    print("正在請求網頁...")
    driver.get(PAGE_URL)

    page_num = 1
    
    # --- 開始全自動爬取迴圈 ---
    while True:
        
        print(f"\n--- 正在等待第 {page_num} 頁載入... ---")
        try:
            WebDriverWait(driver, 10).until(
                EC.invisibility_of_element_located((By.CLASS_NAME, "loading-wrap"))
            )
            print(f"第 {page_num} 頁載入完畢！")
            time.sleep(0.5) 
        
        except TimeoutException:
            print(f"等待第 {page_num} 頁載入超時。")
            break

        current_html = driver.page_source
        current_soup = BeautifulSoup(current_html, 'html.parser')
        new_data = parse_page_content(current_soup, page_num)
        
        if not new_data:
            print(f"第 {page_num} 頁沒有解析到任何資料，停止爬取。")
            break
            
        all_news_data.extend(new_data)

        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='下一頁']")
            parent_li = next_button.find_element(By.XPATH, "..")
            
            if "disabled" in parent_li.get_attribute("class"):
                # 如果被禁用，代表這是最後一頁
                print("\n---「下一頁」按鈕已禁用，已達最後一頁。爬取完畢。 ---")
                break 
            else:
                print(f"\n--- 正在點擊「下一頁」，前往第 {page_num + 1} 頁... ---")
                driver.execute_script("arguments[0].click();", next_button)
                page_num += 1

        except NoSuchElementException:
            print("\n--- 找不到「下一頁」按鈕，已是唯一頁面。爬取完畢。 ---")
            break

except Exception as e:
    print(f"\n爬取過程中發生嚴重錯誤: {e}")

finally:
    # 無論成功或失敗，最後都確保瀏覽器被關閉
    if driver:
        driver.quit()
        print("\n--- 瀏覽器已關閉 ---")

# --- 寫入 CSV 檔案 ---
if all_news_data:
    print(f"\n--- 爬取完畢，共 {len(all_news_data)} 筆資料 ---")
    
    try:
        print(f"正在檢查/建立資料夾: {CSV_FOLDER}")
        os.makedirs(CSV_FOLDER, exist_ok=True)

        print(f"正在寫入檔案至: {CSV_FULL_PATH}")
        with open(CSV_FULL_PATH, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADER)
            writer.writerows(all_news_data)
            
        print(f"成功將資料儲存至 {CSV_FULL_PATH}")

    except IOError as e:
        print(f"寫入 CSV 檔案時發生錯誤: {e}")
else:
    print("\n--- 沒有抓取到任何資料，不建立 CSV 檔案。 ---")