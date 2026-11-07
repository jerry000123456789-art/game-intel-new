# 全球遊戲情報中心 — 2026-11-07 來源整合／自動更新版

此版本延續既有的 `game-intel-new` Cloudflare Worker，不需要重新建立專案、設定登入或另買爬蟲服務。

## 優先來源（均在系統內整理、搜尋與篩選，不是單純的商店跳轉頁）

1. Google Play 台灣：https://play.google.com/store/games?hl=zh_TW
2. App Store 台灣：https://apps.apple.com/tw/iphone/games
3. Google Play 國際（美國市場）：https://play.google.com/store/games?hl=zh_TW&gl=US
4. Huawei AppGallery：https://appgallery.huawei.com/tab/automore%7Cdoublecolumncardwithstar%7C903189%7CA01000

補充來源：Steam 官方公開商店 API、Google News RSS、官方遊戲公告搜尋、巴哈姆特 GNN RSS 與指定的四個 YouTube 頻道 RSS。

### YouTube 頻道清單

- `UCOCtiyIH-Dt00Ntv-WqPgfw`
- `UCNH35X4JoxqnZHRyWGI04Vg`
- `UC4c-wTOqEID-_vH4MhNs06w`
- `UC-e2q_YhFnfsEggbJsTLPHg`

## 實際行為

- 每 3 小時透過 GitHub Actions 收集一次，收集到的紀錄合併舊資料、不重複收錄。
- 遊戲資訊可按來源、分類、最近 10 天及新舊順序篩選；YouTube/Bahamut RSS 失敗時，提供來源原址連結。
- 商店資料在站內按 **Google Play / App Store / Steam** 及地區篩選。實際商店頁面沒有標示的正式上市日期**不會推測**。「商店收錄」不是「新上市」。
- 公開文章有明確兌換碼字串時，整理成遊戲卡片、可複製代碼，顯示「未實測」及原始網址。
- 公告有明確活動開始、結束日期時，保留日期和原始來源，顯示跨遊戲彩色橫條時間軸。
- 來源收集成功／失敗會在「新上市／即將上市」的「查看自動資料來源狀態」呈現。

## 上傳與首次啟動

1. 解壓 ZIP，將內容覆蓋上傳到原有 GitHub 私人儲存庫 `jerry000123456789-art/game-intel-new` 的 `main` 分支；不是直接上傳 ZIP 本身。
2. GitHub 儲存庫打開 **Actions → Collect and validate public game intelligence → Run workflow**。本流程也已設為每三小時排程。
3. 確認此 workflow 執行成功，產生 `Refresh game intelligence from public sources` 新 commit，再檢查 Cloudflare **Workers & Pages → game-intel-new → Deployments** 最新部署為 `Ready`。
4. 開啟正式網址 `https://game-intel-new.jerry000123456789.workers.dev`，到「新上市／即將上市 → 查看自動資料來源狀態」查看實際結果。

Cloudflare 綁定 `main` 後，GitHub 每次 push 可自動觸發 Workers Builds 部署。**GitHub Actions 完成抓取本身不等於正式網站已發布**；只有 GitHub commit + Cloudflare 部署完成後才會反映在網頁。

原有 Cloudflare 設定應為：Build `python3 scripts/build_private.py`；Deploy `npx wrangler deploy`；Root `/`。本版本 Worker 不要求 SITE_USERNAME/SITE_PASSWORD，但如果 Cloudflare Access 額外開著仍可能出現 Cloudflare 登入。

## 已知限制／排查

- 這個交付環境的外部 DNS 不可用，因此無法在本地直接對四個頻道、巴哈、商店和 Cloudflare 做**線上連線成功測試**。GitHub Actions 是第一次真正跨外網驗收的必要環境；會在 `runtime_status.json` 與 `store_health.json` 留下紀錄。
- Huawei 原始頁面以動態 JS 組裝，公開 HTML 暫無可信的清單提取，系統會如實標示來源失敗，不會隨意把新聞標題當作 AppGallery 商品。
- RSS 是滾動窗口，YouTube 較舊影片需要另找可公開讀取的資料源；但已存的歷史資料不會因新一輪 RSS 變少而消失。
- 官方網站內文、Google News 跳轉與站點反爬蟲可能阻擋自動識別，無法核實的資訊僅提供來源連結。
- 活動的不同遊戲配色只保證**同一月份內不同遊戲不重複顏色**；各遊戲官方時區需以來源為準。

## 本版離線測試

- `python3 scripts/test_channel_pipeline.py`：兩次 10 日內 RSS 模擬收集，歷史保留且去重，通過。
- `python3 scripts/test_live_pipeline.py`：Google Play TW/US、App Store 模擬官方頁面解析；重跑不重複；代碼與活動日期從明確文本抽取，通過。
- `python3 scripts/validate_data.py` / `scripts/validate_site.py` / `scripts/build_private.py`：通過。
- `python3 scripts/test_browser.py`：Chromium 真正執行桌機/手機 UI；資料由本地 JSON 模擬傳送，不是對外網爬蟲測試。通過。

目前隨包附有歷史新聞 87 筆、商店遊戲 18 筆、兌換碼 15 組、攻略 3 篇、活動 18 筆（至少 4 款遊戲）。這些只是種子資料，**不能表示所有遊戲來源已完整覆蓋或 GitHub Actions 線上已通過**。
