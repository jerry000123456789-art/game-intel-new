# 全球遊戲情報中心：第三階段

延續第二階段，不需建立新 Repository。`scripts/collect.py` 取得 RSS 標題，`scripts/classify.py` 對標題做保守分類並寫入 `data/classified.json`。網站讀取兩份 JSON。

## 安裝
將 ZIP 解壓縮後的 `index.html`、`README.md`、`scripts/classify.py`、`.github/workflows/collect.yml`、`data/classified.json` 上傳到原本的 `game-intel-new` 對應路徑；其餘檔案無需刪除。**注意** GitHub 上 `.github/workflows/collect.yml` 必須是資料夾路徑，不是含反斜線的檔名。

Actions → Collect public game headlines → Run workflow。檢查 `Collect RSS` 日誌應出現 `classified=...`。工作流程每三小時嘗試更新，實際時間受 GitHub 排程限制。

## 誠實限制
目前只分析 RSS 標題，遊戲名稱為關鍵字比對，標題日期並不等於正式活動或上市日期。**不會**把文章標題當作可兌換代碼、不會推斷付款方式，也不會把日期直接放入正式行事曆。四大原始區塊仍為示範資料。下一步需加入可靠來源的內文擷取、欄位驗證與人工核對。
