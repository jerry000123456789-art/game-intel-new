# 無密碼部署版

這個版本已移除 Worker 的 HTTP Basic Auth 驗證，不再使用 SITE_USERNAME / SITE_PASSWORD。
注意：這代表任何知道網址的人都可能瀏覽網站與公開 JSON 資料，並非私人網站。

Cloudflare 操作：
1. 將此壓縮檔解壓後的內容覆蓋上傳到 GitHub `game-intel-new` 的 main 分支（保留資料夾結構）。
2. Cloudflare Build command: `python3 scripts/build_private.py`
3. Cloudflare Deploy command: `npx wrangler deploy`
4. 等最新 GitHub 自動部署成功並成為正式使用版本。
5. 如果不想要 Cloudflare Access 身分驗證，還需要在 Cloudflare Access 移除/停用此 Worker 的 Access 保護；否則仍會有 Access 登入要求。
6. SITE_USERNAME / SITE_PASSWORD 不再使用，可以在確認新版本正常後刪除。

網站的兌換碼、攻略、活動資料仍取決於 data/*.json 是否有真實內容，不能因部署成功就視為全部功能有資料。
