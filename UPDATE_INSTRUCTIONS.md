# 更新既有 game-intel-new 專案

1. 解壓縮，將全部檔案和資料夾上傳至 GitHub 專案根目錄，覆蓋同名檔案。
2. Commit changes。
3. Actions → Collect public game headlines → Run workflow。
4. 檢查日誌 `Discover public source leads`，應顯示 `source_leads codes=... guides=... events=...`。
5. 在 `data/source_leads.json` 檢視自動整理的來源線索。

注意：線索**不是**可直接複製的兌換碼、完整攻略或已核實的活動。真正的結構化資料仍由 `config/verified_sources.json` 指定的 HTTPS JSON feeds 匯入。未配置來源時，這三個正式資料庫可能仍是空的。

此更新新增可追蹤的來源候選清單及工作流程，沒有宣稱已接通不存在的官方 API。
