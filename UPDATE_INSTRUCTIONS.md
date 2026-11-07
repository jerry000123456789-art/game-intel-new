# 正式網站：遊戲商店資料庫更新

## 本次更新
- 新上市／即將上市只顯示真實商店遊戲條目，不再把新聞標題當遊戲。
- 新增 Steam「即將上市」商店條目與 Apple 台灣 App Store 精確名稱查詢。
- 顯示遊戲圖片、遊戲名稱、商店來源、地區、上市狀態；點擊卡片開啟詳細資料。
- 未取得實際付款方式的遊戲不會宣稱支援特定支付工具。
- 原有新聞、兌換碼、攻略、行事曆結構與原本蒐集程式保留。

## 更新 GitHub
建議使用此 ZIP 內的 `index.html`、`scripts/game_catalog.py`、`.github/workflows/collect.yml` 更新同名路徑。不要把 ZIP 外層資料夾當成 GitHub 根目錄上傳。
GitHub Actions > Collect public game headlines > Run workflow。
工作流程會產生 `data/game_catalog.json`。新遊戲卡片由此 JSON 讀取。

## 限制
- Steam 提供即將上市商店條目；Apple Search API 只收錄搜尋種子中精確名稱相符、屬於 Games 類別的實際條目。
- 這不是完整全球商店清單。Google Play、華為及 Epic 的可靠商店目錄收集仍待擴充。
- 此環境無法連線商店 API，因此只能完成本地語法驗證，不能保證商店 API 即時回傳。若商店來源全數失敗，工作流程會報錯而不會發布假資料。
- `App 內購買` 不代表遊戲已確認支援某種特定付款工具，故目前付款方式不自動填寫。
