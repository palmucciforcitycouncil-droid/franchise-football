// Standings widget: renders NFL-style compact table with Team, W/L/T, Pct, PF/PA, Home/Away, Strk.
// Expects GET /api/standings to return something like:
// {
//   "division": "AFC East",
//   "teams": [
//     {"abbr":"NE","name":"Patriots","w":4,"l":2,"t":0,"pf":150,"pa":120,"home_w":1,"home_l":2,"away_w":3,"away_l":0,"streak":3},
//     ...
//   ]
// }

const TBODY = document.getElementById('std-tbody');
const DIVNAME = document.getElementById('std-division-name');
const DEMOBADGE = document.getElementById('std-demo');

export async function initStandings(){
  let payload;
  try{
    const r = await fetch('/api/standings',{headers:{'Accept':'application/json'}});
    if(!r.ok) throw new Error('bad status '+r.status);
    payload = await r.json();
  }catch(err){
    // Demo fallback
    DEMOBADGE.hidden = false;
    payload = demoStandings();
  }
  renderStandings(payload);
}

function renderStandings(data){
  const teams = Array.isArray(data?.teams) ? data.teams.slice() : [];
  DIVNAME.textContent = data?.division || 'Division';

  // Sort by win pct, then PF diff (PF-PA)
  teams.sort((a,b)=>{
    const pa = winPct(a), pb = winPct(b);
    if(pb !== pa) return pb - pa;
    const da = (a.pf||0)-(a.pa||0), db = (b.pf||0)-(b.pa||0);
    return db - da;
  });

  TBODY.innerHTML = teams.map(t => rowHtml(t)).join('');
}

function rowHtml(t){
  const abbr = normalizeAbbr(t.abbr || t.team || '');
  const name = t.name || teamNameFromAbbr(abbr) || abbr;
  const w = t.w|0, l = t.l|0, tt = t.t|0;
  const pct = toPct(winPct(t));
  const pf = t.pf|0, pa = t.pa|0;
  const home = `${t.home_w|0}-${t.home_l|0}`;
  const away = `${t.away_w|0}-${t.away_l|0}`;
  const strk = streakStr(t.streak);
  const strkClass = (t.streak||0) >= 0 ? 'win' : 'loss';

  return `
    <tr>
      <td>
        <div class="std-team">
          <span class="std-abbr">${abbr}</span>
          <span class="std-name">${name}</span>
        </div>
      </td>
      <td>${w}</td>
      <td>${l}</td>
      <td>${tt}</td>
      <td class="std-pct">${pct}</td>
      <td>${pf}</td>
      <td>${pa}</td>
      <td>${home}</td>
      <td>${away}</td>
      <td class="std-strk ${strkClass}">${strk}</td>
    </tr>`;
}

function winPct(t){
  const w=t.w|0, l=t.l|0, tt=t.t|0;
  const g=w+l+tt;
  if(!g) return 0;
  return (w + 0.5*tt) / g;
}
function toPct(x){
  // format like .667, .500, .000
  return x === 0 ? '.000' : ('.' + Math.round(x*1000).toString().padStart(3,'0'));
}
function streakStr(s){
  // positive => Wn, negative => Ln, 0 => –
  if(!s) return '–';
  const n = Math.abs(s);
  return (s>0?'W':'L')+n;
}
// Normalize to requested style (NE, BUF, MIA, NYJ, etc.; allow BUFF from input)
function normalizeAbbr(a){
  const up = String(a||'').toUpperCase();
  if(up==='BUFF') return 'BUF';
  return up;
}
function teamNameFromAbbr(ab){
  const map = {
    NE:'Patriots', BUF:'Bills', MIA:'Dolphins', NYJ:'Jets',
    DAL:'Cowboys', NYG:'Giants', PHI:'Eagles', WAS:'Commanders'
    // extend as needed; fallback uses abbr
  };
  return map[ab];
}

function demoStandings(){
  return {
    division:'AFC East',
    teams:[
      {abbr:'NE',  name:'Patriots', w:4, l:2, t:0, pf:150, pa:120, home_w:1, home_l:2, away_w:3, away_l:0, streak: 3},
      {abbr:'BUF', name:'Bills',     w:4, l:2, t:0, pf:167, pa:137, home_w:3, home_l:1, away_w:1, away_l:1, streak:-2},
      {abbr:'MIA', name:'Dolphins',  w:1, l:5, t:0, pf:134, pa:174, home_w:1, home_l:2, away_w:0, away_l:3, streak:-2},
      {abbr:'NYJ', name:'Jets',      w:0, l:6, t:0, pf:123, pa:170, home_w:0, home_l:4, away_w:0, away_l:2, streak:-6}
    ]
  };
}

// Auto-init if the card exists
if (TBODY) { initStandings(); }