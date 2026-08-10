<?php
// polelo_widgets.php - helper that builds Polelo widget markup for course pages.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

namespace local_polelo;

defined('MOODLE_INTERNAL') || die();

/**
 * Builds embed markup for Polelo translation and quiz widgets.
 */
class polelo_widgets {

    /**
     * Inject a translation widget node into the course navigation.
     *
     * @param \navigation_node $navigation
     * @param \stdClass $course
     * @param \context_course $context
     * @return void
     */
    public static function inject_course_widgets($navigation, $course, $context) {
        $broken = false; // No-op when called via legacy signature; real work happens on the page.
    }

    /**
     * Render a translation widget container for a concept.
     *
     * @param string $conceptid Polelo concept UUID.
     * @param int $grade Default grade level.
     * @param string $theme Widget theme (light|dark).
     * @return string HTML snippet with data attributes the JS widget picks up.
     */
    public static function translation_widget($conceptid, $grade = 8, $theme = 'light') {
        $safe = (int)$grade;
        $escaped = s($conceptid);
        $themesafe = in_array($theme, array('light', 'dark')) ? $theme : 'light';
        return '<div class="polelo-translate" id="polelo-translate" data-concept-id="' . $escaped
            . '" data-grade="' . $safe . '" data-theme="' . $themesafe . '"></div>';
    }

    /**
     * Render a quiz widget container for a concept.
     *
     * @param string $conceptid Polelo concept UUID.
     * @param int $grade Default grade level.
     * @param int $count Number of questions.
     * @param string $theme Widget theme (light|dark).
     * @return string HTML snippet.
     */
    public static function quiz_widget($conceptid, $grade = 8, $count = 5, $theme = 'light') {
        $safe = (int)$grade;
        $cnt = (int)$count;
        $escaped = s($conceptid);
        $themesafe = in_array($theme, array('light', 'dark')) ? $theme : 'light';
        return '<div class="polelo-quiz" id="polelo-quiz" data-concept-id="' . $escaped
            . '" data-grade="' . $safe . '" data-count="' . $cnt . '" data-theme="' . $themesafe . '"></div>';
    }

    /**
     * Render an iframe embed of the hosted translation page (fallback when JS widgets unavailable).
     *
     * @param string $conceptid Polelo concept UUID.
     * @param int $grade Default grade level.
     * @param string $baseurl Polelo base URL.
     * @return string iframe HTML.
     */
    public static function translation_iframe($conceptid, $grade = 8, $baseurl = '') {
        $base = rtrim($baseurl, '/');
        $url = $base . '/embed/translate?concept_id=' . urlencode($conceptid) . '&grade=' . (int)$grade;
        $height = 220;
        return '<iframe src="' . $url . '" width="100%" height="' . $height . '"'
            . ' style="border:0" title="Polelo translation" loading="lazy"></iframe>';
    }

    /**
     * Render an iframe embed of the hosted quiz page (fallback when JS widgets unavailable).
     *
     * @param string $conceptid Polelo concept UUID.
     * @param int $grade Default grade level.
     * @param int $count Number of questions.
     * @param string $baseurl Polelo base URL.
     * @return string iframe HTML.
     */
    public static function quiz_iframe($conceptid, $grade = 8, $count = 5, $baseurl = '') {
        $base = rtrim($baseurl, '/');
        $url = $base . '/embed/quiz?concept_id=' . urlencode($conceptid) . '&grade=' . (int)$grade . '&count=' . (int)$count;
        $height = 420;
        return '<iframe src="' . $url . '" width="100%" height="' . $height . '"'
            . ' style="border:0" title="Polelo quiz" loading="lazy"></iframe>';
    }
}