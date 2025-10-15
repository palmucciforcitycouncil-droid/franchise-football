const el = (sel) => document.querySelector(sel);

/** Initialize on dashboard load */
export async function initBoxScore(){
  const flag = el('#box-demo-flag');
  try{
    const r = await fetch('/api/boxscore/last', { headers:{'Accept':'application/json'} });
    if(!r.ok) throw new Error('bad status');
    const data = await r.json();
    renderBox(data);
  }catch(err){
    const data = demoBox();     // safe fallback (shapes match GDD)
    if (flag) flag.hidden = false;
    renderBox(data);
  }
}

/** Render everything */
function renderBox(data){
  renderQuarters(data);
  renderCompare(data);
  renderLeaders(data);
}

/** === Quarters Table === */
function renderQuarters(d){
  const rows = [];
  const home = rowForTeam(d.home_abbr || 'HOME', d.score_by_quarter_home, d.home_score);
  const away = rowForTeam(d.away_abbr || 'AWAY', d.score_by_quarter_away, d.away_score);
  rows.push(away, home); // away first like TV slates
  el('#qbody').innerHTML = rows.join('');
}
function rowForTeam(abbr, quarters = [0,0,0,0], total = 0){
  const cells = quarters.map(n => `<td>${n ?? 0}</td>`).join('');
  return `<tr><td class="qteam">${abbr}</td>${cells}<td><strong>${total ?? 0}</strong></td></tr>`;
}

/** === Team Comparison (compact) === */
function renderCompare(d){
  const L = [];
  const h = d.team_lines?.home || {};
  const a = d.team_lines?.away || {};
  const fmtPct = (x) => (x==null ? '—' : `${(x*100).toFixed(1)}%`);
  const fmt = (x) => (x==null ? '—' : x);

  const rows = [
    ['Total yards',          fmt(h.totals?.yards),             fmt(a.totals?.yards)],
    ['Passing yards',        fmt(h.pass?.yds),                 fmt(a.pass?.yds)],
    ['Rushing yards',        fmt(h.rush?.yds),                 fmt(a.rush?.yds)],
    ['Yards per play',       (h.totals?.ypp ?? '—'),           (a.totals?.ypp ?? '—')],
    ['First downs',          fmt(h.fd?.total),                 fmt(a.fd?.total)],
    ['3rd down efficiency',  fmtPct(h.situational?.conv3?.rate), fmtPct(a.situational?.conv3?.rate)],
    ['4th down efficiency',  fmtPct(h.situational?.conv4?.rate), fmtPct(a.situational?.conv4?.rate)],
    ['Total plays',          fmt(h.totals?.plays),             fmt(a.totals?.plays)],
    ['Sacks allowed',        fmt(h.pass?.sack),                fmt(a.pass?.sack)],
    ['Turnovers',            fmt(h.security?.to),              fmt(a.security?.to)],
    ['Penalties (Yds)',      penFmt(h.penalties),              penFmt(a.penalties)],
    ['Time of possession',   topFmt(h.totals?.top_sec),        topFmt(a.totals?.top_sec)],
  ];

  for (const [label, hv, av] of rows){
    L.push(`<div class="cmp-row">
      <div class="cmp-val">${hv}</div>
      <div class="cmp-label">${label}</div>
      <div class="cmp-val">${av}</div>
    </div>`);
  }
  el('#cmp-list').innerHTML = L.join('');
}
function penFmt(p){ if(!p) return '—'; const {count=0,yards=0}=p; return `${count} (${yards})`; }
function topFmt(sec){
  if(sec == null) return '—';
  const m = Math.floor(sec/60), s = sec%60;
  return `${m}:${String(s).padStart(2,'0')}`;
}

/** === Leaders (Passing/Rushing/Receiving) === */
function renderLeaders(d){
  const cont = el('#leaders');
  const cats = [
    ['Passing Yards', d.leaders?.passing],
    ['Rushing Yards', d.leaders?.rushing],
    ['Receiving Yards', d.leaders?.receiving]
  ];

  const html = cats.map(([title, block]) => leaderBlock(title, block)).join('');
  cont.innerHTML = html;
}
function leaderBlock(title, b){
  if(!b) return '';
  // expect shape { home:{name, stat}, away:{name, stat} }
  const h = b.home || {name:'—', stat:'—'};
  const a = b.away || {name:'—', stat:'—'};
  return `<div class="lead-section">
    <div class="lead-title">${title}</div>
    <div class="lead-grid">
      <div>
        <div class="pname">${h.name ?? '—'}</div>
        <div class="pstat">${h.stat ?? '—'}</div>
      </div>
      <div style="opacity:.6;">vs</div>
      <div style="text-align:right;">
        <div class="pname">${a.name ?? '—'}</div>
        <div class="pstat">${a.stat ?? '—'}</div>
      </div>
    </div>
  </div>`;
}

/** === Demo payload (shape aligns with GDD 3.1/3.3) === */
function demoBox(){
  return {
    game_id: 'demo_last',
    week_number: 5,
    home_abbr: 'NE',
    away_abbr: 'BUF',
    home_score: 27,
    away_score: 20,
    score_by_quarter_home: [7,10,3,7],
    score_by_quarter_away: [7,3,7,3],
    team_lines:{
      home:{
        totals:{ plays:63, yards:381, ypp:6.0, top_sec: 28*60+26 },
        rush:{ att:24, yds:145, td:1 },
        pass:{ att:35, cmp:23, yds:236, td:2, int:1, sack:3 },
        fd:{ total:19 }, situational:{ conv3:{made:3,att:10,rate:0.3}, conv4:{made:0,att:1,rate:0.0} },
        penalties:{ count:9, yards:84 }, security:{ to:1 }
      },
      away:{
        totals:{ plays:60, yards:329, ypp:5.5, top_sec: 31*60+34 },
        rush:{ att:22, yds:124, td:1 },
        pass:{ att:34, cmp:21, yds:205, td:1, int:1, sack:2 },
        fd:{ total:22 }, situational:{ conv3:{made:3,att:8,rate:0.375}, conv4:{made:1,att:1,rate:1.0} },
        penalties:{ count:5, yards:40 }, security:{ to:2 }
      }
    },
    leaders:{
      passing:{ home:{name:'Mac Jones', stat:'287 YDS, 3 TD'}, away:{name:'Josh Allen', stat:'156 YDS, 1 TD'} },
      rushing:{ home:{name:'R. Stevenson', stat:'18 CAR, 89 YDS, 1 TD'}, away:{name:'D. Singletary', stat:'12 CAR, 45 YDS'} },
      receiving:{ home:{name:'J. Smith-Schuster', stat:'6 REC, 98 YDS, 1 TD'}, away:{name:'S. Diggs', stat:'5 REC, 67 YDS'} }
    }
  };
}

// auto-run on page load (if card exists)
if (document.getElementById('boxscore-card')) {
  initBoxScore();
}
