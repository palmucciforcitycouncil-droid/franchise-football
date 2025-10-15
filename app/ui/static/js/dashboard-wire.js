/* dashboard-wire v2.0 — fills tiles + button wiring */
(function(){
  const LOG='[dashboard-wire]'; console.info(LOG,'boot');

  const T = {
    season: /season status|current season|season/i,
    champs: /championship|playoffs|finals/i,
    leaders:/leaders|top players/i,

    standings:/standings/i,
    schedule:/schedule/i,
    scouting:/scouting/i,
    power:/power rankings?/i,
    box:/box score/i,
    performers:/team top performers|performers|top performers/i,

    btnSim: /sim(ulate)?\s*week/i,
    btnPO:  /start playoffs/i,
    btnOS:  /process offseason/i,
  };

  function findCard(regex){
    const hs=[...document.querySelectorAll('h1,h2,h3,h4,strong,header,div')];
    const h = hs.find(el => regex.test((el.textContent||'').trim()));
    if(!h) return null;
    let n=h; for(let i=0;i<6 && n; i++, n=n.parentElement){
      if(n.classList && /card|panel|box|container|tile|module/i.test(n.className)) return n;
    }
    return h.closest('section,div') || h.parentElement;
  }
  function ensureField(card, key){
    if(!card) return null;
    let slot = card.querySelector(`[data-field="${key}"]`);
    if(!slot){
      slot=document.createElement('div');
      slot.setAttribute('data-field',key);
      slot.style.fontSize='0.95rem';
      slot.style.opacity='0.95';
      slot.style.whiteSpace='pre-wrap';
      (card.querySelector('.card-body, .panel, .content, .body, .inner') || card).appendChild(slot);
    }
    return slot;
  }
  function findButton(regex){
    const btns=[...document.querySelectorAll('button,a,input[type="button"],input[type="submit"]')];
    return btns.find(b => regex.test((b.textContent||b.value||'').trim()));
  }

  async function renderHeader(){
    const api = window.uiAdapters?.dashboard;
    if(!api) return;

    const seasonCard = findCard(T.season);
    const champsCard = findCard(T.champs);
    const leadersCard= findCard(T.leaders);

    const [season, champs, leaders] = await Promise.allSettled([
      api.getSeasonSummary(), api.getChampionship(), api.getLeaders()
    ]);

    const S = (p)=>p.status==='fulfilled'?p.value:null;

    const fWeek   = ensureField(seasonCard,'week');
    const fRecord = ensureField(seasonCard,'record');
    const fHealth = ensureField(seasonCard,'health');
    if(fWeek)   fWeek.textContent   = `Week ${S(season)?.week ?? '?'}`;
    if(fRecord) fRecord.textContent = `Record: ${S(season)?.record ?? '—'}`;
    if(fHealth) fHealth.textContent = `Health: ${S(season)?.health ?? '—'}`;

    const fChamp = ensureField(champsCard,'champion');
    if(fChamp){
      const c=S(champs);
      fChamp.textContent = c?.champion ? `Champion: ${c.champion}` : (c?.stage ? `Stage: ${c.stage}` : 'No champion yet.');
    }

    const fLead = ensureField(leadersCard,'leaders');
    if(fLead){
      const L=S(leaders)||{};
      const qb = L.qb, rb = L.rb;
      fLead.textContent = [
        qb ? `QB: ${qb.name} (OVR ${qb.ovr})` : null,
        rb ? `RB: ${rb.name} (OVR ${rb.ovr})` : null,
      ].filter(Boolean).join('   |   ');
    }
  }

  function fmtTable(rows, cols){
    const th = cols.map(c=>c.h).join(' | ');
    const line = '-'.repeat(th.length);
    const body = rows.map(r => cols.map(c=>String(r[c.k] ?? '')).join(' | ')).join('\n');
    return th + '\n' + line + '\n' + body;
  }

  async function renderTiles(){
    const api = window.uiAdapters?.dashboard;
    if(!api) return;

    // Standings
    const cardStand = findCard(T.standings);
    const fStand = ensureField(cardStand,'stand');
    if(fStand){
      const rows = await api.getStandings();
      fStand.textContent = fmtTable(rows, [
        {h:'Team',k:'team'},{h:'W',k:'w'},{h:'L',k:'l'}
      ]);
    }

    // Schedule
    const cardSched = findCard(T.schedule);
    const fSched = ensureField(cardSched,'sched');
    if(fSched){
      const rows = await api.getSchedule();
      fSched.textContent = fmtTable(rows, [
        {h:'Wk',k:'wk'},{h:'Opp',k:'opp'},{h:'Home',k:'home'},{h:'Time',k:'time'}
      ]);
    }

    // Scouting
    const cardScout = findCard(T.scouting);
    const fScout = ensureField(cardScout,'scout');
    if(fScout){
      const s = await api.getScouting();
      fScout.textContent = s?.note || 'No scouting notes.';
    }

    // Power Rankings
    const cardPower = findCard(T.power);
    const fPower = ensureField(cardPower,'power');
    if(fPower){
      const rows = await api.getPower();
      fPower.textContent = rows.map(r => `${r.rk}. ${r.team}`).join('\n');
    }

    // Box Score
    const cardBox = findCard(T.box);
    const fBox = ensureField(cardBox,'box');
    if(fBox){
      const b = await api.getBox();
      fBox.textContent = `${b.last}: ${b.us}-${b.them}\n${b.qb || ''}`;
    }

    // Top Performers
    const cardPerf = findCard(T.performers);
    const fPerf = ensureField(cardPerf,'perf');
    if(fPerf){
      const rows = await api.getPerformers();
      fPerf.textContent = rows.map(p => `${p.name} (${p.pos}) — ${p.stat}`).join('\n');
    }

    console.info(LOG,'tiles rendered');
  }

  async function renderAll(){
    await renderHeader();
    await renderTiles();
  }

  function wireButtons(){
    const api = window.uiAdapters?.dashboard;
    if(!api) return;

    const bSim = findButton(T.btnSim);
    const bPO  = findButton(T.btnPO);
    const bOS  = findButton(T.btnOS);

    if(bSim && !bSim.dataset.wired){
      bSim.dataset.wired='1';
      bSim.addEventListener('click', async (e)=>{ e.preventDefault(); console.info(LOG,'simulate'); await api.simulateWeek(); renderAll(); });
    }
    if(bPO && !bPO.dataset.wired){
      bPO.dataset.wired='1';
      bPO.addEventListener('click', async (e)=>{ e.preventDefault(); console.info(LOG,'playoffs'); await api.startPlayoffs(); renderAll(); });
    }
    if(bOS && !bOS.dataset.wired){
      bOS.dataset.wired='1';
      bOS.addEventListener('click', async (e)=>{ e.preventDefault(); console.info(LOG,'offseason'); await api.processOffseason(); renderAll(); });
    }
  }

  function badge(){
    if(document.getElementById('dash-wire-badge')) return;
    const b=document.createElement('div');
    b.id='dash-wire-badge';
    b.style.cssText='position:fixed;right:10px;bottom:10px;z-index:2147483647;font:12px ui-monospace,Consolas;color:#cbd5e1;background:#0f172a;border:1px solid #334155;border-radius:8px;padding:5px 8px;opacity:.9';
    b.textContent='Dashboard Wire v2.0';
    document.body.appendChild(b);
  }

  function boot(){
    badge(); renderAll(); wireButtons();
    const mo = new MutationObserver(()=>{ wireButtons(); });
    mo.observe(document.body, { childList:true, subtree:true });
  }

  if(document.readyState==='loading'){ document.addEventListener('DOMContentLoaded', boot); }
  else { boot(); }
})();