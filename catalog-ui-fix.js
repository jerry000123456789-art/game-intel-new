/* Game Intel: show actual store games, never headline leads, in launch catalog. */
(() => {
  'use strict';
  const oldRender = window.renderLaunch;
  const el = id => document.getElementById(id);
  const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeUrl = value => { try { const u = new URL(value); return ['https:','http:'].includes(u.protocol) ? u.href : '#'; } catch { return '#'; } };
  function renderStoreGames() {
    const root = el('launchitems');
    if (!root || typeof launches === 'undefined') return;
    const q = (el('launchquery')?.value || '').trim().toLocaleLowerCase();
    const status = el('launchstatus')?.value || '';
    const region = el('launchregion')?.value || '';
    const groups = new Map();
    for (const item of launches) {
      if (!item || !item.name || !item.verified_store_listing || !(item.store_links || []).length) continue;
      const key = item.name.trim().normalize('NFKC').toLocaleLowerCase();
      if (!groups.has(key)) groups.set(key, { name:item.name.trim(), entries:[], platforms:new Set(), regions:new Set(), links:[], dates:[] });
      const group = groups.get(key);
      group.entries.push(item);
      (item.platforms || []).forEach(x => group.platforms.add(x));
      if (item.region) group.regions.add(item.region);
      for (const link of item.store_links || []) if (link.url && !group.links.some(x => x.url === link.url)) group.links.push(link);
      if (item.release_date) group.dates.push({ date:item.release_date, region:item.region, platform:(item.platforms || []).join('、') });
    }
    const cards = [...groups.values()].filter(g => (!q || g.name.toLocaleLowerCase().includes(q)) && (!region || g.regions.has(region)) && (!status || g.entries.some(x => x.status === status)));
    root.innerHTML = cards.map((g,i) => {
      const image = g.entries.find(x => x.cover_url)?.cover_url;
      const img = image ? `<img src="${safe(safeUrl(image))}" alt="${safe(g.name)} 遊戲封面" loading="lazy" style="width:100%;height:170px;object-fit:contain;background:#f5f7fa;border-radius:12px;margin-bottom:12px" onerror="this.style.display='none'">` : '';
      const statuses = [...new Set(g.entries.map(x => x.status).filter(Boolean))].join('／');
      return `<article class="card">${img}<h3>${safe(g.name)}</h3><p><span class="tag">${safe(statuses)}</span></p><p class="muted small">${safe([...g.platforms].join('、'))} · ${safe([...g.regions].join('、'))}</p>${g.dates.length ? `<p class="small">商店標示日期：${safe([...new Set(g.dates.map(x => `${x.date}（${x.region} ${x.platform}）`))].join('、'))}</p>` : ''}<button data-realgame="${i}">遊戲資料</button></article>`;
    }).join('') || '<div class="empty">目前沒有符合條件的遊戲商店資料。新聞上市消息請到「最新遊戲情報」查看。</div>';
    root.querySelectorAll('[data-realgame]').forEach(b => b.addEventListener('click', () => {
      const g = cards[Number(b.dataset.realgame)];
      const methods = g.entries.flatMap(x => x.payment_methods || []).filter(x => x && x.name && x.source_url);
      const uniqueMethods = [...new Map(methods.map(x => [x.name+'|'+x.source_url,x])).values()];
      const dates = g.dates.length ? `<h3>商店標示日期</h3>${g.dates.map(x => `<p>${safe(x.date)} · ${safe(x.region)} · ${safe(x.platform)}</p>`).join('')}` : '';
      const stores = g.links.map(x => `<p><a href="${safe(safeUrl(x.url))}" target="_blank" rel="noopener noreferrer">${safe(x.name || '遊戲商店')} · ${safe(x.region || '')}</a></p>`).join('');
      const payments = uniqueMethods.length ? `<h3>已確認付款方式</h3>${uniqueMethods.map(x => `<p>${safe(x.name)} · <a href="${safe(safeUrl(x.source_url))}" target="_blank" rel="noopener noreferrer">查證來源</a></p>`).join('')}` : '';
      if (typeof showDetails === 'function') showDetails(`<h2>${safe(g.name)}</h2><p>平台：${safe([...g.platforms].join('、'))}</p><p>地區：${safe([...g.regions].join('、'))}</p>${dates}<h3>商店連結</h3>${stores}${payments}`);
    }));
    const hint = el('launchhint');
    if (hint) hint.textContent = `目前顯示 ${cards.length} 款有商店條目的遊戲；新聞標題不會混入遊戲目錄。`;
  }
  window.renderLaunch = renderStoreGames;
  // Existing page loads its data asynchronously. Render once loaded and whenever filters change.
  ['launchquery','launchstatus','launchregion'].forEach(id => el(id)?.addEventListener('input', renderStoreGames));
  const target = el('launchitems');
  if (target) {
    const observer = new MutationObserver(() => {
      if (typeof launches !== 'undefined' && launches.length) { observer.disconnect(); renderStoreGames(); }
    });
    observer.observe(target, {childList:true});
  }
  document.querySelector('[data-news="launches"]')?.addEventListener('click', renderStoreGames);
  renderStoreGames();
})();
