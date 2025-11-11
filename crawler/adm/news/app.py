import requests
from bs4 import BeautifulSoup
import csv
import os


URL = "https://pdc.adm.ncu.edu.tw/"


CSV_FILENAME = 'docs/news.csv'
CSV_HEADER = ['日期', '分類', '標題', '連結']


all_news_data = []

print(f"正在嘗試爬取: {URL}")

try:
    response = requests.get(URL, verify=False)
    response.raise_for_status() 
    response.encoding = 'big5'
    
    print("成功取得網頁內容！")
    print("\n--- 開始爬取最新消息 ---\n")

    soup = BeautifulSoup(response.text, 'html.parser')
    
    marker_cells = soup.find_all('td', width='80')
    
    if not marker_cells:
        print("找不到任何新聞標記 (td width='80')。")
    else:
        print(f"成功定位到 {len(marker_cells)} 則新聞項目。\n")
        
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
                    

                    print(f"日期: {date}, 分類: {category}, 標題: {title}")
                    
                    row_data = [date, category, title, link]
                    
                    all_news_data.append(row_data)

    if all_news_data:
        print(f"\n--- 爬取完畢，共 {len(all_news_data)} 筆資料 ---")
        
        try:
            os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)
            with open(CSV_FILENAME, 'w', newline='', encoding='utf-8-sig') as file:
                
                writer = csv.writer(file)
                
                writer.writerow(CSV_HEADER)
                
                writer.writerows(all_news_data)
                
            print(f"成功將資料儲存至 {CSV_FILENAME}")

        except IOError as e:
            print(f"寫入 CSV 檔案時發生錯誤: {e}")

except requests.RequestException as e:
    print(f"爬取失敗: {e}")