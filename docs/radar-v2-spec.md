# Game Radar V2 — approved requirements (2026-11-14, Asia/Taipei)

## Product scope
One fast, mobile-first website: **今日商機／新遊戲雷達**, with top-level store views **所有 / Google Play / App Store**. Remove navigation and active UI/workflows for redemption codes, creator guides, event calendar, marketing workspace, ad-copy studio, and non-mobile platforms. Archive previous data, do not erase original history. Poll discovery/verification every **three hours**. Keep no-paid-API baseline with explicit coverage/error diagnostics.

## UI wording and visual ordering (owner's A–L sketch is internal-only)
**Never show the letters A–L or English field identifiers in user-facing text.** They were only the owner's annotations for communicating relative positions.

**Top category tabs MUST use full Traditional Chinese:** `新上市` / `即將上市` / `預約／預先註冊`. A game can occupy one list item even when Android is released in one country and iOS is pre-registered in another. Do not duplicate the game merely to place it under two categories.

The visible sequence of every game card/row:
1. Chinese game name and English game name (both when validated as aliases), game cover.
2. `Android：台灣、國際` or `iOS：台灣` etc. **Show ONLY the platform/country combinations for which an actual store result was found and independently verified**; order `台灣` first, then `國際`. Android and iOS are separate concise lines. No empty slots for absent platforms/markets.
3. **DIRECTLY UNDER the relevant platform/market line** show only documented `上架日期：` or `預約上架時間：` (including per-market date if different). If the preorder/start date was not announced, omit the date instead of inventing one. Platform/country line can mention `預先註冊` when necessary to distinguish current state. Do not conflate `預約開放日` with `預計上架日`.
4. `詳細資訊` opens a drawer/modal with full verified countries (including Japan/Korea), developer, original store links, country/platform observations, precise evidence labels, provenance and history.

**Avoid redundancy:** Do NOT show `已確認可下載`, `可下載`, technical status codes, A–L, or empty/unknown date placeholders in the main list. Availability has already been established through verified platform+region listings; underlying eligibility and detailed provenance belong in the details.

Suggested copy-only illustration, **fictional dates/markets; not real game facts**:

```text
新上市     即將上市     預約／預先註冊

《遊戲甲》 / Game A
Android：台灣、國際
上架日期：台灣 11/11｜國際 11/12
iOS：國際（預先註冊）
預約上架時間：12/05

[詳細資訊]
```

One game per compact row (small icon, dense typography, no oversized cards), for desktop and mobile. For a true iOS-only Taiwan title, show only `iOS：台灣` with its relevant date line; don't render Android or international blanks. Country statuses are independent; never infer another platform's status from one market.

## Compact game list and on-page search (owner refinement, 2026-11-14)
- **Do not use tall per-game cards**. Desktop uses a compact, readable single-row or at most two-line per-game list; mobile uses a similarly short row. Keep cover icons small (about 40–52px), tight spacing, and one `詳細資訊` action. Dates sit immediately underneath their own platform/market line. The detail drawer can be spacious; the overview should show many games without excessive scrolling.
- **Show just one preferred official game name by default**, prioritize Taiwan storefront's real displayed title. Only show an additional Chinese/English title or alias if the differing name materially improves identification/search (e.g. Taiwan and international have different names, translated names diverge, known same-game ambiguity, or user-facing name differs from storefront); avoid routine duplicated bilingual lines.
- **Always-visible search box above the results** with prompt `搜尋遊戲名稱、中文／英文別名或商店 ID`. Search both current and historical records, across `所有 / Google Play / App Store`, not only the currently visible first page. Match names in Traditional and Simplified Chinese, English, normalized spacing/punctuation/case, aliases, Google Play package ID, Apple App ID, and publisher/developer when supplied. Maintain one result per verified game identity, never duplicates due to language/market. Provide an explicit no-results message with scope and a way to reset filters, distinguishing no match from source ingestion failure.
- Search must remain immediate and usable with pagination and the region/store/status filters. No external search navigation for the local stored games. A direct app URL or package/app ID may be parsed as an exact lookup when officially supported; it must never fabricate an entry if the remote lookup fails.
- **Example list copy only** (fictional): `遊戲甲  ·  Android 台灣、國際  / 上架日期：台灣 11/11、國際 11/12  ·  詳細資訊`. Only if the same verified title is known under another materially different name, show small secondary text `其他名稱：Game A`.
- Preserve eye-friendly colors #EAEAEF and #2D3142 and 1.5 line-height despite more compact spacing.

## Identity and naming
Identity by store-specific **Google Play package ID** and **Apple App ID**; never dedupe merely because a name matches, nor split known same-game cross-store records because translations differ. Cross-platform identity can merge only using corroborated developer, canonical website, official cross-link, or manually verified alias mapping. Preserve Chinese/English canonical names and aliases internally for matching and dedup, but display only the preferred verified storefront name by default; show second-language names only when they differ materially or prevent mistaken identity. Support direct search by Google Play package ID or Apple App ID. Preserve one grouped game card with country/platform variants and source links. Keep per-country observation history and re-check conflicting cases.

## Dates: precision and integrity
- Verified official launch date/time (and timezone when published) is different from Google Play app 'Updated on' and Apple's currentVersionReleaseDate.
- Apple product releaseDate is not automatically country-first release date; verify per-country evidence.
- **first_seen_installable_at** or **first_seen_in_country_at** is observational time (when crawler first saw it), not proof of release date.
- For a Google Play app, prioritize Taiwan official first-launch evidence when available. If only an earliest TW-installable observation is available, label it as such in detail, never relabel it as confirmed Taiwan release time.
- Upcoming/pre-registration status can legitimately have no announced launch date: show the preorder badge and omit blank date fields. Do not show “首次發布日期待確認” in normal result cards.
- Version updates and app renames never reset first-ever launch date, and cannot qualify as newly launched games.

## Discovery: high recall, not single homepage
Google Play: TW/US/JP/KR/HK/SG as available, homepage, featured/categories/top/new/pre-registration collections, search pages with rotating game/discovery terms, Google Search/Google News discovery leads, developer/official pages and direct detail by package ID.
App Store: official public **newapplications/newfreeapplications/newpaidapplications** and games-category chart feeds for TW/US/JP/KR/HK/SG, current storefront categories, per-country lookup by Apple app ID, Apple Search queries created from cross-source discovery and known aliases, developer announcements/pre-orders. News headlines and web search results are discovery leads, not proof of launch or app identity. Dedup and verify every official listing before accepting a card. Store source health, number of scanned items, failures, exact source URL, detected-at timestamps, and change history.
These public feeds are **not** a guarantee of 100% global store inventory. Do not imply full exhaustiveness; display the factual scan coverage in status panel.

## Layout
Colors: background #EAEAEF; text #2D3142; deep blue #253F68; deep green #276657; line height 1.5; eye-friendly long sessions. Main header 今日商機｜新遊戲雷達. Tabs 所有 / Google Play / App Store. Visible Chinese tabs 新上市 (recent 30 days only when evidenced), 即將上市, 預約／預先註冊; filters 台灣 / 國際, search all aliases and IDs, sorting newest/earliest, 60-rows pages; don't infinite scroll. Each lightweight row shows validated Chinese/English names, the available Android/iOS Taiwan/international markets and then the relevant 上架日期 or 預約上架時間 immediately beneath the platform/market. No A–L letters, no 已確認可下載 labels, no absent platform placeholders. 詳細資訊 modal contains additional specific countries, source evidence, developer, history and links. Do not display unsupported facts or invented publication times. Provide data-quality/scan-health panel separate from normal results.

## Mandatory regression test set
- UnGodly (Android package com.azragames.ungodly): independent Android and iOS, TW and international status, prereg-to-release transition.
- 三國組合塔防2 / Three Kingdoms Combo Defense 2 (Android package com.looperse.td3kingdom): synonyms search same one game; version update not launch.
- 寰宇卡尊Online (Android package com.jiys.mfqb): independent discovery of a less-popular game outside store home.
- 等級99億 / LV 9.9B (Android package com.curiousdotlab.level99): Chinese/English alias search one game.
Test cases for iOS-only prereg, Android-only TW launch, other-country-only listing, same-game CN/EN localization, different games with same title (must NOT merge), missing release evidence, broken endpoints, 3h and notification snapshot freshness.
A passing test alone does not certify every game is covered. The data quality panel must expose misses/errors.

## Noon daily notification
Recurring **12:00 Asia/Taipei** ChatGPT automation configured separately. Report last successful <=3-hour crawler snapshot before delivery; if stale, show exact stale timestamp and diagnostics rather than claim freshness. Daily 24h diff plus latest known future-release/preorder watch changes. Fixed categories: confirmed newly released, upcoming, new pre-register/pre-order, discrepancies/possible omissions. Each game one entry with CN/EN name, platform/country status TW first, verified official dates where available and official link. Even if zero data, send a status/exception report. Push delivery depends on ChatGPT notification settings/permissions.

## Go-live criteria
1. Build and frontend static checks green, no missing data references.
2. Four sample names and package IDs resolvable and correctly classified.
3. No accidental duplicate across market or language; false merges avoided.
4. Current official store sources tested; failures surfaced with timestamps and retry status.
5. Official site release compared with deployed assets, not just GitHub commit.
6. Don't disable working site or claim successful deployment before these checks pass.
