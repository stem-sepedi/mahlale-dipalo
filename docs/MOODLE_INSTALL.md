# Moodle Install Guide

Step-by-step guide to installing the `local_polelo` plugin and connecting a Moodle
instance to your Polelo STEM Sepedi translation layer.

Tested against Moodle 4.1+ (LTS).

---

## 1. Prerequisites

- A running Polelo instance (see `DEPLOYMENT_GUIDE.md` / `docker-compose.yml`).
- A Moodle 4.1+ installation with access to the file system (filesystem access
  to `local/` and the CLI `php` binary).
- An API key for your Moodle instance, configured on the Polelo server:

  ```env
  # Polelo .env
  MOODLE_API_KEYS=<your-instance-key>
  MoodleApiKey=<the-plugin-key-for-this-moodle>
  MoodleWebhookSecret=<shared-webhook-secret>
  MoodleLtiSecret=<lti-jwt-signing-secret>
  ```

> **Note:** The keys are issued by the Polelo operator. `MoodleApiKey` is what the
> plugin presents in the `X-Moodle-Key` header when calling the content API.

## 2. Install the plugin

Copy the plugin into the Moodle code tree:

```bash
cp -r <repo>/moodle/local/polelo <moodle-root>/local/polelo
```

Then trigger the install from the CLI or web installer:

```bash
cd <moodle-root>
sudo -u www-data php admin/cli/upgrade.php
```

The upgrade step installs the XMLDB tables (`local_polelo_courses`,
`local_polelo_events`) defined in `db/install.xml`.

## 3. Configure the plugin

1. Log in to Moodle as an admin.
2. Visit **Site administration → Plugins → Local plugins → Polelo STEM Sepedi**.
3. Fill in the settings:

   | Setting          | Value                                              |
   |------------------|----------------------------------------------------|
   | Polelo server URL| `https://polelo.taip.co.za` (your Polelo base URL)  |
   | Polelo API key   | The `MoodleApiKey` value from step 1               |
   | MQTT broker host | Host of the MQTT broker (usually the Polelo server)|
   | MQTT port        | `1883`                                             |
   | Default grade    | `8` (adjust per school)                            |
   | Webhook secret   | The `MoodleWebhookSecret` value from step 1        |

## 4. Grant capabilities

The plugin ships with two capabilities:

- `local/polelo:view` — granted to students/teachers by default. Allows widgets
  and the sync landing page.
- `local/polelo:manage` — system-level. Allows configuring the plugin.

Assign roles as needed under **Site administration → Users → Permissions →
Define roles** or edit the archetype defaults in `db/access.php`.

## 5. Verify the connection

1. Open the plugin landing page: `https://<moodle>/local/polelo/index.php?courseid=2`
2. Press **Synchronise with Polelo**.

If configured correctly you should see the pulled concept/quiz totals. Check the
Moodle error log if the sync fails.

## 6. Embedding widgets in courses

On any course section, add a label / HTML block containing a shortcode:

```html
<div class="polelo-embed">
    [polelo-translate concept_id="<concept-uuid>"]</div>
<div class="polelo-embed">
    [polelo-quiz concept_id="<concept-uuid>" grade="8" count="5"]
</div>
```

The `polelo-embed.js` loader (injected by `local_polelo_before_footer`) replaces
these with live widgets. You can also copy the generated iframe markup from
`classes/polelo_widgets.php::translation_iframe()`.

## 7. LTI 1.3 tool provision (optional)

Beyond simple widgets you can expose a concept as an LTI 1.3 tool assignment:

1. Create an external tool activity in a Moodle course.
2. Configure it with tool URL `https://polelo.taip.co.za/embed/translate` and the
   public/private client id documented in `docs/MOODLE_API.md`.
3. The plugin signs the launch JWT with `MoodleLtiSecret`; grade passback works
   via `lti/grades.php` for quiz/assignment results.

## 8. Uninstall

```bash
cd <moodle-root>
sudo -u www-data php admin/cli/uninstall_plugin.php --plugin=local_polelo
```

## Troubleshooting

| Symptom                              | Likely cause                                       |
|--------------------------------------|----------------------------------------------------|
| Sync returns transport error         | Wrong `polelo_url` or the app is unreachable       |
| 401/403 from Polelo API              | Wrong/missing API key                              |
| Widgets render "no concept-id"       | Shortcode missing `concept_id`                     |
| Widgets never load scripts           | MQTT host unreachable is unrelated; check the browser console and `EMBED_ALLOWED_ORIGINS` CSP on the Polelo side |