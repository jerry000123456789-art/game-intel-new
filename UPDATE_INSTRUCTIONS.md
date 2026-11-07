# 全球遊戲情報中心：正式版整合更新

## 更新方式
1. 解壓縮，將**壓縮檔內的檔案與資料夾**上傳到現有 `game-intel-new` Repository 根目錄，覆蓋同名檔案；不要把外層資料夾一起上傳。
2. GitHub → Actions → **Collect public game headlines** → Run workflow。
3. 確認 `Collect RSS and organize leads`、`Validate curated data`、`Commit updated data` 全部成功。
4. 開啟 GitHub Pages 網站並重新整理。

## 目前可用
- 遊戲情報：RSS 更新、搜尋、分類、排序。
- 新上市／即將上市：獨立子分頁、商店實際條目、圖片、地區、商店連結、搜尋篩選。
- 兌換碼：可讀取經確認的 `data/codes.json`，逐碼複製及一鍵複製全部。沒有確認的代碼不會憑新聞標題製造。
- 攻略：可讀取 `data/guides.json` 的完整原創文章，依遊戲選擇、閱讀、複製分享文案。
- 行事曆：可讀取 `data/events.json` 的真實起迄時間，依遊戲獨立橫列、每遊戲不同顏色、月份切換、點擊詳情、匯出 CSV。

## 如何新增可直接使用的資料
- 編輯 `data/codes.json`、`data/guides.json`、`data/events.json`，依 `examples/` 內對應範本填寫。範本不是已核實資料，**不要把範本直接放進正式 data**。
- 每筆必須附來源 HTTPS 網址。活動時間需含時區，例如 `2026-11-07T10:00:00+08:00`。
- GitHub Actions 執行 `scripts/validate_data.py`，有錯誤會停止，不發布錯誤資料。
- `data/game_catalog.json` 由 `scripts/game_catalog.py` 收集 Steam 與 Apple 商店資料。付款方式欄位不會由「App 內購買」自行推斷。

## 尚未實現的部分（不能誤認已完成）
- Discord/Facebook/YouTube 字幕等來源的自動兌換碼抽取及驗證；需要來源權限與解析器。
- 完整攻略文章自動生成與事實查核；目前須整理後輸入。
- 遊戲官方活動的自動起迄時間驗證；目前須輸入經核實資料。
- Google Play、華為、Epic 全球完整商店掃描及各遊戲支付方式核實。

此更新保留既有收集流程，不聲稱空白資料庫已有真實資料。
