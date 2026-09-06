import { makePager } from './carouselUtil.js';

const left  = document.getElementById('ttp-left');
const right = document.getElementById('ttp-right');

let pages = []; 
let page = 0;

function getCount(){ return pages.length || 1; }
function getPage(){ return page; }
function setPage(v){ 
  page = Math.max(0, Math.min(v, getCount()-1)); 
  renderTeamPerformers(pages[page]); 
}

const pager = makePager({getCount, getPage, setPage, leftBtn:left, rightBtn:right});

function renderTeamPerformers(performers) {
  if (!performers) return;
  
  const html = `<div class="list-compact">
    ${performers.map(p => `<div class="row">
      <div>
        <div>${p.player}</div>
        <div class="muted">${p.position}</div>
      </div>
      <div class="kv">
        <span class="k">${p.stat}</span>
        <span>${p.value}</span>
      </div>
    </div>`).join("")}
  </div>`;
  
  const cardBody = document.querySelector('#team-perf-card .card-body');
  if (cardBody) cardBody.innerHTML = html;
}

export async function initTeamPerformers(){
  const ok = await loadTeamPerformers(); // fill pages
  setPage(0); 
  pager.apply();
}

function chunk(arr, size=5){
  const out=[]; 
  for(let i=0;i<arr.length;i+=size){ 
    out.push(arr.slice(i,i+size)); 
  }
  return out.length ? out : [[]];
}

async function loadTeamPerformers() {
  try {
    const response = await fetch('/api/team/performers');
    if (response.ok) {
      const data = await response.json();
      pages = chunk(data.performers || [], 5);
      return true;
    }
  } catch (e) {
    console.warn('Failed to load team performers:', e);
  }
  
  // Fallback demo data
  const demoPerformers = [
    {player: "Casey Allen", position: "QB", stat: "Passing Yards", value: "2,847"},
    {player: "Jordan Moss", position: "RB", stat: "Rushing Yards", value: "1,234"},
    {player: "Terry Hill", position: "WR", stat: "Receiving Yards", value: "987"},
    {player: "Chris Harris", position: "CB", stat: "Tackles", value: "89"},
    {player: "Sam Jackson", position: "DE", stat: "Sacks", value: "8.5"},
    {player: "Alex Brown", position: "WR", stat: "Receptions", value: "67"},
    {player: "Marcus Johnson", position: "RB", stat: "Rush TDs", value: "12"},
    {player: "Jalen Jackson", position: "QB", stat: "Pass TDs", value: "24"},
    {player: "Chris White", position: "LB", stat: "Tackles", value: "76"},
    {player: "Sam Wilson", position: "S", stat: "Interceptions", value: "4"}
  ];
  
  pages = chunk(demoPerformers, 5);
  
  // Show demo badge
  const demoBadge = document.getElementById('ttp-demo');
  if (demoBadge) demoBadge.hidden = false;
  
  return false;
}

export function setPages(arr){ 
  pages = arr; 
  pager.apply(); 
}
