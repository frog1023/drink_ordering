# 八曜和茶菜單示範：QR Code 問答點餐網站

顧客掃 QR Code，進入網站後以「一問一答」方式選擇 → 選飲料 → 甜度 → 冰熱 → 杯數 → 訂單確認；還能向 AI 詢問推薦。店員從管理頁查看與更新訂單。

## 系統架構

~~~mermaid
flowchart TD
  Q[桌面 QR Code] --> P[顧客對話頁]
  P --> B[FastAPI 後端]
  B --> M[menu.json 菜單]
  B --> O[OpenAI 菜單問答]
  B --> D[(SQLite 訂單)]
  S[店員管理頁] --> B
~~~

| 功能 | 實作 | 說明 |
| --- | --- | --- |
| QR 入口 | GET /qr?table=A1 | 將桌號放進顧客網址 |
| 問答點餐 | index.html | 每一步顯示一個問題及可選答案，不必依賴 AI |
| 自由提問 | POST /api/chat | AI 依菜單回答推薦，無下單權限 |
| 訂單 | POST /api/orders | 檢查飲料 ID、甜度與冰量，依菜單重新計價 |
| 店員 | /admin、/api/admin/orders | 權杖保護；可接單、完成、取消 |
| 儲存 | orders.sqlite3 | 訂單狀態與品項快照 |

## 在電腦執行

需要 Python 3.10 以上。在本資料夾執行：

~~~bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
~~~

複製 .env.example 成 .env，填入 OPENAI_API_KEY（AI 問答）及自行設定長密碼 ADMIN_TOKEN（店員管理）。未填 API key 時，一問一答點餐與送單仍正常，AI 問答會提示設定。啟動：

~~~bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
~~~

瀏覽 http://127.0.0.1:8000/?table=A1；管理頁 http://127.0.0.1:8000/admin；下載或列印 A1 桌 QR 圖 http://127.0.0.1:8000/qr?table=A1。手機掃碼前，須把服務部署至手機可存取的 HTTPS 網址，並將 .env 的 PUBLIC_BASE_URL 改為該網址再產 QR 圖。127.0.0.1 僅供電腦本機展示。不要公開 .env。

## 展示流程

掃QR → 選「厚奶茶」→「覺醒奶茶」→「3分糖」→「完全去冰」→「2 杯」→「確認送單」→ 店員於 /admin 輸入權杖，查看 NT$110 的訂單並改為已接單。也可在下方輸入「推薦不含奶的飲料」體驗 AI 問答。

## 自訂與限制

此版本以提供的八曜和茶圖片整理 56 款示範品項；茶拿鐵與鮮乳茶分為不同品項，價格依圖片錄入。甜度與冰熱按圖片下方標示。圖片上部分配方、供應限制及個別品項選項未能可靠判讀，因此不作精確承諾；正式使用前須逐項核對品名、價格、成分、供應及客製化限制。此示範與品牌無合作或授權關係。

在 menu.json 修改店名、品項及價格，各 id 必須唯一；同步檢查飲料描述、成分和過敏原。AI 可能回答錯誤，過敏或特殊飲食需求應由店員確認。此版為課堂 MVP，沒有金流、庫存、驗證桌號真偽、限流或使用者登入；店員權杖與 SQLite 適合單機展示，正式營運需加上身分驗證、備份和共享資料庫。OpenAI API 使用可能產生費用。

## 訂單狀態更新

新訂單送出後顧客頁頂部會顯示狀態；保持頁面開啟時約每 10 秒更新一次，切回分頁也會重新查詢。店員頁有待確認、已接單、已完成、已取消分類。此功能只適用於更新版本送出的訂單；舊訂單沒有狀態查詢權杖。免費主機休眠或重啟導致 SQLite 訂單消失時，狀態也無法保留。
