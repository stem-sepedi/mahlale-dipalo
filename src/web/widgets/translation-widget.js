/* Polelo translation widget — lightweight fetch + render.
 *
 * Usage:
 *   <div id="polelo-translate" data-concept-id="..." data-theme="dark" data-grade="8" data-lang="sepedi"></div>
 *   <script src="/widgets/translation-widget.js"></script>
 *
 * Or programmatically:
 *   PoleloTranslate.render("#polelo-translate", { conceptId, theme, grade, lang });
 */
(function (global) {
  "use strict";

  var DEFAULTS = {
    baseUrl: global.POLELO_BASE_URL || "/",
    theme: "light",
    grade: 8,
    lang: "sepedi",
    hideDefinition: false,
  };

  function merge(base, overlay) {
    var out = {};
    for (var k in base) out[k] = base[k];
    for (var k2 in overlay) if (overlay[k2] !== undefined) out[k2] = overlay[k2];
    return out;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function themeCss(theme) {
    var dark = theme === "dark";
    return {
      backgroundColor: dark ? "#1e293b" : "#ffffff",
      color: dark ? "#e2e8f0" : "#0f172a",
      borderColor: dark ? "#334155" : "#e2e8f0",
      accent: dark ? "#38bdf8" : "#2563eb",
    };
  }

  function render(payload, cfg, lang) {
    var t = themeCss(cfg.theme);
    var showSepedi = lang !== "english";
    var term = showSepedi ? payload.sepedi_term || payload.name_en : payload.name_en;
    var explanation = showSepedi
      ? payload.explanation_sep || payload.explanation_en
      : payload.explanation_en || payload.explanation_sep;

    var html = "";
    html += '<div class="polelo-widget" style="font-family:system-ui,sans-serif;border:1px solid ' + t.borderColor + ';border-radius:10px;background:' + t.backgroundColor + ';color:' + t.color + ';padding:1rem;max-width:560px">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">';
    html += '<strong style="font-size:1.05rem">' + escapeHtml(term) + "</strong>";
    html += '<button type="button" class="polelo-lang-btn" style="font-size:.75rem;border:1px solid ' + t.borderColor + ';background:transparent;color:' + t.color + ';border-radius:99px;padding:.2rem .7rem;cursor:pointer">'
      + (showSepedi ? "English" : "Sepedi") + "</button>";
    html += "</div>";
    if (payload.domain) {
      html += '<div style="font-size:.75rem;opacity:.7;margin-bottom:.25rem">' + escapeHtml(payload.domain) + " · Grade " + escapeHtml(cfg.grade) + "</div>";
    }
    if (!cfg.hideDefinition && payload.definition_en) {
      html += '<p style="font-size:.9rem;opacity:.85;margin:.25rem 0">' + escapeHtml(payload.definition_en) + "</p>";
    }
    if (explanation) {
      html += '<div class="polelo-explanation" style="margin-top:.5rem;padding:.6rem;border-left:3px solid ' + t.accent + ';font-size:.9rem">'
        + escapeHtml(explanation) + "</div>";
    }
    html += "</div>";
    return html;
  }

  async function fetchConcept(conceptId, cfg) {
    var base = (cfg.baseUrl || DEFAULTS.baseUrl).replace(/\/$/, "");
    var url = base + "/embed/api/translate/" + encodeURIComponent(conceptId) + "?grade=" + encodeURIComponent(cfg.grade || DEFAULTS.grade);
    var resp = await fetch(url);
    if (!resp.ok) throw new Error("Polelo: concept not found (" + resp.status + ")");
    return resp.json();
  }

  async function translate(el, callerCfg) {
    var cfg = merge(DEFAULTS, callerCfg || {});
    if (typeof el === "string") el = document.querySelector(el);
    var elCfg = el ? {
      theme: el.getAttribute("data-theme"),
      grade: el.getAttribute("data-grade"),
      lang: el.getAttribute("data-lang"),
      hideDefinition: el.getAttribute("data-hide-definition"),
      baseUrl: el.getAttribute("data-base-url"),
    } : {};
    cfg = merge(cfg, elCfg);
    var conceptId = cfg.conceptId || cfg.concept || (el && el.getAttribute("data-concept-id"));
    if (!conceptId) {
      if (el) el.innerHTML = '<div class="polelo-widget">Polelo: no concept-id provided.</div>';
      return;
    }
    var lang = cfg.lang || DEFAULTS.lang;
    if (el) el.innerHTML = "<div>Loading…</div>";
    try {
      var payload = await fetchConcept(conceptId, cfg);
      if (el) el.innerHTML = render(payload, cfg, lang);
      bindToggle(el, payload, cfg);
      if (typeof cfg.onRender === "function") cfg.onRender(el, payload, cfg);
    } catch (err) {
      if (el) el.innerHTML = '<div class="polelo-widget">Polelo error: ' + escapeHtml(err.message) + "</div>";
    }
  }

  function bindToggle(el, payload, cfg) {
    if (!el) return;
    var btn = el.querySelector(".polelo-lang-btn");
    if (!btn) return;
    var lang = cfg.lang || DEFAULTS.lang;
    btn.addEventListener("click", function () {
      lang = lang === "sepedi" ? "english" : "sepedi";
      el.innerHTML = render(payload, cfg, lang);
      bindToggle(el, payload, cfg);
    });
  }

  async function init() {
    var els = document.querySelectorAll("[data-concept-id]");
    for (var i = 0; i < els.length; i++) {
      if (elIsWidget(els[i])) await translate(els[i]);
    }
  }

  function elIsWidget(el) {
    return el.id === "polelo-translate" || /\bpolelo-translate\b/.test(el.className);
  }

  global.PoleloTranslate = {
    render: translate,
    init: init,
    DEFAULTS: DEFAULTS,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);