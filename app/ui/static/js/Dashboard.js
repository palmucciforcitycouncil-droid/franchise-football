/* Dashboard v3.0 — robust render + safe fallbacks + clear logs */
(function(){
  const LOG='[Dashboard]';
  console.info(`${LOG} loading v3.0`);

  function qs(s, r=document){ return r.querySelector(s); }
  function setText(el, txt){ if(el) el.textContent = txt; }

  async function render() {
    const api = window.uiAdapters?.dashboard;
    if (!api) { console.error(`${LOG} adapter missing`); return; }

    // Grab DOM targets (works with your restored template structure)
    const elSeason  = qs('[data-card="season-status"]') || qs('#card-season-status');
    const elChamp   = qs('[data-card="championship"]')  || qs('#card-championship');
    const elLeaders = qs('[data-card="leaders"]')       || qs('#card-leaders');

    try {
      // Load all in parallel (fast)
      const [season, champs, leaders] = await Promise.all([
        api.getSeasonSummary(),
        api.getChampionship(),
        api.getLeaders()
      ]);

      // Season Status
      if (elSeason) {
        setText(qs('[data-field="week"]', elSeason), `Week ${season.week ?? '?'}`);
        setText(qs('[data-field="record"]', elSeason), season.record ?? '');
        setText(qs('[data-field="health"]', elSeason), season.health ?? '');
      }

      // Championship
      if (elChamp) {
        const label = champs?.champion ? `Champion: ${champs.champion}` :
                      (champs?.stage ? `(${champs.stage})` : 'No champion yet.');
        setText(qs('[data-field="champion"]', elChamp), label);
      }

      // Leaders
      if (elLeaders) {
        const qb = leaders?.qb, rb = leaders?.rb;
        const txt = [
          qb ? `QB: ${qb.name} (OVR ${qb.ovr})` : null,
          rb ? `RB: ${rb.name} (OVR ${rb.ovr})` : null
        ].filter(Boolean).join('   |   ');
        setText(qs('[data-field="leaders"]', elLeaders), txt || 'No leaders available');
      }

      console.info(`${LOG} render complete`);
    } catch (e) {
      console.error(`${LOG} render error`, e);
    }

    // Wire buttons
    qs('[data-action="simulate"]')?.addEventListener('click', async () => {
      console.info(`${LOG} simulate clicked`);
      await api.simulateWeek();
      render(); // re-paint
    });
    qs('[data-action="playoffs"]')?.addEventListener('click', async () => {
      console.info(`${LOG} playoffs clicked`);
      await api.startPlayoffs();
      render();
    });
    qs('[data-action="offseason"]')?.addEventListener('click', async () => {
      console.info(`${LOG} offseason clicked`);
      await api.processOffseason();
      render();
    });
  }

  // Kick off when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
