/* Polelo embed loader — auto-detect shortcodes in Moodle HTML and bootstrap widgets.
 *
 * Detects:
 *   [polelo-translate concept_id="..."] and [polelo-translate id="..."] — inline translation widget
 *   [polelo-quiz concept_id="..."] / [polelo-translate][/polelo-translate] block form
 *
 * Elements using data-* attributes are still auto-initialised by each widget script;
 * this file only handles the shortcode text form embedded in page HTML.
 */
(function (global) {
  "use strict";

  function extractShortcodes(html) {
    var out = [];
    var re = /\[(polelo-translate|polelo-quiz)\s+([^\]]*)\](\[(?:[^\]]*)\])?/g;
    var m;
    while ((m = re.exec(html)) !== null) {
      var attrs = {};
      var raw = " " + m[2] + " ";
      var attrRe = /([a-zA-Z_:][a-zA-Z0-9_:.-]*)\s*=\s*"([^"]*)"/g;
      var am;
      while ((am = attrRe.exec(raw)) !== null) {
        attrs[am[1]] = am[2];
      }
      out.push({ widget: m[1], attrs: attrs, index: m.index, matched: m[0] });
    }
    return out;
  }

  function renderQuizInto(container, attrs) {
    if (!global.PoleloQuiz) {
      console.error("Polelo: quiz-widget.js must be loaded before polelo-embed.js");
      return;
    }
    var div = document.createElement("div");
    div.className = "polelo-quiz";
    div.id = "polelo-quiz";
    div.setAttribute("data-concept-id", attrs.concept_id || attrs.id || "");
    div.setAttribute("data-grade", attrs.grade || global.POLELO_GRADE || 8);
    container.appendChild(div);
    global.PoleloQuiz.render(div, {
      conceptId: attrs.concept_id || attrs.id,
      grade: attrs.grade || global.POLELO_GRADE || 8,
      theme: attrs.theme || global.POLELO_THEME || "light",
      baseUrl: global.POLELO_BASE_URL || "/",
    });
  }

  function renderTranslateInto(container, attrs) {
    if (!global.PoleloTranslate) {
      console.error("Polelo: translation-widget.js must be loaded before polelo-embed.js");
      return;
    }
    var div = document.createElement("div");
    div.className = "polelo-translate";
    div.id = "polelo-translate";
    div.setAttribute("data-concept-id", attrs.concept_id || attrs.id || "");
    div.setAttribute("data-grade", attrs.grade || global.POLELO_GRADE || 8);
    div.setAttribute("data-theme", attrs.theme || global.POLELO_THEME || "light");
    container.appendChild(div);
    return global.PoleloTranslate.render(div, {
      conceptId: attrs.concept_id || attrs.id,
      grade: attrs.grade || global.POLELO_GRADE || 8,
      theme: attrs.theme || global.POLELO_THEME || "light",
      baseUrl: global.POLELO_BASE_URL || "/",
    });
  }

  function buildWidget(attrs) {
    var holder = document.createElement("div");
    if (attrs.widget === "polelo-translate") {
      renderTranslateInto(holder, attrs);
    } else {
      renderQuizInto(holder, attrs);
    }
    return holder.outerHTML;
  }

  function scan() {
    var containers = document.querySelectorAll(".polelo-embed, [data-polelo-embed]");
    containers.forEach(function (container) {
      if (container.getAttribute("data-polelo-processed")) return;
      container.setAttribute("data-polelo-processed", "1");
      var html = container.innerHTML;
      var tokens = extractShortcodes(html);
      var parts = [];
      var cursor = 0;
      tokens.forEach(function (token) {
        parts.push(html.slice(cursor, token.index));
        parts.push(buildWidget(token.attrs));
        cursor = token.index + token.matched.length;
      });
      parts.push(html.slice(cursor));
      if (tokens.length) container.innerHTML = parts.join("");
    });
  }

  global.PoleloEmbed = { extractShortcodes: extractShortcodes, scan: scan };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
})(window);