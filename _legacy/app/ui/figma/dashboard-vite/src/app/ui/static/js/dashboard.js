import { j, qs } from "/static/js/ui.js";

(async function(){
  // wire buttons
  const seasonInput = qs("#season");
  const seedInput = qs("#seed");
  const out = qs("#out");

  async function run(fn){
    out.textContent = "…"; 
    try{ out.textContent = JSON.stringify(await fn(), null, 2); }
    catch(e){ out.textContent = "Error: "+e.message; }
  }

  qs("#seedTeams").onclick = ()=> run(()=> j("/api/sim/seed-teams",{method:"POST"}));
  qs("#seedRosters").onclick = ()=> run(()=> j("/api/roster/seed",{method:"POST"}));
  qs("#importPlayers").onclick = ()=> run(()=> j("/api/admin/import/players",{method:"POST"}));
  qs("#importCoaches").onclick = ()=> run(()=> j("/api/admin/import/coaches",{method:"POST"}));

  qs("#initSeason").onclick = ()=> {
    const y = Number(seasonInput.value||"2025"); const s = Number(seedInput.value||"2025");
    return run(()=> j(`/api/admin/season/init/${y}?seed=${s}`,{method:"POST"}));
  };
  qs("#buildSchedule").onclick = ()=> {
    const y = Number(seasonInput.value||"2025"); const s = Number(seedInput.value||"1234");
    return run(()=> j(`/api/sim/schedule/${y}?seed=${s}`,{method:"POST"}));
  };
  qs("#advanceWeek").onclick = ()=> {
    const y = Number(seasonInput.value||"2025");
    return run(()=> j(`/api/admin/season/${y}/advance`,{method:"POST"}));
  };

  qs("#buildPO").onclick = ()=> {
    const y = Number(seasonInput.value||"2025");
    return run(()=> j(`/api/playoffs/build/${y}`,{method:"POST"}));
  };
  qs("#runPO").onclick = ()=> {
    const y = Number(seasonInput.value||"2025"); const s = Number(seedInput.value||"2025");
    return run(()=> j(`/api/playoffs/run/${y}?seed=${s}`,{method:"POST"}));
  };

  qs("#runOff").onclick = ()=> {
    const y = Number(seasonInput.value||"2025"); const s = Number(seedInput.value||"2025");
    return run(()=> j(`/api/offseason/run/${y}?seed=${s}`,{method:"POST"}));
  };
  qs("#newPre").onclick = ()=> {
    const y = Number((Number(seasonInput.value||"2025")+1));
    return run(()=> j(`/api/offseason/advance-to-preseason/${y}?seed=${y}`,{method:"POST"}));
  };

  qs("#save").onclick = ()=> run(()=> j(`/api/save`,{method:"POST"}));
  qs("#load").onclick = async ()=>{
    // naive: reload whatever was just saved into the textarea
    const txt = qs("#payload").value.trim();
    if(!txt){ out.textContent="Paste JSON payload first."; return; }
    await run(()=> j(`/api/load`,{method:"POST", body: txt}));
  };

  // quick-links
  qs("#viewGames").onclick = ()=>{
    const y = Number(seasonInput.value||"2025"); const w = Number(qs("#week").value||"1");
    location.href = `/games/${y}/${w}`;
  };
  qs("#viewTeams").onclick = ()=> location.href = `/teams`;
  qs("#ping").onclick = async ()=> run(()=> j(`/api/health`));
})();
