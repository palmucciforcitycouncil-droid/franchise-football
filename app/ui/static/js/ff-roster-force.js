/* ff-roster-force.js v1.0 — Force-mount roster shell + immediate fallback table.
   Loads on every page (added in base.html), but only acts on /roster.
   Logs with [ff-roster-force]. Safe to remove once native render is stable. */
(function () {
  const LOG = '[ff-roster-force]';

  function isRosterRoute() {
    const { pathname, hash } = window.location;
    const pOk = pathname && pathname.toLowerCase().endsWith('/roster');
    const hOk = hash && hash.toLowerCase().includes('roster');
    return !!(pOk || hOk);
  }

  function host() {
    return document.querySelector('#app-root') ||
           document.querySelector('main') ||
           document.querySelector('#content') ||
           document.body;
  }

  function mountShell() {
    if (document.getElementById('page-roster')) return true;
    const h = host();
    if (!h) return false;
    const el = document.createElement('section');
    el.id = 'page-roster';
    el.dataset.testid = 'page-roster';
    el.className = 'page roster-page';
    el.innerHTML = `
      <header class="mb-3"><h2 class="text-lg font-semibold">Roster</h2></header>
      <div class="grid grid-cols-12 gap-4">
        <section class="col-span-12">
          <div class="flex items-center gap-2 mb-2">
            <button id="btn-auto-assign" data-action="auto-assign" class="btn">Auto Assign</button>
            <button id="btn-undo-assign" data-action="undo-assign" class="btn btn-secondary">Undo</button>
          </div>
          <section id="roster-main" class="card panel min-h-[360px]" data-roster-root></section>
        </section>
        <section class="col-span-12">
          <h3 class="text-base font-semibold mb-2">Depth Chart</h3>
          <div class="grid grid-cols-12 gap-4">
            <section id="depth-offense"  class="col-span-12 card panel min-h-[220px]" data-depth-offense></section>
            <section id="depth-defense"  class="col-span-12 card panel min-h-[220px]" data-depth-defense></section>
            <section id="depth-special"  class="col-span-12 card panel min-h-[180px]" data-depth-special></section>
          </div>
        </section>
      </div>`;
    h.appendChild(el);
    el.addEventListener('click', (e) => {
      const a = e.target?.dataset?.action;
      if (a === 'auto-assign') window.dispatchEvent(new CustomEvent('ff:depth:autoAssign'));
      if (a === 'undo-assign')  window.dispatchEvent(new CustomEvent('ff:depth:undo'));
    });
    console.info(`${LOG} shell mounted`);
    // Notify native components
    window.dispatchEvent(new Event('ff:roster:rendered'));
    return true;
  }

  async function getRoster() {
    try {
      if (typeof window.uiAdapters?.roster?.getTeamRoster === 'function') {
        return await window.uiAdapters.roster.getTeamRoster();
      }
      if (window.FF?.data?.activeTeamRoster) return window.FF.data.activeTeamRoster;
      if (window.FF?.data?.demo?.roster) return window.FF.data.demo.roster;
    } catch (_) {}
    // Synthetic tiny roster so we never stay blank
    return [
      { id:'qb_1', name:'Alex Carter', pos:'QB', ovr:74 },
      { id:'rb_1', name:'Miles Stone', pos:'RB', ovr:71 },
      { id:'wr_1', name:'Jay Banks',   pos:'WR', ovr:73 },
      { id:'te_1', name:'D. Clark',    pos:'TE', ovr:69 },
      { id:'k_1',  name:'K. Hale',     pos:'K',  ovr:68 },
    ];
  }

  async function renderFallbackTable() {
    const root = document.querySelector('#roster-main[data-roster-root]');
    if (!root) { console.warn(`${LOG} no #roster-main found`); return; }
    if (root.dataset.rendered === 'native' || root.querySelector('table')) {
      console.info(`${LOG} native/table present — skipping fallback`);
      return;
    }
    const roster = await getRoster();
    const rows = (roster || []).map(p => `
      <tr>
        <td class="sticky left-0 bg-base-200 px-2">${p.name || [p.first_name,p.last_name].filter(Boolean).join(' ')}</td>
        <td>${p.pos ?? ''}</td><td>${p.ovr ?? ''}</td>
      </tr>`).join('');
    root.innerHTML = `
      <div class="mb-2 text-sm opacity-70">Roster (Forced Fallback)</div>
      <div class="overflow-auto border border-base-300 rounded">
        <table class="w-full min-w-[520px] text-sm">
          <thead>
            <tr><th class="sticky left-0 bg-base-300 text-left px-2">Name</th><th>Pos</th><th>OVR</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
    console.info(`${LOG} fallback table rendered (${roster?.length||0} players)`);
  }

  function boot() {
    console.info(`${LOG} loaded (path=${location.pathname} hash=${location.hash})`);
    if (!isRosterRoute()) return;
    if (mountShell()) renderFallbackTable();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  // SPA safety: if DOM mutates while we're on /roster, remount once.
  let remounted = false;
  new MutationObserver(() => {
    if (remounted) return;
    if (isRosterRoute() && !document.getElementById('page-roster')) {
      remounted = mountShell();
      if (remounted) renderFallbackTable();
    }
  }).observe(document.body, { childList: true, subtree: true });
})();
