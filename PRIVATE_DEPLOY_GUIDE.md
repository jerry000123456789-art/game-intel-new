# 私人遊戲情報中心：一次部署指南

## 已完成的改動

- 保留既有四個前台專區和資料蒐集腳本。
- 新增 Cloudflare Worker 伺服器端 HTTP Basic 帳號密碼驗證，包含 `/data/*.json`；無憑證返回 401，未設定密碼返回 503。
- GitHub Actions 每 3 小時收集、驗證、建置及部署；驗證失敗不會部署新版本。
- 不會把設定檔、腳本、密碼或 `.github` 發布為靜態資產。

## 你需要在自己的帳號操作（無須把密碼傳給任何人）

1. **先保護原始碼**：GitHub repository → Settings → General → Danger Zone → Change repository visibility → **Private**。注意：公開過的資料可能已被複製或快取，改為 Private 不會抹除過往副本。
2. **關閉舊公開站**：GitHub → Settings → Pages → 停止發布原本的 GitHub Pages；確認舊 `github.io` 網址不再公開。若有自訂網域也要撤除舊指向。
3. **建立 Cloudflare 帳號**：https://dash.cloudflare.com/ 。在 Workers & Pages 建立 Worker，名稱可用 `private-game-intel`；實際部署由 GitHub Actions 完成。
4. **Cloudflare API Token**：Cloudflare → My Profile → API Tokens → Create Token，授予目標帳號 Workers Scripts 編輯所需最小權限。取得 Account ID。
5. **GitHub Actions Secrets**：Repository → Settings → Secrets and variables → Actions，新增 `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`。**不要把它們寫進程式碼或傳給聊天機器人。**
6. **部署前先設定 Worker 的加密秘密**：第一次部署後到 Cloudflare Dashboard → Workers & Pages → `private-game-intel` → Settings → Variables and Secrets，新增兩個 **Secret**：`SITE_USERNAME`（你的登入帳號）、`SITE_PASSWORD`（長且唯一的密碼）。也可透過已登入 Cloudflare CLI 執行 `npx wrangler secret put SITE_USERNAME` 和 `npx wrangler secret put SITE_PASSWORD`。首次設定前 Worker 會返回 503，不會公開資料。
7. **執行一次工作流程**：GitHub → Actions → `Collect and deploy private game intelligence` → Run workflow。日後每 3 小時更新。
8. **開啟 Worker 網址**：通常是 `https://private-game-intel.<你的 workers 子網域>.workers.dev`。瀏覽器會跳出原生帳號密碼視窗；登入後才能查看任何頁面或 JSON。

## 安全注意

- **這是瀏覽器原生 Basic Auth 登入視窗，不是自製漂亮的登入頁。** 全程依賴 HTTPS。瀏覽器可能記住憑證，且不提供完整的單點登出／多帳號管理。
- 建議再於 Cloudflare WAF/Access 增加登入嘗試防護與 MFA。Basic Auth 沒有內建防暴力猜測；密碼應使用密碼管理器產生至少 20 個隨機字元。
- Cloudflare Workers 免費方案有流量、執行及部署配額；超過額度時可能需要調整方案。GitHub 私人儲存庫 Actions 也有免費用量限制。
- 不要在任何其他公開託管位置放相同的 `index.html` 或 `data/*.json`；Cloudflare Worker 的密碼保護不會保護其他副本。
- 資料來源為公開 RSS／商店／已驗證來源；Discord、Facebook 只提供外部連結，不會繞過私人平台權限。
- 現有兌換碼、攻略及活動資料仍可能為 0 筆。這不代表功能測試通過，也不會生成假資料。

## 本機檢查

```bash
python scripts/validate_data.py
python scripts/validate_site.py
python scripts/build_private.py
node --check worker/index.js
```

正式雲端部署與 GitHub Secrets/Cloudflare Secret 設定必須由你的帳號完成；本更新包本身不會自動取得你的帳號權限。
