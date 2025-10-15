import { makePager } from './carouselUtil.js';

const left  = document.getElementById('lgp-left');
const right = document.getElementById('lgp-right');

let pages = []; // each page => array of 5 performers
let page = 0;

function getCount(){ return pages.length || 1; }
function getPage(){ return page; }
function setPage(v){
  page = Math.max(0, Math.min(v, getCount()-1));
  renderLeaguePerformers(pages[page]);
}

const pager = makePager({getCount, getPage, setPage, leftBtn:left, rightBtn:right});

function renderLeaguePerformers(performers) {
  if (!performers) return;
  
  const html = `<ol class="list">
    ${performers.map((p, i) => `<li>${p.rank || i+1}. ${p.player} <span class="muted">${p.value || p.val}</span></li>`).join("")}
  </ol>`;
  
  const cardBody = document.querySelector('#league-perf-card .card-body');
  if (cardBody) cardBody.innerHTML = html;
}

export async function initLeaguePerformers(){
  const ok = await loadLeaguePerformers(); // shape into pages of 5
  page = 0;
  renderLeaguePerformers(pages[page]);
  pager.apply();
}

function chunk(arr, size=5){
  const out=[]; 
  for(let i=0;i<arr.length;i+=size){ 
    out.push(arr.slice(i,i+size)); 
  }
  return out.length ? out : [[]];
}

async function loadLeaguePerformers() {
  try {
    const response = await fetch('/api/performers');
    if (response.ok) {
      const data = await response.json();
      pages = chunk(data.performers || [], 5);
      return true;
    }
  } catch (e) {
    console.warn('Failed to load league performers:', e);
  }
  
  // Fallback demo data
  const demoPerformers = [
    {rank: 1, player: "Chris White (QB)", val: "103.8"},
    {rank: 2, player: "Casey Jones (QB)", val: "102.6"},
    {rank: 3, player: "Jalen Jackson (QB)", val: "100.4"},
    {rank: 4, player: "Marcus Johnson (RB)", val: "98.2"},
    {rank: 5, player: "Terry Hill (WR)", val: "96.8"},
    {rank: 6, player: "Sam Wilson (QB)", val: "94.5"},
    {rank: 7, player: "Jordan Moss (RB)", val: "92.1"},
    {rank: 8, player: "Alex Brown (WR)", val: "89.7"},
    {rank: 9, player: "Chris Harris (CB)", val: "87.3"},
    {rank: 10, player: "Sam Jackson (DE)", val: "85.9"}
  ];
  
  pages = chunk(demoPerformers, 5);
  
  // Show demo badge
  const demoBadge = document.getElementById('lgp-demo');
  if (demoBadge) demoBadge.hidden = false;
  
  return false;
}

// expose for loader to set pages after fetch
export function setPages(arr){ 
  pages = arr; 
  pager.apply(); 
}
