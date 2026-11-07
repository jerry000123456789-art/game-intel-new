# 2026-11-07 交付驗收紀錄

| 測項 | 本地結果 | 限制 |
| --- | --- | --- |
| 10 天內 YouTube + 巴哈 RSS 模擬資料，連抓 2 次、合併、去重 | PASS | 真實來源待 GitHub Actions 驗收 |
| Google Play TW、Google Play US、App Store HTML 解析與紀錄去重 | PASS | 使用可重現測試夾具，未驗證線上抓取成功 |
| Huawei AppGallery | 保留來源及錯誤回報 | 官方頁面 JS 動態資料尚無可核對的抓取方法 |
| 兌換碼文字 → 帶來源的可複製資料（未實測） | PASS | 無法直接驗證遊戲內是否仍有效；依需求不做 |
| 有明確日期的活動文字 → 開始/結束日期 | PASS | 無日期不得猜測；時區依官方標示 |
| 商店平台站內篩選、新聞來源和最近 10 天篩選 | PASS | 真實 Chrome UI，用本地 JSON 回應 |
| 兌換碼彈窗、攻略、四款遊戲活動獨立色彩 | PASS | 真實 Chrome UI，用本地 JSON 回應 |
| 手機 390px 排版與互動 | PASS | 真實 Chrome UI，用本地 JSON 回應 |
| GitHub Actions 遠端抓取、commit | **未驗證** | 需要在你已連結的 GitHub 儲存庫執行 |
| Cloudflare 最新正式部署自動反映 | **未驗證** | 需檢查 GitHub push 後 Cloudflare `Ready` |

本地腳本已加 `verify_live_sources.py`：若 GitHub Actions 當次所有網路來源都未成功，會直接失敗，不把舊資料冒充當次新資料。
