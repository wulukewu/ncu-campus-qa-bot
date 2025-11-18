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
from selenium.common.exceptions import TimeoutException

# --- CSV 相關設定 ---
CSV_FOLDER = 'docs'
CSV_FILENAME = 'qa.csv'
CSV_FULL_PATH = os.path.join(CSV_FOLDER, CSV_FILENAME)
CSV_HEADER = ['分類', '問題', '回答']

# --- 網站相關設定 ---
BASE_URL = "https://www.oga.ncu.edu.tw"
PAGE_URL = f"{BASE_URL}/questions/4c8e117e"

# 總資料搜集器
all_qa_data = []

# --- 輔助函數：解析 Q&A 頁面的 HTML (策略三) ---
def parse_page_content(soup, page_num):
    """
    接收一個 BeautifulSoup 物件，解析其 Q&A 內容，並回傳資料 list。
    """
    page_data = []
    print(f"--- 開始解析第 {page_num} 頁 HTML ---")
    
    main_container = soup.find('div', class_='inside-content-wrap')
    if not main_container:
        print(f"第 {page_num} 頁找不到 Q&A 的主要容器 (div.inside-content-wrap)。")
        return page_data

    category_headers = main_container.find_all('div', class_='second-title')
    
    if not category_headers:
        print(f"第 {page_num} 頁找不到任何分類標題 (div.second-title)。")
        return page_data

    print(f"第 {page_num} 頁成功定位到 {len(category_headers)} 個分類。")
    item_count = 0

    for header in category_headers:
        current_category = header.get_text(strip=True)
        print(f"\n   -> 正在處理分類: {current_category}")
        
        qa_list_container = header.find_next_sibling()
        
        if not qa_list_container or 'mb-5' not in qa_list_container.get('class', []):
            print(f"    -> 警告: 在 '{current_category}' 分類下找不到 'mb-5' 容器。跳過此分類。")
            continue
            
        question_blocks = qa_list_container.find_all('div', class_='mb-0')
        
        if not question_blocks:
            question_blocks = qa_list_container.find_all('div', class_='m-0') # 備案
            if not question_blocks:
                print(f"    -> 警告: 在 '{current_category}' 分類下找不到 'mb-0' 或 'm-0' 問題區塊。")
                continue

        for q_block in question_blocks:
            question = "N/A"
            answer = "N/A"

            q_anchor = q_block.find('a', class_='list-toggle-wrap')
            if q_anchor:
                q_text_tag = q_anchor.find('span')
                question = q_text_tag.get_text(strip=True) if q_text_tag else 'N/A'

            answer_row = q_block.find_next_sibling('div', class_='row')
            if answer_row:
                answer_tag = answer_row.find('div', class_='card-body')
                if answer_tag:
                    answer = answer_tag.get_text(strip=True)

            page_data.append([current_category, question, answer])
            item_count += 1

    print(f"--- 第 {page_num} 頁解析完畢 ---")
    print(f"第 {page_num} 頁總共解析到 {item_count} 個 Q&A 項目。")
    return page_data

# --- 主要執行腳本 (單頁版) ---
print(f"--- 開始使用 Selenium 爬取 (JS 載入) ---\nURL: {PAGE_URL}\n")

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage') 
options.add_argument('--dns-server=8.8.8.8,8.8.4.4')
options.binary_location = "/usr/bin/chromium"
print(f"Chrome options: {options.arguments}")
driver = None

try:
    print("正在啟動瀏覽器驅動...")
    service = Service(executable_path="/usr/bin/chromedriver", service_log_path="/tmp/chromedriver.log")
    driver = webdriver.Chrome(service=service, options=options)

    print("正在請求網頁...")
    driver.get(PAGE_URL)

    print(f"\n--- 正在等待第 1 頁載入... ---")
    try:
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "loading-wrap"))
        )
        print(f"第 1 頁載入完畢！")
        time.sleep(0.5) 
    
    except TimeoutException:
        print(f"等待第 1 頁載入超時。")
        raise 

    current_html = driver.page_source
    current_soup = BeautifulSoup(current_html, 'html.parser')
    all_qa_data = parse_page_content(current_soup, page_num=1)
    
    if not all_qa_data:
        print(f"第 1 頁沒有解析到任何資料。")

    print("\n--- 頁面爬取完畢。 ---")

except Exception as e:
    print(f"\n爬取過程中發生嚴重錯誤: {e}")

finally:
    if driver:
        driver.quit()
        print("\n--- 瀏覽器已關閉 ---")

# --- 寫入 CSV 檔案 ---
if all_qa_data:
    print(f"\n--- 爬取完畢，共 {len(all_qa_data)} 筆資料 ---")
    
    try:
        print(f"正在檢查/建立資料夾: {CSV_FOLDER}")
        os.makedirs(CSV_FOLDER, exist_ok=True)

        print(f"正在寫入檔案至: {CSV_FULL_PATH}")
        with open(CSV_FULL_PATH, 'w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADER)
            writer.writerows(all_qa_data)
            
        print(f"成功將資料儲存至 {CSV_FULL_PATH}")

    except IOError as e:
        print(f"寫入 CSV 檔案時發生錯誤: {e}")
else:
    print("\n--- 沒有抓取到任何資料，不建立 CSV 檔案。 ---")