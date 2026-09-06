import { j, qs, el } from "/static/js/ui.js";

const state = {
  season: Number(qs("#season")?.value || "2025"),
  tab: "AFC",
  data: null
};

function setStatus(txt){ qs("#msg").textContent = txt; }

function badge(txt, cls=""){ return el("span",{className:`badge ${cls}`}, txt); }
function row(match){
  const hi = match.higher_seed_team, lo = match.lower_seed_team;
  const score = (match.higher_seed_score ?? "-") + " – " + (match.lower_seed_score ?? "-");
  const done = match.is_complete ? " (F)" : "";
  return el("div",{className:"rowline"},
    el("div",{className:"seed"}, `#${hi.seed||"?"}`),
    el("div",{className:"team"}, `${hi.team_abbr} ${hi.team_name}`),
    el("div",{className:"vs"},"vs"),
    el("div",{className:"seed"}, `#${lo.seed||"?"}`),
    el("div",{className:"team"}, `${lo.team_abbr} ${lo.team_name}`),
    el("div",{className:"score"}, score + done)
  );
}

function renderBracket(){
  const br = qs("#bracket"); br.innerHTML = "";
  const title = qs("#roundTitle");
  if(!state.data){ title.textContent = "Bracket"; return; }

  if(state.tab === "SB"){
    title.textContent = "Super Bowl";
    const sb = state.data.rounds.find(r => r.round_name === "SB");
    if(!sb || !sb.matchups.length){ br.textContent = "No Super Bowl matchup yet."; return; }
    sb.matchups.forEach(m => br.append(row(m)));
    return;
  }

  const side = state.tab; // "AFC" | "NFC"
  title.textContent = `${side} Bracket`;
  const order = ["WC","DIV","CONF"];
  order.forEach(rn => {
    const rnd = state.data.rounds.find(r => r.round_name === rn && (r.matchups[0]?.side === side));
    const box = el("div",{className:"round"});
    box.append(el("h3",{}, rn === "WC" ? "Wild Card" : rn === "DIV" ? "Divisional" : "Conference"));
    if(!rnd || rnd.matchups.length === 0){
      box.append(el("div",{className:"muted"},"No matchups yet.")); 
    } else {
      rnd.matchups.forEach(m => box.append(row(m)));
    }
    br.append(box);
  });
}

function renderHunt(){
  const hn = qs("#hunt"); hn.innerHTML = "";
  if(!state.data) return;
  ["AFC","NFC"].forEach(side=>{
    const hdr = el("div",{className:"huntHdr"}, side);
    hn.append(hdr);
    const items = state.data.in_the_hunt.filter(t => t.side === side);
    if(items.length===0){ hn.append(el("div",{className:"muted"},"—")); return; }
    items.forEach(t=>{
      hn.append(el("div",{className:"huntItem"},
        `${t.team_abbr} ${t.team_name} — GB: ${t.games_back} • Seed if made: ${t.seed_if_made}`
      ));
    });
  });
}

function selectTab(tab){
  state.tab = tab;
  document.querySelectorAll(".tab").forEach(b=>{
    b.classList.toggle("red", b.dataset.tab==="AFC");
    b.classList.toggle("gold", b.dataset.tab==="SB");
    b.classList.toggle("blue", b.dataset.tab==="NFC");
  });
  renderBracket();
}

async function load(){
  setStatus("Loading…");
  try{
    const url = `/api/playoffs/bracket/${state.season}`;
    state.data = await j(url);
    setStatus("Loaded.");
    renderBracket();
    renderHunt();
  } catch(e){
    setStatus("Error: "+e.message);
  }
}

function wire(){
  qs("#season").addEventListener("change", (e)=> {
    state.season = Number(e.target.value || "2025"); load();
  });
  document.querySelectorAll(".tab").forEach(b => b.onclick = ()=> selectTab(b.dataset.tab));
  qs("#refresh").onclick = load;
  selectTab(state.tab);
  load();
}
wire();
