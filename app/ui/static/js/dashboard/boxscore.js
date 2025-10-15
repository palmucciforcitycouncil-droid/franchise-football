import { demoBox, withDemo } from './demoData.js';

const el = (sel) => document.querySelector(sel);

/** Initialize on dashboard load */
export async function initBoxScore(){
  const flag = el('#box-demo-flag');
  
  const { data, isDemo } = await withDemo(
    async (signal) => {
      const r = await fetch('/api/boxscore/last', { 
        headers: {'Accept': 'application/json'},
        signal
      });
      if (!r.ok) throw new Error('bad status');
      return r.json();
    },
    demoBox
  );
  
  if (isDemo) {
    showErrorBanner();
    flag.hidden = false;
  } else {
    flag.hidden = true;
  }
  
  renderBox(data);
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
  
  // Handle both old format (home_abbr/away_abbr) and new format (home_id/away_id)
  const homeId = d.home_id || d.home_abbr || 'HOME';
  const awayId = d.away_id || d.away_abbr || 'AWAY';
  
  // Handle both old format (score_by_quarter_*) and new format (q array)
  let homeQuarters, awayQuarters, homeTotal, awayTotal;
  
  if (d.q && Array.isArray(d.q)) {
    // New format: q: [{NE:7,BUF:3}, {NE:10,BUF:7}, ...]
    homeQuarters = d.q.map(q => q[homeId] || 0);
    awayQuarters = d.q.map(q => q[awayId] || 0);
    homeTotal = d.totals?.[homeId] || homeQuarters.reduce((a,b) => a+b, 0);
    awayTotal = d.totals?.[awayId] || awayQuarters.reduce((a,b) => a+b, 0);
  } else {
    // Old format
    homeQuarters = d.score_by_quarter_home || [0,0,0,0];
    awayQuarters = d.score_by_quarter_away || [0,0,0,0];
    homeTotal = d.home_score || homeQuarters.reduce((a,b) => a+b, 0);
    awayTotal = d.away_score || awayQuarters.reduce((a,b) => a+b, 0);
  }
  
  const home = rowForTeam(homeId, homeQuarters, homeTotal);
  const away = rowForTeam(awayId, awayQuarters, awayTotal);
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

function showErrorBanner(){
  const cardBody = document.querySelector('#boxscore-card .card-body');
  if (cardBody && !cardBody.querySelector('.error-banner')) {
    const banner = document.createElement('div');
    banner.className = 'error-banner';
    banner.innerHTML = 'Couldn\'t load. Showing demo data.';
    cardBody.insertBefore(banner, cardBody.firstChild);
  }
}

// auto-run on page load (if card exists)
if (document.getElementById('boxscore-card')) {
  initBoxScore();
}
