# 全球遊戲情報中心 — 第二階段

## 安裝（全新 game-intel-new 專案）

將本 ZIP 解壓縮後，**連同隱藏的 `.github` 資料夾**上傳至新專案根目錄，覆蓋既有 `index.html`、`README.md`。保留資料夾階層：

- `index.html`
- `config/sources.json`
- `scripts/collect.py`
- `data/latest.json`
- `.github/workflows/collect.yml`
- `README.md`

GitHub Pages 仍使用 `main / (root)`。到 **Actions → Collect public game headlines → Run workflow** 手動跑第一次；之後每 3 小時排程（GitHub 可能延遲或停用閒置排程）。若工作流程無法寫回，至 **Settings → Actions → General → Workflow permissions** 開啟 **Read and write permissions**。

## 資料品質與限制

- 只擷取 Google News RSS 公開標題、連結、來源及時間，沒有 AI 自動驗證。
- 所有情報在「最新蒐集情報」獨立區塊，標示為**未驗證線索**；不會把新聞標題當成可用兌換碼、已確認活動或支付方式。
- 四大專區原有內容仍是 DEMO。後續才會加入官方來源驗證、資料結構化、真正的遊戲卡片和攻略。
- GitHub Actions 和 Pages 有免費額度及政策限制；排程不保證準時。
- RSS 抓取失敗時保留舊資料，工作流程回報失敗，避免清空網站。
