/* dashboardAdapter v1.0 — front-end only, safe fallbacks */
(function () {
  const LOG = '[dashboardAdapter]';
  function j(x){ try { return JSON.stringify(x); } catch { return String(x); } }

  async function get(url, {timeout=3500}={}) {
    const ctl = new AbortController();
    const t = setTimeout(()=>ctl.abort(), timeout);
    try {
      const res = await fetch(url, { signal: ctl.signal, headers: { 'Accept': 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } finally {
      clearTimeout(t);
    }
  }

  // Demo data (used if API missing or fails)
  const demo = {
    season: { week: 1, record: '0-0', health: 'Healthy' },
    champs: { champion: null, stage: 'preseason' },
    leaders: { qb: { name: 'A. Carter', ovr: 74 }, rb: { name: 'M. Stone', ovr: 71 } }
  };

  window.uiAdapters = window.uiAdapters || {};
  window.uiAdapters.dashboard = {
    async getSeasonSummary() {
      try { return await get('/api/season/summary'); } 
      catch (e) { console.warn(`${LOG} season fallback`, e); return demo.season; }
    },
    async getChampionship() {
      try { return await get('/api/championship'); } 
      catch (e) { console.warn(`${LOG} champs fallback`, e); return demo.champs; }
    },
    async getLeaders() {
      try { return await get('/api/leaders'); } 
      catch (e) { console.warn(`${LOG} leaders fallback`, e); return demo.leaders; }
    },
    async simulateWeek() {
      try { 
        const r = await fetch('/api/season/simulate', { method:'POST' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.json();
      } catch (e) {
        console.warn(`${LOG} simulate fallback`, e);
        // Fake a quick advance for demo
        demo.season.week += 1;
        return { ok:true, demo:true, week: demo.season.week };
      }
    },
    async startPlayoffs() {
      try { 
        const r = await fetch('/api/season/playoffs', { method:'POST' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.json();
      } catch (e) { console.warn(`${LOG} playoffs fallback`, e); return { ok:true, demo:true }; }
    },
    async processOffseason() {
      try { 
        const r = await fetch('/api/season/offseason', { method:'POST' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.json();
      } catch (e) { console.warn(`${LOG} offseason fallback`, e); return { ok:true, demo:true }; }
    },
  };
  console.info(`${LOG} ready`);
})();
