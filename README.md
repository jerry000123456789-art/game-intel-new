# 全球遊戲情報中心（無密碼版）

四個可操作分頁：新聞搜尋與商店目錄、兌換碼與來源、攻略原文與文章閱讀器、活動時間軸與 CSV 匯出。

**資料完整度限制**：目前已驗證的 codes/guides/events 結構化資料仍為空；相關公開新聞原文可以直接開啟，但不冒充已核實代碼或完整攻略。要自動填入精確代碼、完整攻略和活動日期，需在 `config/verified_sources.json` 配置有授權的結構化 HTTPS JSON 來源。

Cloudflare Git integration: Build `python3 scripts/build_private.py`；Deploy `npx wrangler deploy`；root `/`。登入功能已移除，若 Access 仍開啟需在 Cloudflare 另外關閉。網站公開可訪問，GitHub Private 不等於網站 Private。

GitHub Actions 每 3 小時執行公開來源收集、驗證與提交；提交會觸發 Cloudflare Git 整合部署。
