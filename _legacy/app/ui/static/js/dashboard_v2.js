(function(){
  const $ = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  function setTabs(){
    const tabs = $$('#scouting-card .tab');
    tabs.forEach(t=>{
      t.addEventListener('click', ()=>{
        tabs.forEach(x=>x.classList.remove('active'));
        t.classList.add('active');
        const mode = t.dataset.tab;
        $('#scouting-stats').classList.toggle('hidden', mode!=='stats');
        $('#scouting-top').classList.toggle('hidden', mode!=='top');
      });
    });
  }

  function row(cols){ const tr=document.createElement('div'); tr.className='tr'; cols.forEach(c=>{const d=document.createElement('div'); d.innerHTML=c; tr.appendChild(d);}); return tr; }

  async function load(){
    const res = await fetch('/api/dashboard_demo');
    const data = await res.json();

    // Standings
    const sb = $('#standings-body');
    sb.innerHTML = '';
    if(!data.standings.length){
      sb.innerHTML = '<div class="empty">No teams found for AFC East</div>';
    } else {
      const header = row(['Team','W — L','']);
      header.classList.add('th');
      sb.appendChild(header);
      data.standings.forEach((t, i)=>{
        sb.appendChild(row([`${i+1}. ${t.team}`, `${t.w}-${t.l}`, '']));
      });
    }

    // Schedule
    const sched = $('#schedule-body'); sched.innerHTML = '';
    data.schedule.forEach(g=>{
      const wrap = document.createElement('div'); wrap.className='game';
      const wl = g.result === 'W' ? '<span class="badge win">W</span>' : '<span class="badge loss">L</span>';
      wrap.innerHTML = `
        <div class="title">${g.week} ${g.home? 'vs':'at'} ${g.opp} ${wl}</div>
        <div class="meta">${g.line}</div>
      `;
      sched.appendChild(wrap);
    });

    // Schedule scrolling
    const scheduleContainer = $('#schedule-body');
    $('#schedule-scroll-up').addEventListener('click', ()=>{
      scheduleContainer.scrollTop -= 50;
    });
    $('#schedule-scroll-down').addEventListener('click', ()=>{
      scheduleContainer.scrollTop += 50;
    });

    // Scouting (Stats)
    const sstats = $('#scouting-stats .table');
    sstats.innerHTML = '<div class="tr th"><div>Rank ↑</div><div>Stat</div><div>Value</div></div>';
    data.scouting.stats.forEach(r=>{
      sstats.appendChild(row([r.rank, r.stat, r.value]));
    });

    // Scouting (Top)
    const stop = $('#scouting-top .table');
    stop.innerHTML = '<div class="tr th"><div>#</div><div>Player</div><div>Value</div></div>';
    data.scouting.top.forEach((r,idx)=>{
      stop.appendChild(row([idx+1, `${r.name} <span class="muted">${r.pos}</span>`, r.value]));
    });

    // Power Rankings (carousel)
    const pb = $('#power-body'); pb.innerHTML = '';
    data.power.forEach((rowObj, i)=>{
      const r = document.createElement('div'); r.className='tr';
      r.innerHTML = `<div>${i+1}</div><div>${rowObj.team}</div><div>${rowObj.score}</div>`;
      pb.appendChild(r);
    });

    // Power Rankings carousel functionality
    let powerCurrentPage = 0;
    const powerPerPage = 5;
    const totalPowerPages = Math.ceil(data.power.length / powerPerPage);
    
    function showPowerPage(page) {
      const pb = $('#power-body');
      pb.innerHTML = '';
      const start = page * powerPerPage;
      const end = Math.min(start + powerPerPage, data.power.length);
      for (let i = start; i < end; i++) {
        const rowObj = data.power[i];
        const r = document.createElement('div'); r.className='tr';
        r.innerHTML = `<div>${i+1}</div><div>${rowObj.team}</div><div>${rowObj.score}</div>`;
        pb.appendChild(r);
      }
    }
    
    $('#power-prev').addEventListener('click', () => {
      powerCurrentPage = Math.max(0, powerCurrentPage - 1);
      showPowerPage(powerCurrentPage);
    });
    
    $('#power-next').addEventListener('click', () => {
      powerCurrentPage = Math.min(totalPowerPages - 1, powerCurrentPage + 1);
      showPowerPage(powerCurrentPage);
    });
    
    showPowerPage(0);

    // Box Score
    $('#box-home-abbr').textContent = data.box.home.abbr;
    $('#box-home-name').textContent = data.box.home.name;
    $('#box-away-abbr').textContent = data.box.away.abbr;
    $('#box-away-name').textContent = data.box.away.name;
    $('#box-score').textContent = `${data.box.home.total} — ${data.box.away.total}`;
    const q = $('#box-qtrs'); q.innerHTML = '';
    const header = document.createElement('div'); header.className='row';
    header.innerHTML = '<div></div><div>Q1</div><div>Q2</div><div>Q3</div><div>Q4</div>';
    q.appendChild(header);
    const rHome = document.createElement('div'); rHome.className='row';
    rHome.innerHTML = `<div>${data.box.home.abbr}</div>${data.box.home.quarters.map(v=>`<div>${v}</div>`).join('')}`;
    q.appendChild(rHome);
    const rAway = document.createElement('div'); rAway.className='row';
    rAway.innerHTML = `<div>${data.box.away.abbr}</div>${data.box.away.quarters.map(v=>`<div>${v}</div>`).join('')}`;
    q.appendChild(rAway);

    // Box Score Top Performers
    const boxPerformers = $('#box-top-performers');
    if (boxPerformers) {
      boxPerformers.innerHTML = `
        <h4>Top Performers</h4>
        <div class="team-performers">
          <strong>${data.box.home.abbr}</strong>
          <div class="performer">
            <span>Mac Jones</span>
            <span>24/31, 287 yards, 3 TD</span>
          </div>
          <div class="performer">
            <span>Rhamondre Stevenson</span>
            <span>18 att, 89 yards, 1 TD</span>
          </div>
          <div class="performer">
            <span>JuJu Smith-Schuster</span>
            <span>6 rec, 98 yards, 1 TD</span>
          </div>
        </div>
        <div class="team-performers">
          <strong>${data.box.away.abbr}</strong>
          <div class="performer">
            <span>Davis Mills</span>
            <span>18/28, 156 yards, 1 TD, 1 INT</span>
          </div>
          <div class="performer">
            <span>Dameon Pierce</span>
            <span>12 att, 45 yards, 0 TD</span>
          </div>
          <div class="performer">
            <span>Brandin Cooks</span>
            <span>5 rec, 67 yards, 0 TD</span>
          </div>
        </div>
      `;
    }

    // Play by Play
    const pbp = $('#playbyplay-body .pbp-container');
    if (pbp && data.playbyplay) {
      pbp.innerHTML = '';
      data.playbyplay.forEach(entry => {
        const entryEl = document.createElement('div');
        entryEl.className = 'pbp-entry';
        entryEl.innerHTML = `
          <span class="pbp-time">${entry.time}</span>
          <span class="pbp-play">${entry.play}</span>
        `;
        pbp.appendChild(entryEl);
      });
    }

    // Team Top Performers
    const tt = $('#team-top-body'); tt.innerHTML='';
    Object.entries(data.teamTop).forEach(([label, items])=>{
      const h = document.createElement('div');
      h.innerHTML = `<h4 style="margin:14px 0 6px 0">${label.toUpperCase()}</h4>`;
      tt.appendChild(h);
      items.forEach(p=>{
        const rowEl = document.createElement('div'); rowEl.className='tr';
        rowEl.style.gridTemplateColumns = '1fr 1fr';
        rowEl.innerHTML = `<div>${p.name} <span class="muted">${p.pos}</span></div><div>${p.line}</div>`;
        tt.appendChild(rowEl);
      });
    });

    // League Top Performers (carousel)
    const lb = $('#league-top-body .table');
    let leagueCurrentPage = 0;
    const leaguePerPage = 5;
    
    function renderLeague(list){
      lb.innerHTML = '<div class="tr th"><div>#</div><div>Player</div><div>Value</div></div>';
      const totalPages = Math.ceil(list.length / leaguePerPage);
      const start = leagueCurrentPage * leaguePerPage;
      const end = Math.min(start + leaguePerPage, list.length);
      
      for (let i = start; i < end; i++) {
        const p = list[i];
        lb.appendChild(row([i+1, `${p.name} <span class="muted">(${p.pos})</span><div class="muted" style="font-size:12px">${p.id}</div>`, p.value]));
      }
    }
    
    function showLeaguePage(page, list) {
      leagueCurrentPage = page;
      const lb = $('#league-top-body .table');
      lb.innerHTML = '<div class="tr th"><div>#</div><div>Player</div><div>Value</div></div>';
      const start = page * leaguePerPage;
      const end = Math.min(start + leaguePerPage, list.length);
      
      for (let i = start; i < end; i++) {
        const p = list[i];
        lb.appendChild(row([i+1, `${p.name} <span class="muted">(${p.pos})</span><div class="muted" style="font-size:12px">${p.id}</div>`, p.value]));
      }
    }
    
    $('#league-prev').addEventListener('click', () => {
      const totalPages = Math.ceil(data.leagueTop.length / leaguePerPage);
      leagueCurrentPage = Math.max(0, leagueCurrentPage - 1);
      showLeaguePage(leagueCurrentPage, data.leagueTop);
    });
    
    $('#league-next').addEventListener('click', () => {
      const totalPages = Math.ceil(data.leagueTop.length / leaguePerPage);
      leagueCurrentPage = Math.min(totalPages - 1, leagueCurrentPage + 1);
      showLeaguePage(leagueCurrentPage, data.leagueTop);
    });

    renderLeague(data.leagueTop);

    $('#league-metric').addEventListener('change', ()=>{
      leagueCurrentPage = 0;
      renderLeague(data.leagueTop);
    });
    $('#league-scope').addEventListener('change', ()=>{
      leagueCurrentPage = 0;
      renderLeague(data.leagueTop);
    });

    // Box Score Continuation (C3 portion)
    const boxContinuation = $('#box-continuation-body');
    if (boxContinuation) {
      boxContinuation.innerHTML = `
        <div class="game-stats">
          <h4>Team Stats</h4>
          <div class="stat-row">
            <span>Total Yards</span>
            <span>NE: 387 | HOU: 234</span>
          </div>
          <div class="stat-row">
            <span>Passing Yards</span>
            <span>NE: 287 | HOU: 156</span>
          </div>
          <div class="stat-row">
            <span>Rushing Yards</span>
            <span>NE: 100 | HOU: 78</span>
          </div>
          <div class="stat-row">
            <span>Time of Possession</span>
            <span>NE: 32:15 | HOU: 27:45</span>
          </div>
          <div class="stat-row">
            <span>Turnovers</span>
            <span>NE: 1 | HOU: 2</span>
          </div>
        </div>
      `;
    }
  }

  setTabs();
  load().catch(err=>console.error(err));
})();
