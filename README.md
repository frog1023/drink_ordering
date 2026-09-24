# QR Code 飲料問答點餐網站（八曜和茶菜單示範）

本專案以使用者提供的菜單圖片作為課堂示範，並非八曜和茶官方網站。顧客掃 QR Code 後依序選系列、飲料、甜度、冰熱與杯數，或向 AI 詢問菜單推薦。顧客確認送出外帶自取訂單，店員查看並更新狀態，顧客頁顯示最近一筆訂單的進度。

## 系統架構

~~~mermaid
flowchart TD
    QR[QR Code] --> C[顧客點餐頁]
    C --> API[FastAPI 後端]
    S[店員管理頁] --> API
    API --> M[menu.json 菜單]
    API --> DB[(SQLite 訂單)]
    API --> AI[OpenAI API]
~~~

| 流程 | 路徑或檔案 | 實際功能 |
| --- | --- | --- |
| QR 入口 | GET /qr | 產生指向顧客網站首頁的 QR 圖 |
| 顧客點餐 | GET /、index.html | 逐題選飲料與客製選項、確認送單 |
| 菜單 | GET /api/menu、menu.json | 提供示範品項與價格 |
| AI 問答 | POST /api/chat | 後端呼叫 OpenAI API；AI 無法代替顧客加購物車或送單 |
| 送出訂單 | POST /api/orders | 驗證品項、甜度及冰熱，後端重新計價並儲存 |
| 顧客查狀態 | GET /api/orders/{id}/status | 使用訂單私密權杖查詢；顧客頁約每 10 秒更新 |
| 店員管理 | GET /admin、GET /api/admin/orders、PATCH /api/admin/orders/{id} | 使用 ADMIN_TOKEN 查看與更新訂單狀態 |
| 儲存 | orders.sqlite3 | 訂單、狀態與品項快照 |

逐題點餐由網頁程式控制，沒有 API 金鑰仍可點餐。AI 僅負責自由提問與推薦；價格和訂單狀態由後端管理。

## 已部署的展示網址

- 顧客網站：https://drink-ordering-krze.onrender.com/
- 店員管理：https://drink-ordering-krze.onrender.com/admin
- QR 圖：https://drink-ordering-krze.onrender.com/qr

QR 圖的目的地是顧客網站首頁。若 Render 網址變更，須同步修改本節網址與 Render 的 PUBLIC_BASE_URL 環境變數，再重新產生 QR 圖。

## 本機執行（Windows／VS Code）

需要 Python 3.10 以上。在專案資料夾的 PowerShell 執行：

~~~powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
~~~

在專案根目錄新增 .env ，內容範例：

~~~env
OPENAI_API_KEY=填入你的API金鑰
OPENAI_MODEL=gpt-4.1-mini
ADMIN_TOKEN=自行設定一組長密碼
PUBLIC_BASE_URL=http://127.0.0.1:8000
~~~

啟動服務：

~~~powershell
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000
~~~

- 本機顧客頁：http://127.0.0.1:8000/
- 店員頁：http://127.0.0.1:8000/admin
- QR 圖：http://127.0.0.1:8000/qr

本機 QR 圖含 127.0.0.1，手機無法藉此連到你的電腦；手機展示應使用上面的公開 QR 圖。

## Render 部署設定

程式由 GitHub 儲存庫部署至 Render Web Service。Root Directory 留空，Build Command 為 pip install -r requirements.txt，Start Command 為 uvicorn app:app --host 0.0.0.0 --port $PORT。在服務的 Environment 頁設定 OPENAI_API_KEY、ADMIN_TOKEN、選用的 OPENAI_MODEL，以及 PUBLIC_BASE_URL=https://drink-ordering-krze.onrender.com。

## 展示與驗收

1. 用手機掃公開 QR Code，選系列、飲料、甜度、冰熱、杯數並確認送單。
2. 記下成功畫面的訂單編號與金額；顧客頁頂部顯示「待店員確認」。
3. 店員開啟 /admin，輸入管理權杖，核對品項與金額，將該筆改為「已接單」。
4. 顧客保留原頁，稍後看到「已接單，準備製作」；店員改為「已完成」後，顧客看到取餐提示。
5. 輸入「推薦 60 元以下的飲料」測試 AI 是否依菜單回答。

## 資料與使用限制

menu.json 依使用者提供的圖片整理，品名及價格僅供課堂示範；正式使用前須由店家核對價格、供應、成分、過敏原和客製限制。AI 的飲食安全回答也需由店員確認。此版沒有金流、庫存或正式會員系統。

Render Free 的本機檔案儲存為暫時性。服務休眠、重啟或重新部署後，SQLite 訂單可能消失；真正營運前須改用持久化資料庫，並補上登入、備份及防濫用機制。顧客狀態頁只記住目前瀏覽器最近一筆新訂單；換裝置或清除網站資料後無法由此版本恢復。舊版本訂單沒有狀態查詢權杖。
