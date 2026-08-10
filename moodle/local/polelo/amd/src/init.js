/**
 * AMD module for the local_polelo plugin - initialises Polelo widget assets
 * on course pages when the plugin requests it via js_init_call.
 */
define(['jquery', 'core/log'], function ($, Log) {
    'use strict';

    var loaded = false;

    /**
     * Load each Polelo widget script once and expose global config.
     *
     * @param {Object} config baseUrl and default grade supplied by the plugin.
     */
    function init(config) {
        if (loaded) {
            return;
        }
        loaded = true;

        window.POLELO_BASE_URL = config.baseUrl || '/';
        window.POLELO_GRADE = config.grade || 8;
        window.POLELO_THEME = 'light';

        var scripts = [
            '/widgets/translation-widget.js',
            '/widgets/quiz-widget.js',
            '/widgets/polelo-embed.js'
        ];
        scripts.forEach(function (src) {
            var script = document.createElement('script');
            script.src = config.baseUrl + src;
            script.async = true;
            document.head.appendChild(script);
        });
        Log.debug('Polelo widget scripts queued.');
    }

    return {
        init: init
    };
});