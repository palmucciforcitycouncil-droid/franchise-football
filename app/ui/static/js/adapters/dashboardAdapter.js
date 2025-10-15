/* dashboardAdapter v2.0 — real API first, demo fallback */
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
    leaders:{ qb:{name:'A. Carter',ovr:74}, rb:{name:'M. Stone',ovr:71} },
    standings: [
      { team:'Patriots', w:0, l:0 }, { team:'Bills', w:0, l:0 },
      { team:'Jets', w:0, l:0 }, { team:'Dolphins', w:0, l:0 },
    ],
    schedule: [
      { wk:1, opp:'Bills', home:true,  time:'Sun 1:00' },
      { wk:2, opp:'Jets',  home:false, time:'Sun 4:25' },
    ],
    scouting: { note:'Rookie QB class: strong arms, raw accuracy. RB depth solid rounds 3–5.' },
    power: [
      { rk:1, team:'49ers' }, { rk:2, team:'Chiefs' }, { rk:3, team:'Ravens' }, { rk:12, team:'Patriots' }
    ],
    box: { last:'Preseason Wk 1', us:23, them:17, qb:'A. Carter 18/27, 214y, 2 TD' },
    performers: [
      { name:'A. Carter', pos:'QB', stat:'214y, 2 TD' },
      { name:'M. Stone',  pos:'RB', stat:'18 rush, 84y, TD' },
      { name:'J. Banks',  pos:'WR', stat:'6 rec, 71y' },
    ],
  };

  function bumpWeekLocal(){
    demo.season.week += 1;
    // toy updates
    demo.standings[0].w += 1;
    demo.box = { last:`Week ${demo.season.week-1}`, us:27, them:20, qb:'A. Carter 21/31, 238y, 2 TD' };
  }

  window.uiAdapters = window.uiAdapters || {};
  window.uiAdapters.dashboard = {
    // Header/summary
    async getSeasonSummary(){ try{ return await getJSON('/api/season/summary'); } catch(e){ return demo.season; } },
    async getChampionship(){  try{ return await getJSON('/api/championship'); }    catch(e){ return demo.champs; } },
    async getLeaders(){       try{ return await getJSON('/api/leaders'); }         catch(e){ return demo.leaders; } },

    // Tiles
    async getStandings(){     try{ return await getJSON('/api/standings'); }       catch(e){ return demo.standings; } },
    async getSchedule(){      try{ return await getJSON('/api/schedule'); }        catch(e){ return demo.schedule; } },
    async getScouting(){      try{ return await getJSON('/api/scouting'); }        catch(e){ return demo.scouting; } },
    async getPower(){         try{ return await getJSON('/api/power'); }           catch(e){ return demo.power; } },
    async getBox(){           try{ return await getJSON('/api/boxscore/last'); }   catch(e){ return demo.box; } },
    async getPerformers(){    try{ return await getJSON('/api/performers'); }      catch(e){ return demo.performers; } },

    // Actions
    async simulateWeek(){
      try{
        const r=await fetch('/api/season/simulate',{method:'POST'});
        if(!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.json();
      }catch(e){
        bumpWeekLocal();
        return {ok:true, demo:true, week:demo.season.week};
      }
    },
    async startPlayoffs(){    try{ const r=await fetch('/api/season/playoffs',{method:'POST'}); if(!r.ok) throw new Error(); return await r.json(); }
      catch(e){ return {ok:true,demo:true}; } },
    async processOffseason(){ try{ const r=await fetch('/api/season/offseason',{method:'POST'}); if(!r.ok) throw new Error(); return await r.json(); }
      catch(e){ return {ok:true,demo:true}; } },
  };
  console.info(`${LOG} ready v2.0`);
})();