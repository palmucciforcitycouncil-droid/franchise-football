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

    // Power Rankings
    const pb = $('#power-body'); pb.innerHTML = '';
    data.power.forEach((rowObj, i)=>{
      const r = document.createElement('div'); r.className='tr';
      r.innerHTML = `<div>${i+1}</div><div>${rowObj.team}</div><div>${rowObj.score}</div>`;
      pb.appendChild(r);
    });

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

    // League Top Performers
    const lb = $('#league-top-body .table');
    function renderLeague(list){
      lb.innerHTML = '<div class="tr th"><div>#</div><div>Player</div><div>Value</div></div>';
      list.forEach((p,i)=>{
        lb.appendChild(row([i+1, `${p.name} <span class="muted">(${p.pos})</span><div class="muted" style="font-size:12px">${p.id}</div>`, p.value]));
      });
    }
    renderLeague(data.leagueTop);

    $('#league-metric').addEventListener('change', ()=>renderLeague(data.leagueTop));
    $('#league-scope').addEventListener('change', ()=>renderLeague(data.leagueTop));
  }

  setTabs();
  load().catch(err=>console.error(err));
})();
