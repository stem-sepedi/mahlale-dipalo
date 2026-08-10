/* Polelo quiz widget — interactive quiz (questions + scoring).
 *
 * Usage:
 *   <div id="polelo-quiz" data-concept-id="..." data-grade="8" data-theme="light"></div>
 *   <script src="/widgets/quiz-widget.js"></script>
 */
(function (global) {
  "use strict";

  var DEFAULTS = {
    baseUrl: global.POLELO_BASE_URL || "/",
    theme: "light",
    grade: 8,
    count: 5,
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
      success: dark ? "#4ade80" : "#16a34a",
      danger: dark ? "#f87171" : "#dc2626",
    };
  }

  async function fetchQuiz(conceptId, cfg) {
    var base = (cfg.baseUrl || DEFAULTS.baseUrl).replace(/\/$/, "");
    var url = base + "/embed/api/quiz/" + encodeURIComponent(conceptId)
      + "?grade_level=" + encodeURIComponent(cfg.grade || DEFAULTS.grade)
      + "&count=" + encodeURIComponent(cfg.count || DEFAULTS.count);
    var resp = await fetch(url);
    if (!resp.ok) throw new Error("Polelo: quiz unavailable (" + resp.status + ")");
    return resp.json();
  }

  function questionMarkup(q, idx, t) {
    var html = '<div class="polelo-q" data-qid="' + escapeHtml(q.id) + '" style="margin-bottom:1rem">';
    html += '<p style="margin:0 0 .5rem"><strong>' + (idx + 1) + ". " + escapeHtml(q.question_sep) + "</strong></p>";
    var options = q.options || [];
    if (q.question_type === "multiple_choice" && options.length) {
      options.forEach(function (opt, oi) {
        html += '<label style="display:block;padding:.35rem .5rem;border:1px solid ' + t.borderColor + ';border-radius:6px;margin:.3rem 0;cursor:pointer">'
          + '<input type="radio" name="q' + escapeHtml(q.id) + '" value="' + escapeHtml(opt) + '"> '
          + escapeHtml(opt) + "</label>";
      });
    } else {
      html += '<input type="text" class="polelo-input" style="width:100%;padding:.45rem;border:1px solid ' + t.borderColor + ';border-radius:6px;color:' + t.color + ';background:transparent">';
    }
    html += '<div class="polelo-feedback" style="font-size:.85rem;margin-top:.3rem"></div>';
    html += "</div>";
    return html;
  }

  function scoreMarkup(correct, total, t) {
    var pct = total ? Math.round((correct / total) * 100) : 0;
    return '<div style="text-align:center;padding:1rem">'
      + '<div style="font-size:2rem">' + pct + "%</div>"
      + "<div>" + escapeHtml(correct) + " of " + escapeHtml(total) + " correct</div>"
      + "</div>";
  }

  async function renderQuiz(el, cfg) {
    cfg = merge(DEFAULTS, cfg || {});
    var conceptId = cfg.conceptId || cfg.concept || (el && el.getAttribute("data-concept-id"));
    if (!conceptId) {
      if (el) el.innerHTML = '<div class="polelo-widget">Polelo: no concept-id provided.</div>';
      return;
    }
    var t = themeCss(cfg.theme);
    if (el) el.innerHTML = "<div>Loading quiz…</div>";
    try {
      var data = await fetchQuiz(conceptId, cfg);
      var questions = data.questions || [];
      var pool = questions.slice(0, cfg.count || DEFAULTS.count);
      if (!pool.length) {
        if (el) el.innerHTML = '<div class="polelo-widget">No quiz questions available for this concept yet.</div>';
        return;
      }

      var html = '<div class="polelo-widget" style="font-family:system-ui,sans-serif;border:1px solid ' + t.borderColor + ';border-radius:10px;background:' + t.backgroundColor + ';color:' + t.color + ';padding:1rem;max-width:560px">';
      html += '<h3 style="margin:0 0 .75rem">' + escapeHtml(data.concept_name || "Quiz") + "</h3>";
      pool.forEach(function (q, i) { html += questionMarkup(q, i, t); });
      html += '<button type="button" class="polelo-submit" style="width:100%;padding:.6rem;border:none;border-radius:8px;background:' + t.accent + ';color:#fff;cursor:pointer;font-size:1rem">Check answers</button>';
      html += '<div class="polelo-score"></div>';
      html += "</div>";
      if (el) el.innerHTML = html;

      var submit = el.querySelector(".polelo-submit");
      submit.addEventListener("click", function () {
        var correct = 0;
        pool.forEach(function (q) {
          var card = el.querySelector('.polelo-q[data-qid="' + CSS.escape(q.id) + '"]');
          var fb = card.querySelector(".polelo-feedback");
          var answer = "";
          var radio = card.querySelector('input[type="radio"]:checked');
          if (radio) {
            answer = radio.value;
          } else {
            var input = card.querySelector(".polelo-input");
            if (input) answer = input.value;
          }
          var ok = String(answer).trim().toLowerCase() === String(q.correct_answer).trim().toLowerCase();
          if (ok) correct += 1;
          fb.innerHTML = ok
            ? '<span style="color:' + t.success + '">✓ Correct</span>'
            : '<span style="color:' + t.danger + '">✗ Correct answer: ' + escapeHtml(q.correct_answer) + "</span>";
        });
        var scoreEl = el.querySelector(".polelo-score");
        scoreEl.innerHTML = scoreMarkup(correct, pool.length, t);
      });
      if (typeof cfg.onRender === "function") cfg.onRender(el, data, cfg);
    } catch (err) {
      if (el) el.innerHTML = '<div class="polelo-widget">Polelo error: ' + escapeHtml(err.message) + "</div>";
    }
  }

  async function init() {
    var els = document.querySelectorAll("[data-concept-id]");
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.id === "polelo-quiz" || /\bpolelo-quiz\b/.test(el.className)) {
        await renderQuiz(el);
      }
    }
  }

  global.PoleloQuiz = { render: renderQuiz, init: init, DEFAULTS: DEFAULTS };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);