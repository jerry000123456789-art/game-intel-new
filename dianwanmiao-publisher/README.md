# 電玩喵｜獨立發文排程模組

這是獨立的 Cloudflare Worker 程式碼，不會修改 game-intel-new 的正式網站。
儲存為 SQLite-backed Durable Object，支援 Workers 免費方案，不必事先建立 D1。

## 使用前設定
1. Cloudflare Workers & Pages -> Create application -> GitHub，選擇 jerry000123456789-art/game-intel-new。
2. 指定 Root directory: dianwanmiao-publisher；Worker name: dianwanmiao-publisher。
3. **一定要將 production branch 設成 dianwanmiao-publisher-free，不要選 main**。若初始設定無法選分支，先不要部署。
4. Deploy command: npx wrangler deploy；Build command 可留空。
5. 部署後在 Worker Secrets 建立隨機至少 32 字元 ADMIN_API_TOKEN。未設定時管理 API 不會開放。

## 發布限制
X_PUBLISH_ENABLED 預設 false，不會呼叫任何付費 X API。X 付費需使用者事前明確許可。
獲同意後才能在 Cloudflare Secrets 設定 X_API_KEY、X_API_SECRET、X_ACCESS_TOKEN、X_ACCESS_TOKEN_SECRET。
之後使用者仍需明確允許改為 X_PUBLISH_ENABLED=true；本分支不會自行打開。
痞客邦與巴哈姆特只記錄草稿，不聲稱具有官方自動發文權限；Dcard 暫停。

### 安全
不要把 Cloudflare / X API 金鑰放到 GitHub、聊天紀錄或版本控制。管理介面使用暫時記憶的 Bearer Token，不在 localStorage 留存。
目前尚未正式部署或授權；發文與流量仍受平台 API 權限限制。