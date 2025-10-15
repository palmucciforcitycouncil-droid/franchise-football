import { makePager } from './carouselUtil.js';

const left  = document.getElementById('std-left');
const right = document.getElementById('std-right');

// Assume we have divisions[] and currentIndex managed here.
let divisions = []; // [{name:'AFC East', teams:[...]}...]
let page = 0;

function getCount(){ return divisions.length || 1; }
function getPage(){ return page; }
function setPage(v){
  page = Math.max(0, Math.min(v, getCount()-1));
  renderDivision(divisions[page]);
}

const pager = makePager({getCount, getPage, setPage, leftBtn:left, rightBtn:right});

function renderDivision(division) {
  if (!division) return;
  
  const html = `<div class="list-compact">
    ${division.teams.map(t=>`<div class="row">
      <div>
        <div>${t.name}</div>
        <div class="muted">${t.pf||995} PF / ${t.pa||987} PA</div>
      </div>
      <div class="kv">
        <span class="k">Record</span>
        <span>${t.w}-${t.l}</span>
      </div>
    </div>`).join("")}
  </div>`;
  
  const cardBody = document.querySelector('#standings-card .card-body');
  if (cardBody) cardBody.innerHTML = html;
}

export async function initStandings(){
  const ok = await loadDivisions(); // fill divisions[]; on fail => demo data
  setPage(0);
  pager.apply(); // enable/disable arrows correctly
}

async function loadDivisions() {
  try {
    const response = await fetch('/api/standings');
    if (response.ok) {
      const data = await response.json();
      divisions = data.divisions || [];
      return true;
    }
  } catch (e) {
    console.warn('Failed to load standings:', e);
  }
  
  // Fallback demo data
  divisions = [
    {name: 'AFC East', teams: [
      {name: 'Patriots', w: 10, l: 7, pf: 995, pa: 987},
      {name: 'Bills', w: 9, l: 8, pf: 1023, pa: 945},
      {name: 'Jets', w: 7, l: 10, pf: 876, pa: 1023},
      {name: 'Dolphins', w: 11, l: 6, pf: 1087, pa: 892}
    ]},
    {name: 'AFC West', teams: [
      {name: 'Chiefs', w: 12, l: 5, pf: 1156, pa: 834},
      {name: 'Chargers', w: 8, l: 9, pf: 945, pa: 1023},
      {name: 'Raiders', w: 6, l: 11, pf: 823, pa: 1087},
      {name: 'Broncos', w: 5, l: 12, pf: 756, pa: 1156}
    ]}
  ];
  
  // Show demo badge
  const demoBadge = document.getElementById('std-demo');
  if (demoBadge) demoBadge.hidden = false;
  
  return false;
}
