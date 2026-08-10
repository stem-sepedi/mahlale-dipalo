# Polelo Widgets — Embed Guide

Polelo ships lightweight embeddable widgets for cross-origin iframe embedding and
in-page injection. They are the recommended way to surface Sepedi translations and
quizzes inside Moodle (or any website).

---

## 1. Quick start — iframe embeds

The simplest and most robust option: drop a `<iframe>` pointing at the hosted
`/embed` pages. No JavaScript configuration needed.

```html
<iframe src="https://polelo.taip.co.za/embed/translate?concept_id=<uuid>&grade=8"
        width="100%" height="220" style="border:0" loading="lazy"></iframe>
```

```html
<iframe src="https://polelo.taip.co.za/embed/quiz?concept_id=<uuid>&grade=8&count=5"
        width="100%" height="420" style="border:0" loading="lazy"></iframe>
```

### Parameters

| Page        | Param       | Default | Description                              |
|-------------|-------------|---------|------------------------------------------|
| /embed/translate | `concept_id` | —   | Concept UUID (required)                  |
|             | `grade`     | 8       | Grade level for the explanation          |
|             | `theme`     | light   | `light` or `dark`                        |
|             | `lang`      | sepedi  | `sepedi` or `english` initial language   |
| /embed/quiz | `concept_id` | —      | Concept UUID (required)                  |
|             | `grade`     | 8       | Difficulty grade                         |
|             | `count`     | 5       | Number of questions (≤20)                |

The pages are styled to match the `theme`, and respect
`EMBED_ALLOWED_ORIGINS` for `frame-ancestors` CSP.

## 2. JS widgets (in-page)

Three scripts are served from `/widgets`:

| Script                    | Purpose                                        |
|---------------------------|------------------------------------------------|
| `translation-widget.js`   | Fetch + render a Sepedi translation card       |
| `quiz-widget.js`          | Interactive quiz with instant scoring          |
| `polelo-embed.js`         | Auto-detects `[polelo-*]` shortcodes in HTML   |

Global config can be set before the scripts load:

```html
<script>
  window.POLELO_BASE_URL = 'https://polelo.taip.co.za';
  window.POLELO_GRADE = 8;
  window.POLELO_THEME = 'light';
</script>
<script src="https://polelo.taip.co.za/widgets/translation-widget.js" defer></script>
<script src="https://polelo.taip.co.za/widgets/quiz-widget.js" defer></script>
<script src="https://polelo.taip.co.za/widgets/polelo-embed.js" defer></script>
```

### Data-attribute usage

```html
<div id="polelo-translate"
     data-concept-id="<uuid>" data-grade="8" data-theme="dark"></div>

<div id="polelo-quiz"
     data-concept-id="<uuid>" data-grade="8" data-count="5"></div>
```

The widgets auto-initialise on `DOMContentLoaded`.

### Programmatic API

```js
PoleloTranslate.render('#polelo-translate', {
  conceptId: '<uuid>', grade: 8, theme: 'light', lang: 'sepedi',
});

PoleloQuiz.render('#polelo-quiz', {
  conceptId: '<uuid>', grade: 8, count: 5, theme: 'dark',
});
```

## 3. Shortcode loader («polelo-embed»)

`polelo-embed.js` scans elements matching `.polelo-embed` or `[data-polelo-embed]`
and replaces shortcodes with live widget containers:

```html
<div class="polelo-embed">
  [polelo-translate concept_id="<uuid>" grade="8" theme="light"]
  [polelo-quiz concept_id="<uuid>" grade="8" count="5"]
</div>
```

Supported attributes on each shortcode: `concept_id` (or `id`), `grade`, `theme`,
`count` (quiz only).

## 4. Widget configuration

Widget behaviour is controlled by `data-*` attributes, per-render options, or the
global `window.POLELO_*` variables:

| Option          | Values        | Represents                                   |
|-----------------|---------------|----------------------------------------------|
| `baseUrl`       | URL           | Polelo server origin (default `/`)           |
| `grade`         | 0–12          | Grade level for explanation/quiz difficulty   |
| `theme`         | light, dark   | Colour scheme                               |
| `lang`          | sepedi, english | Initial render language                   |
| `count`         | 1–20          | Number of quiz questions                     |
| `hideDefinition`| true, false   | Hide the English definition in translation card |

## 5. Underlying public API

The widgets talk to unauthenticated learner endpoints (rate-limited as `learner`):

- `GET /embed/api/translate/{concept_id}?grade=8`
- `GET /embed/api/quiz/{concept_id}?grade_level=8&count=5`

Only **published** concepts and **approved** translations/explanations are
returned.

## 6. CSP & CORS

Embed responses set:

- `Content-Security-Policy: ...; frame-ancestors <origins>;`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` (when `frame-ancestors` is not `*`)

`EMBED_ALLOWED_ORIGINS` (comma-separated origins or `*`) controls which sites may
frame the `/embed/*` pages. The FastAPI `CORSMiddleware` allows the widget API
calls from `CORS_ORIGINS`.

## 7. Webhooks (for sending events back)

The Moodle plugin (`local_polelo`) pushes learner events back to Polelo via
HMAC-signed webhooks so results land in the polelo tables:

| Event            | Trigger               | Effect                                         |
|------------------|-----------------------|------------------------------------------------|
| enrolment        | Course enrolment      | Course sync marked pending (bulk translation)  |
| activity         | Module completion     | concepts → `mqtt_jobs` mastery events          |
| quiz-submission  | Quiz attempt graded   | score stored for course/concept/user           |

Signing: `X-Moodle-Timestamp` (Unix) plus `X-Moodle-Signature` =
`HMAC_SHA256(<timestamp>.<raw-body>)` using `MoodleWebhookSecret`. Events are
queued to the `moodle.webhook` MQTT topic and processed asynchronously by
`src/services/moodle_sync.py`.