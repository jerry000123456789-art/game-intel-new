# Game Radar V2 — approved requirements (2026-11-14, Asia/Taipei)

## Product scope
One fast, mobile-first website: **今日商機／新遊戲雷達**, with top-level store views **所有 / Google Play / App Store**. Remove navigation and active UI/workflows for redemption codes, creator guides, event calendar, marketing workspace, ad-copy studio, and non-mobile platforms. Archive previous data, do not erase original history. Poll discovery/verification every **three hours**. Keep no-paid-API baseline with explicit coverage/error diagnostics.

## A–L UI (owner's handwritten diagram)
A 新上市; B 即將上市; C 預約／預先註冊; D Android 台灣 status; E Android 國際 status; F iOS 台灣 status; G iOS 國際 status; H Android 台灣發佈時間; I Android 國際發佈時間; J iOS 台灣發佈時間; K iOS 國際發佈時間; L 遊戲詳細資訊 via modal/drawer.
One game per row, compact PC table and readable mobile cards. Show only confirmed applicable platform/country cells. If only iOS Taiwan exists, show only that cell. Primary country Taiwan; international summary next; specific US, JP, KR, HK, SG etc in L detail. Platform country states must be independent (installable, preorder/pre-registration, upcoming with official date, unavailable/unobserved). Never globally mark the entire game as released solely from one country/OS.

## Identity and naming
Identity by store-specific **Google Play package ID** and **Apple App ID**; never dedupe merely because a name matches, nor split known same-game cross-store records because translations differ. Cross-platform identity can merge only using corroborated developer, canonical website, official cross-link, or manually verified alias mapping. Preserve both Chinese and English canonical names and search aliases. Support direct search by Google Play package ID or Apple App ID. Preserve one grouped game card with country/platform variants and source links. Keep per-country observation history and re-check conflicting cases.

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
Colors: background #EAEAEF; text #2D3142; deep blue #253F68; deep green #276657; line height 1.5; eye-friendly long sessions. Main header 今日商機｜新遊戲雷達. Tabs 所有 / Google Play / App Store. Sections A 新上市 (recent 30 days only when evidenced), B 即將上市, C 預先註冊/預購; filters 台灣 / 國際, search all aliases and IDs, sorting newest/earliest, 60-rows pages; don't infinite scroll. One lightweight row with icon, CN/EN names, D–G statuses, H–K evidence-based dates. L modal shows every country/platform, last verified, exact source, developer, history, original store links and any conflicts. Do not display unsupported facts or invented publication times. Provide data-quality/scan-health panel separate from normal results.

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
