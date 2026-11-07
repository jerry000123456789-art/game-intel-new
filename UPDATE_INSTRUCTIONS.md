# 更新現有 game-intel-new 網站（增量版）

1. 解壓縮本 ZIP，保留資料夾結構。將內容上傳至 GitHub `game-intel-new` 根目錄，覆蓋同名檔案，Commit changes。
2. GitHub Actions → Collect public game headlines → Run workflow → main。
3. 檢查 Actions 日誌中的 `Verified feed ingestion complete` 及 `Validation passed`。
4. 重新整理 GitHub Pages 網站，檢查四個分頁。

## 本次新增

- `scripts/ingest_verified.py`：每次 Actions 執行時讀取 `config/verified_sources.json` 的來源清單，擷取結構化 JSON，驗證必要欄位、時間、來源網址及允許的網域，合併到 codes/guides/events 資料檔。失敗不會清空舊資料。
- `config/verified_sources.json`：預設來源清單為空，**不會憑空生出兌換碼、攻略或活動**。要自動匯入，需填入可合法讀取且可信的 HTTPS JSON 資料源（需為已核實資料）。
- 遊戲攻略：無完整文章時，顯示已蒐集的攻略新聞原始來源，避免完全空白，且不冒充完整攻略。

## 來源格式

`config/verified_sources.json` 的 `feeds` 例如：

```json
{"feeds":[{"kind":"codes","url":"https://example.org/codes.json","allowed_hosts":["example.org"]}]}
```

來源內容：`{"items":[{"game":"遊戲名","code":"REALCODE","discovered_at":"2026-11-07T12:00:00+08:00","source_url":"https://example.org/official-post"}]}`。這裡僅示意欄位，**REALCODE 不是真實兌換碼**。

請勿填入無授權的 Discord/Facebook 私密內容，也不要把 Google News 標題直接轉成兌換碼或活動。
