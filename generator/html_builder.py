"""
generator/html_builder.py
--------------------------
Genera output/index.html a partir de output/results.json.
El HTML es un único archivo autocontenido (CSS y JS embebidos, sin CDN).
"""

import json
import os
import html as html_escape_lib


# ─── helpers ────────────────────────────────────────────────────────────────

def _esc(value) -> str:
    """Escapa para inserción segura en atributos/texto HTML."""
    return html_escape_lib.escape(str(value), quote=True)


def _fmt_price(price) -> str:
    if price is None:
        return "N/A"
    return f"${float(price):.2f}"


def _metascore_class(score) -> str:
    if score is None:
        return "ms-none"
    if score >= 75:
        return "ms-green"
    if score >= 50:
        return "ms-yellow"
    return "ms-red"


def _discount_class(pct) -> str:
    if pct is None or pct <= 0:
        return ""
    if pct >= 40:
        return "disc-high"
    if pct >= 20:
        return "disc-mid"
    return "disc-low"


def _platform_class(p: str) -> str:
    p_low = p.lower()
    if "ps" in p_low or "playstation" in p_low:
        return "plat-ps"
    if "xbox" in p_low:
        return "plat-xbox"
    if "switch" in p_low or "nintendo" in p_low:
        return "plat-nintendo"
    return "plat-pc"


def _store_logo(store: str) -> str:
    logos = {
        "Steam": "🎮 Steam",
        "Amazon": "📦 Amazon",
        "PlayStation Store": "🎯 PS Store",
    }
    return logos.get(store, store)


# ─── constructores de fragmentos HTML ───────────────────────────────────────

def _build_platform_badges(platforms: list) -> str:
    badges = []
    for p in platforms:
        cls = _platform_class(p)
        badges.append(f'<span class="badge {cls}">{_esc(p)}</span>')
    return " ".join(badges)


def _build_price_block(game: dict) -> str:
    """Precio principal con descuento y badge Best Price."""
    prices = game.get("prices", [])
    if not prices:
        return '<div class="price-main">N/A</div>'

    # Mejor precio entre todas las tiendas
    valid = [p for p in prices if p.get("current_price") is not None]
    if not valid:
        return '<div class="price-main">N/A</div>'

    best_store = min(valid, key=lambda p: p["current_price"])
    best_price = best_store["current_price"]

    # Tomamos el primer precio con descuento para mostrar como "principal"
    # (en práctica suele ser Steam el primero disponible)
    main = valid[0]
    current = main.get("current_price")
    original = main.get("original_price")
    disc = main.get("discount_pct") or 0

    # Decidir si este juego tiene "Best Price" en alguna tienda
    # El badge lo mostramos siempre que haya más de una tienda (hay comparación real)
    is_best = len(valid) > 1  # siempre habrá UN mejor precio si hay varias

    html = '<div class="price-row">'
    html += f'<span class="price-current">{_fmt_price(current)}</span>'

    if original and original > current:
        html += f'<span class="price-original">{_fmt_price(original)}</span>'

    if disc and disc > 0:
        disc_cls = _discount_class(disc)
        html += f'<span class="badge disc-badge {disc_cls}">-{int(disc)}%</span>'

    if is_best:
        html += (
            f'<span class="badge best-price-badge" '
            f'title="Mejor precio: {_fmt_price(best_price)} en {_esc(best_store["store"])}">⭐ Best Price</span>'
        )

    html += "</div>"
    return html


def _build_store_row(prices: list) -> str:
    """Fila con el precio de cada tienda disponible."""
    if not prices:
        return ""
    items = []
    for p in prices:
        store = _esc(p.get("store", "?"))
        logo = _store_logo(p.get("store", ""))
        price = _fmt_price(p.get("current_price"))
        url = p.get("url", "#")
        items.append(
            f'<a class="store-price-item" href="{_esc(url)}" target="_blank" rel="noopener">'
            f'<span class="store-logo">{logo}</span>'
            f'<span class="store-price-val">{price}</span>'
            f"</a>"
        )
    return '<div class="store-prices">' + "".join(items) + "</div>"


def _build_metacritic_block(metacritic: list) -> str:
    """Círculo de Metascore + User Score (primer resultado disponible)."""
    if not metacritic:
        return (
            '<div class="mc-block">'
            '<div class="ms-circle ms-none">N/A</div>'
            '<span class="user-score">User: N/A</span>'
            "</div>"
        )
    entry = metacritic[0]
    ms = entry.get("metascore")
    us = entry.get("user_score")
    ms_cls = _metascore_class(ms)
    ms_txt = str(ms) if ms is not None else "N/A"
    us_txt = str(us) if us is not None else "N/A"
    return (
        '<div class="mc-block">'
        f'<div class="ms-circle {ms_cls}">{ms_txt}</div>'
        f'<span class="user-score">User: {us_txt}</span>'
        "</div>"
    )


def _build_hltb_block(hltb) -> str:
    """Tiempos HLTB con icono de reloj."""
    if not hltb:
        return '<div class="hltb-block"><span class="hltb-item">🕐 N/A</span></div>'
    main = hltb.get("main_story")
    extras = hltb.get("main_extras")
    parts = []
    if main is not None:
        parts.append(f'<span class="hltb-item">🕐 Main: {main}h</span>')
    if extras is not None:
        parts.append(f'<span class="hltb-item">🕑 +Extras: {extras}h</span>')
    if not parts:
        parts.append('<span class="hltb-item">🕐 N/A</span>')
    return '<div class="hltb-block">' + "".join(parts) + "</div>"


def _build_card(game: dict) -> str:
    title = _esc(game.get("title", "Unknown"))
    platforms = game.get("platforms", [])
    prices = game.get("prices", [])
    metacritic = game.get("metacritic", [])
    hltb = game.get("hltb")

    # data-* attributes para filtros JS
    plat_str = _esc(",".join(platforms).lower())
    # Mejor metascore para ordenar
    ms_vals = [e.get("metascore", 0) or 0 for e in metacritic]
    best_ms = max(ms_vals) if ms_vals else 0
    # Mejor descuento
    disc_vals = [p.get("discount_pct") or 0 for p in prices if p.get("current_price") is not None]
    best_disc = max(disc_vals) if disc_vals else 0
    # Precio mínimo
    price_vals = [p["current_price"] for p in prices if p.get("current_price") is not None]
    min_price = min(price_vals) if price_vals else 9999

    return f"""
<div class="card"
     data-title="{title.lower()}"
     data-platforms="{plat_str}"
     data-metascore="{best_ms}"
     data-discount="{best_disc}"
     data-min-price="{min_price}">
  <div class="card-header">
    <h2 class="game-title">{title}</h2>
    <div class="platform-badges">{_build_platform_badges(platforms)}</div>
  </div>
  <div class="card-body">
    <div class="price-meta-row">
      <div class="price-section">
        {_build_price_block(game)}
        {_build_store_row(prices)}
      </div>
      {_build_metacritic_block(metacritic)}
    </div>
    {_build_hltb_block(hltb)}
  </div>
</div>"""


# ─── sección de métricas (será reemplazada/complementada por Persona B) ─────

def _build_metrics(data: dict) -> str:
    """Tabla simple de rendimiento lineal vs paralelo (placeholder para B-4)."""
    lt = data.get("linear_time")
    pt = data.get("parallel_time")
    sp = data.get("speedup")
    total = data.get("total_games", 0)

    def fmt(v, suffix="s"):
        return f"{v:.2f}{suffix}" if v is not None else "—"

    def rate(t):
        if t and total:
            return f"{total/t:.2f} juegos/s"
        return "—"

    lt_bar = int((lt or 0) * 100 / max(lt or 1, pt or 1))
    pt_bar = int((pt or 0) * 100 / max(lt or 1, pt or 1))

    svg_lt_w = max(lt_bar * 3, 10)
    svg_pt_w = max(pt_bar * 3, 10)

    return f"""
<section class="metrics-section">
  <h2 class="metrics-title">⚡ Rendimiento: Lineal vs Paralelo</h2>
  <div class="metrics-grid">
    <table class="metrics-table">
      <thead>
        <tr><th>Métrica</th><th>Lineal</th><th>Paralelo</th></tr>
      </thead>
      <tbody>
        <tr><td>Tiempo total</td><td>{fmt(lt)}</td><td>{fmt(pt)}</td></tr>
        <tr><td>Juegos/segundo</td><td>{rate(lt)}</td><td>{rate(pt)}</td></tr>
        <tr><td>Speedup</td><td colspan="2" style="text-align:center">{fmt(sp, 'x')}</td></tr>
      </tbody>
    </table>
    <svg class="perf-chart" viewBox="0 0 360 140" xmlns="http://www.w3.org/2000/svg">
      <text x="180" y="18" text-anchor="middle" fill="#a0aec0" font-size="12">Tiempo de ejecución (seg)</text>
      <!-- Lineal -->
      <rect x="40" y="30" width="{svg_lt_w}" height="34" rx="4" fill="#e53e3e"/>
      <text x="{40 + svg_lt_w + 6}" y="52" fill="#e2e8f0" font-size="12">{fmt(lt)}</text>
      <text x="30" y="52" text-anchor="end" fill="#a0aec0" font-size="11">Lineal</text>
      <!-- Paralelo -->
      <rect x="40" y="76" width="{svg_pt_w}" height="34" rx="4" fill="#38a169"/>
      <text x="{40 + svg_pt_w + 6}" y="98" fill="#e2e8f0" font-size="12">{fmt(pt)}</text>
      <text x="30" y="98" text-anchor="end" fill="#a0aec0" font-size="11">Paralelo</text>
      <!-- Speedup label -->
      <text x="180" y="132" text-anchor="middle" fill="#667eea" font-size="12">Speedup: {fmt(sp, 'x')}</text>
    </svg>
  </div>
</section>"""


# ─── CSS ────────────────────────────────────────────────────────────────────

CSS = """
/* === Reset & base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #1a1a2e;
  color: #e2e8f0;
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  min-height: 100vh;
  padding: 0 0 60px;
}

a { color: inherit; text-decoration: none; }

/* === Header === */
.site-header {
  background: #16213e;
  border-bottom: 1px solid #2d3748;
  padding: 20px 24px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 12px #0006;
}
.site-header h1 { font-size: 1.5rem; color: #667eea; margin-bottom: 4px; }
.site-header p  { font-size: 0.8rem; color: #718096; }

/* === Controls === */
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 20px 24px;
  background: #16213e;
  border-bottom: 1px solid #2d3748;
}
.controls input, .controls select {
  background: #0f3460;
  border: 1px solid #2d3748;
  color: #e2e8f0;
  border-radius: 8px;
  padding: 8px 14px;
  font-size: 0.9rem;
  outline: none;
  transition: border-color .2s;
}
.controls input { flex: 1; min-width: 180px; }
.controls input:focus, .controls select:focus { border-color: #667eea; }
.controls select { cursor: pointer; }
#results-count { color: #718096; font-size: 0.85rem; align-self: center; margin-left: auto; }

/* === Metrics === */
.metrics-section {
  margin: 24px 24px 0;
  background: #16213e;
  border: 1px solid #2d3748;
  border-radius: 12px;
  padding: 20px 24px;
}
.metrics-title { font-size: 1rem; color: #a0aec0; margin-bottom: 16px; }
.metrics-grid { display: flex; flex-wrap: wrap; gap: 24px; align-items: flex-start; }
.metrics-table { border-collapse: collapse; font-size: 0.88rem; min-width: 240px; }
.metrics-table th, .metrics-table td {
  padding: 8px 16px;
  border: 1px solid #2d3748;
  text-align: right;
}
.metrics-table th { background: #0f3460; color: #a0aec0; text-align: center; }
.metrics-table td:first-child { text-align: left; color: #a0aec0; }
.perf-chart { flex: 1; min-width: 280px; max-width: 420px; background: #0f3460; border-radius: 10px; padding: 6px; }

/* === Grid de tarjetas === */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  padding: 24px;
}

/* === Tarjeta === */
.card {
  background: #16213e;
  border: 1px solid #2d3748;
  border-radius: 14px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform .2s, box-shadow .2s, border-color .2s;
}
.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px #0007;
  border-color: #667eea55;
}
.card.hidden { display: none; }

.card-header {
  padding: 16px 16px 10px;
  border-bottom: 1px solid #2d374855;
}
.game-title {
  font-size: 1rem;
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 8px;
  line-height: 1.3;
}
.platform-badges { display: flex; flex-wrap: wrap; gap: 4px; }

.card-body { padding: 14px 16px; display: flex; flex-direction: column; gap: 12px; flex: 1; }

/* === Badges genéricos === */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}

/* plataformas */
.plat-ps       { background: #003087; color: #fff; }
.plat-xbox     { background: #107c10; color: #fff; }
.plat-nintendo { background: #e4000f; color: #fff; }
.plat-pc       { background: #2a475e; color: #c6d4df; }

/* descuentos */
.disc-badge { font-size: 0.75rem; padding: 2px 8px; }
.disc-high  { background: #22543d; color: #68d391; border: 1px solid #48bb78; }
.disc-mid   { background: #7b341e; color: #fbd38d; border: 1px solid #ed8936; }
.disc-low   { background: #742a2a; color: #fc8181; border: 1px solid #e53e3e; }

/* best price */
.best-price-badge { background: #744210; color: #f6e05e; border: 1px solid #d69e2e; }

/* === Precio principal === */
.price-meta-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.price-section  { flex: 1; }
.price-row      { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 8px; }
.price-current  { font-size: 1.6rem; font-weight: 800; color: #fff; }
.price-original { font-size: 0.9rem; color: #718096; text-decoration: line-through; }

/* === Tiendas === */
.store-prices { display: flex; flex-wrap: wrap; gap: 6px; }
.store-price-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #0f3460;
  border: 1px solid #2d3748;
  border-radius: 8px;
  padding: 5px 10px;
  font-size: 0.75rem;
  transition: border-color .15s;
  cursor: pointer;
}
.store-price-item:hover { border-color: #667eea; }
.store-logo       { color: #a0aec0; font-size: 0.7rem; }
.store-price-val  { color: #e2e8f0; font-weight: 700; margin-top: 2px; }

/* === Metacritic === */
.mc-block       { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.ms-circle {
  width: 48px; height: 48px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.9rem; font-weight: 800;
  border: 3px solid;
  flex-shrink: 0;
}
.ms-green  { background: #22543d; color: #68d391; border-color: #48bb78; }
.ms-yellow { background: #744210; color: #f6e05e; border-color: #d69e2e; }
.ms-red    { background: #742a2a; color: #fc8181; border-color: #e53e3e; }
.ms-none   { background: #2d3748; color: #718096; border-color: #4a5568; font-size: 0.7rem; }
.user-score { font-size: 0.72rem; color: #a0aec0; }

/* === HLTB === */
.hltb-block { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; }
.hltb-item  { font-size: 0.78rem; color: #a0aec0; background: #0f3460; padding: 3px 10px; border-radius: 12px; }

/* === Estado vacío === */
.empty-state { text-align: center; padding: 60px 24px; color: #4a5568; }
.empty-state h3 { font-size: 1.2rem; margin-bottom: 8px; }

/* === Responsive === */
@media (max-width: 600px) {
  .site-header h1 { font-size: 1.1rem; }
  .cards-grid { padding: 12px; gap: 12px; }
  .metrics-section { margin: 12px 12px 0; }
}
"""


# ─── JavaScript ─────────────────────────────────────────────────────────────

JS = """
(function () {
  const searchInput   = document.getElementById('search-input');
  const platformSel   = document.getElementById('platform-filter');
  const sortSel       = document.getElementById('sort-select');
  const grid          = document.getElementById('cards-grid');
  const countEl       = document.getElementById('results-count');
  const emptyEl       = document.getElementById('empty-state');

  function getCards() {
    return Array.from(grid.querySelectorAll('.card'));
  }

  function filter() {
    const query    = searchInput.value.trim().toLowerCase();
    const platform = platformSel.value.toLowerCase();

    let visible = getCards().filter(card => {
      const title     = card.dataset.title || '';
      const platforms = card.dataset.platforms || '';
      const matchQ    = !query    || title.includes(query);
      const matchP    = !platform || platforms.split(',').some(p => p.trim() === platform);
      return matchQ && matchP;
    });

    // Ocultar todas primero
    getCards().forEach(c => c.classList.add('hidden'));

    // Ordenar visibles
    const sortBy = sortSel.value;
    visible.sort((a, b) => {
      if (sortBy === 'discount')  return parseFloat(b.dataset.discount)  - parseFloat(a.dataset.discount);
      if (sortBy === 'price')     return parseFloat(a.dataset.minPrice)  - parseFloat(b.dataset.minPrice);
      if (sortBy === 'metascore') return parseFloat(b.dataset.metascore) - parseFloat(a.dataset.metascore);
      return 0;
    });

    // Re-append en orden y mostrar
    visible.forEach(c => {
      c.classList.remove('hidden');
      grid.appendChild(c);
    });

    countEl.textContent = visible.length + ' juego(s) encontrado(s)';
    emptyEl.style.display = visible.length === 0 ? 'block' : 'none';
  }

  searchInput.addEventListener('input',  filter);
  platformSel.addEventListener('change', filter);
  sortSel.addEventListener('change',     filter);

  // Inicializar
  filter();
})();
"""


# ─── ensamblaje HTML ────────────────────────────────────────────────────────

def _build_html_string(data: dict) -> str:
    games = data.get("games", [])
    timestamp = data.get("timestamp", "")
    total = data.get("total_games", len(games))

    # Recopilar todas las plataformas para el selector
    all_platforms = sorted({
        p
        for g in games
        for p in g.get("platforms", [])
    })
    platform_options = '<option value="">Todas las plataformas</option>\n'
    for p in all_platforms:
        platform_options += f'<option value="{_esc(p.lower())}">{_esc(p)}</option>\n'

    cards_html = "\n".join(_build_card(g) for g in games)
    metrics_html = _build_metrics(data)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Game Deals Scraper</title>
  <style>{CSS}</style>
</head>
<body>

<header class="site-header">
  <h1>🎮 Game Deals Scraper</h1>
  <p>Generado: {_esc(timestamp)} &nbsp;·&nbsp; {total} juego(s) procesado(s)</p>
</header>

<div class="controls">
  <input  id="search-input"   type="search" placeholder="🔍 Buscar por nombre…">
  <select id="platform-filter">
    {platform_options}
  </select>
  <select id="sort-select">
    <option value="">Ordenar por…</option>
    <option value="discount">Mayor descuento</option>
    <option value="price">Menor precio</option>
    <option value="metascore">Mayor Metascore</option>
  </select>
  <span id="results-count"></span>
</div>

{metrics_html}

<main id="cards-grid" class="cards-grid">
{cards_html}
</main>

<div id="empty-state" class="empty-state" style="display:none">
  <h3>Sin resultados</h3>
  <p>Prueba con otros filtros.</p>
</div>

<script>{JS}</script>
</body>
</html>"""


# ─── función pública ─────────────────────────────────────────────────────────

def build_html(results_path: str = "output/results.json",
               output_path: str = "output/index.html") -> None:
    """
    Lee results_path (JSON) y escribe el HTML en output_path.

    Args:
        results_path: ruta al archivo results.json generado por main.py
        output_path:  ruta de salida del HTML
    """
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html_str = _build_html_string(data)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    print(f"[html_builder] HTML generado → {output_path}")


# Alias para compatibilidad con main.py que llama html_builder.build(data)
def build(data: dict, output_path: str = "output/index.html") -> None:
    """
    Versión que recibe el dict directamente (llamada desde main.py).
    """
    html_str = _build_html_string(data)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_str)
    print(f"[html_builder] HTML generado → {output_path}")


if __name__ == "__main__":
    build_html()