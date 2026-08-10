<?php
// Hook callbacks for local_polelo - Polelo STEM Sepedi translation layer.
// This file is part of Moodle: https://moodle.org/

defined('MOODLE_INTERNAL') || die();

/**
 * Inject Polelo widgets into course pages and set up the page requirements.
 *
 * @param navigation_node $navigation
 * @param stdClass $course
 * @param context_course $context
 * @return void
 */
function local_polelo_extend_navigation_course($navigation, $course, $context) {
    if (has_capability('local/polelo:view', $context)) {
        require_once(__DIR__ . '/classes/polelo_widgets.php');
        \local_polelo\polelo_widgets::inject_course_widgets($navigation, $course, $context);
    }
}

/**
 * Extend the settings navigation for the plugin.
 *
 * @param settings_navigation $navigation
 * @param context $context
 * @return void
 */
function local_polelo_extend_settings_navigation($navigation, $context) {
    if (has_capability('local/polelo:manage', $context)) {
        $url = new moodle_url('/local/polelo/index.php');
        $navigation->add(
            get_string('pluginname', 'local_polelo'),
            $url,
            navigation_node::TYPE_SETTING,
            null,
            'local_polelo',
            new pix_icon('i/settings', '')
        );
    }
}

/**
 * Ensure the plugin's public wrapper scripts get the widget assets on every page.
 *
 * @param moodle_page $page
 * @return void
 */
function local_polelo_before_footer() {
    global $PAGE;

    if (strpos($PAGE->url->get_path(), '/course/view.php') === false
        && strpos($PAGE->url->get_path(), '/mod/') === false) {
        return;
    }

    $config = get_config('local_polelo');
    if (empty($config->polelo_url)) {
        return;
    }

    $widgets = array(
        '/widgets/translation-widget.js',
        '/widgets/quiz-widget.js',
        '/widgets/polelo-embed.js',
    );
    $base = rtrim($config->polelo_url, '/');
    foreach ($widgets as $w) {
        $PAGE->requires->js(new moodle_url($base . $w), true);
    }

    $PAGE->requires->js_init_call(
        'M.local_polelo.init',
        array(
            'baseUrl' => $base,
            'grade' => isset($config->default_grade) ? (int)$config->default_grade : 8,
        ),
        true
    );
}

/**
 * Register an AMD module for the plugin so requirejs_js can resolve it when included.
 */
function local_polelo_after_require_js() {
    global $CFG;
    // Placeholder hook - widget assets are loaded via <script> tags in before_footer().
}