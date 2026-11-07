# 正式網站整合更新 — game-intel-new

## 一次更新整個專案

1. 先保留 GitHub 現有版本，必要時可用 Commit history 還原。
2. 解壓縮此 ZIP。將 `game-intel-new-main` **裡面的檔案與資料夾**上傳到 GitHub `game-intel-new` 專案根目錄，覆蓋同名檔案。不要把外層 `game-intel-new-main` 當成新資料夾上傳。
3. Commit changes。
4. GitHub → Actions → `Collect public game headlines` → Run workflow，等待成功。
5. GitHub → Settings → Pages：選擇 `Deploy from a branch`、`main`、`/(root)`；若先前已設定正確則不需變更。
6. 打開 Pages 網址，按 Ctrl+F5 強制重新整理，檢查四大專區與遊戲資訊兩個子頁。

## 目前真實資料的範圍

- 遊戲商店：現有 Steam / Apple 商店資料。支付方式欄位沒有來源時不會顯示；Steam 商店條目不等於遊戲已支援特定支付工具。
- 新聞：RSS 標題與來源，並非完整文章。
- 兌換碼、攻略、活動：`data/codes.json`、`data/guides.json`、`data/events.json` 目前為空。這不是前端故障；來源線索會在各專區以「尚未核實」方式獨立展示。
- `config/verified_sources.json` 的 `feeds` 目前是空陣列。若要自動匯入真實完整資料，須新增可公開讀取的 HTTPS JSON 來源，並遵循 `examples/` 的資料格式；來源主機需列在 `allowed_hosts`。
- 本版不會用新聞標題猜測遊戲上市日、兌換碼、活動起迄或付款方式。

## 檢查

在本機安裝 Python 3.12 後可執行：

```bash
python scripts/validate_data.py
python scripts/validate_site.py
```

## 功能

- 遊戲資訊：最新遊戲情報與上市目錄切換、搜尋、狀態/地區/平台篩選、排序、商店資訊詳情。
- 兌換碼：有正式代碼時按遊戲分組、單筆及全部複製；目前顯示來源線索，不會假造代碼。
- 攻略：完整文章存在時可閱讀、複製分享文案；未匯入時可查找來源線索。
- 活動行事曆：有核實活動時按月份呈現、逐項橫列、同遊戲同色、點擊詳情、CSV 匯出；未核實線索不混入時間軸。
