import requests
from bs4 import BeautifulSoup
import csv  # 1. 匯入 CSV 模組

# 目標 URL
URL = "https://pdc.adm.ncu.edu.tw/"

# --- 3. 設定 CSV 檔案名稱和欄位標頭 ---
CSV_FILENAME = 'ncu_news.csv'
CSV_HEADER = ['日期', '分類', '標題', '連結']

# --- 2. 建立一個空串列，用來收集所有新聞資料 ---
all_news_data = []

print(f"正在嘗試爬取: {URL}")

try:
    response = requests.get(URL, verify=False)
    response.raise_for_status() 
    response.encoding = 'big5'
    
    print("✅ 成功取得網頁內容！")
    print("\n--- 開始爬取最新消息 ---\n")

    soup = BeautifulSoup(response.text, 'html.parser')
    
    marker_cells = soup.find_all('td', width='80')
    
    if not marker_cells:
        print("❌ 找不到任何新聞標記 (td width='80')。")
    else:
        print(f"✅ 成功定位到 {len(marker_cells)} 則新聞項目。\n")
        
        for marker_cell in marker_cells:
            row = marker_cell.find_parent('tr')
            if not row:
                continue
                
            cells = row.find_all('td')
            
            if len(cells) == 3:
                date = cells[0].get_text(strip=True)
                category = cells[1].get_text(strip=True)
                link_tag = cells[2].find('a')
                
                if link_tag:
                    title = link_tag.get_text(strip=True)
                    link = link_tag.get('href')
                    
                    # --- 4. 將資料存入串列中 ---
                    # (我們仍然保留 print 讓您看到過程)
                    print(f"日期: {date}, 分類: {category}, 標題: {title}")
                    
                    # 將抓到的資料整理成一個小串列
                    row_data = [date, category, title, link]
                    
                    # 將這筆資料加入到 "all_news_data" 總串列中
                    all_news_data.append(row_data)

    # --- 5. 在爬蟲迴圈 "結束後"，將資料寫入 CSV 檔案 ---
    # 
    # 檢查我們是否有抓到資料
    if all_news_data:
        print(f"\n--- 爬取完畢，共 {len(all_news_data)} 筆資料 ---")
        
        try:
            # 'w' 代表寫入模式 (write)
            # newline='' 是 csv 模組的標準用法，避免多餘空行
            # encoding='utf-8-sig' 確保 Excel 打開中文不會亂碼
            with open(CSV_FILENAME, 'w', newline='', encoding='utf-8-sig') as file:
                
                # 建立一個 CSV 寫入器
                writer = csv.writer(file)
                
                # 寫入標頭 (第一列)
                writer.writerow(CSV_HEADER)
                
                # 一次性寫入所有收集到的資料 (從第二列開始)
                writer.writerows(all_news_data)
                
            print(f"✅ 成功將資料儲存至 {CSV_FILENAME}")

        except IOError as e:
            print(f"❌ 寫入 CSV 檔案時發生錯誤: {e}")

except requests.RequestException as e:
    print(f"❌ 爬取失敗: {e}")