const charts = [
  // chart 0 is by far the heaviest (~40k OSM road / rail features). We
  // render it on a canvas (small DOM) AND defer it until it nears the
  // viewport via IntersectionObserver, so the initial page load and the
  // scroll past the hero stay smooth.
  { id: '#chart-0',  file: '00-bay-locator.vg.json',     renderer: 'canvas', lazy: true },
  { id: '#chart-1',  file: '01-beach-locations.vg.json' },
  { id: '#chart-2',  file: '02-avg-quality-map.vg.json' },
  { id: '#chart-7',  file: '07-ranking-bar.vg.json' },
  { id: '#chart-3',  file: '03-seasonal-heatmap.vg.json' },
  { id: '#chart-5',  file: '05-beach-eras-dumbbell.vg.json' },
  { id: '#chart-8',  file: '08-risk-calendar.vg.json' },
  { id: '#chart-4',  file: '04-rainfall-scatter.vg.json' },
  { id: '#chart-6',  file: '06-rain-bucket-bar.vg.json' },
  { id: '#chart-9',  file: '09-region-box.vg.json' },
  { id: '#chart-10', file: '10-decision-matrix.vg.json' },
];

const baseEmbedOptions = {
  actions: false,
  config: { background: 'transparent' }
};

(async () => {
  let prefix = 'charts/';
  try {
    const probe = await fetch('charts/00-bay-locator.vg.json', { method: 'HEAD' });
    if (!probe.ok) prefix = '';
  } catch (_) {
    prefix = '';
  }

  const embed = (id, file, renderer) => {
    const opts = { ...baseEmbedOptions, renderer: renderer || 'svg' };
    return vegaEmbed(id, prefix + file, opts)
      .catch(err => {
        console.error(`Failed to render ${id}:`, err);
        const el = document.querySelector(id);
        if (el) el.innerHTML = `<div class="chart-error">Chart failed to load: ${err.message}</div>`;
      });
  };

  charts.forEach(({ id, file, renderer, lazy }) => {
    if (lazy && 'IntersectionObserver' in window) {
      const el = document.querySelector(id);
      if (!el) {
        embed(id, file, renderer);
        return;
      }
      // Start loading 800px before the chart enters the viewport so it
      // is usually ready by the time the user scrolls onto it.
      const observer = new IntersectionObserver((entries, obs) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            obs.disconnect();
            embed(id, file, renderer);
            break;
          }
        }
      }, { rootMargin: '800px 0px' });
      observer.observe(el);
    } else {
      embed(id, file, renderer);
    }
  });
})();
