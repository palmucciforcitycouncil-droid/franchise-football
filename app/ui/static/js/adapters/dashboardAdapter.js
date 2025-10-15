/* dashboardAdapter v1.2 — tries real API, falls back to demo */
(function(){
  const LOG='[dashboardAdapter]';
  async function getJSON(url, ms=4000){
    const ctl=new AbortController(); const to=setTimeout(()=>ctl.abort(),ms);
    try{
      const r=await fetch(url,{signal:ctl.signal,headers:{Accept:'application/json'}});
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.json();
    } finally { clearTimeout(to); }
  }
  const demo = {
    season: { week: 1, record: '0-0', health: 'Healthy' },
    champs: { champion: null, stage: 'preseason' },
    leaders:{ qb:{name:'A. Carter',ovr:74}, rb:{name:'M. Stone',ovr:71} }
  };
  window.uiAdapters = window.uiAdapters || {};
  window.uiAdapters.dashboard = {
    async getSeasonSummary(){ try{ return await getJSON('/api/season/summary'); } catch(e){ console.warn(LOG,'season fallback',e); return demo.season; } },
    async getChampionship(){  try{ return await getJSON('/api/championship'); }    catch(e){ console.warn(LOG,'champs fallback',e);  return demo.champs; } },
    async getLeaders(){       try{ return await getJSON('/api/leaders'); }         catch(e){ console.warn(LOG,'leaders fallback',e); return demo.leaders; } },
    async simulateWeek(){
      try{ const r=await fetch('/api/season/simulate',{method:'POST'}); if(!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
      catch(e){ console.warn(LOG,'simulate fallback',e); demo.season.week+=1; return {ok:true,demo:true,week:demo.season.week}; }
    },
    async startPlayoffs(){    try{ const r=await fetch('/api/season/playoffs',{method:'POST'}); if(!r.ok) throw new Error(); return await r.json(); }
      catch(e){ console.warn(LOG,'playoffs fallback',e); return {ok:true,demo:true}; } },
    async processOffseason(){ try{ const r=await fetch('/api/season/offseason',{method:'POST'}); if(!r.ok) throw new Error(); return await r.json(); }
      catch(e){ console.warn(LOG,'offseason fallback',e); return {ok:true,demo:true}; } },
  };
  console.info(`${LOG} ready`);
})();