<?php
// Settings for local_polelo - Polelo STEM Sepedi translation layer.
// This file is part of Moodle: https://moodle.org/

defined('MOODLE_INTERNAL') || die();

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_polelo', get_string('pluginname', 'local_polelo'));
    $ADMIN->add('localplugins', $settings);

    $settings->add(new admin_setting_configtext(
        'local_polelo/polelo_url',
        get_string('polelo_url', 'local_polelo'),
        get_string('polelo_url_desc', 'local_polelo'),
        'https://polelo.taip.co.za',
        PARAM_URL
    ));

    $settings->add(new admin_setting_configpasswordunmask(
        'local_polelo/api_key',
        get_string('api_key', 'local_polelo'),
        get_string('api_key_desc', 'local_polelo'),
        ''
    ));

    $settings->add(new admin_setting_configtext(
        'local_polelo/mqtt_broker',
        get_string('mqtt_broker', 'local_polelo'),
        get_string('mqtt_broker_desc', 'local_polelo'),
        'localhost',
        PARAM_HOST
    ));

    $settings->add(new admin_setting_configtext(
        'local_polelo/mqtt_port',
        get_string('mqtt_port', 'local_polelo'),
        get_string('mqtt_port_desc', 'local_polelo'),
        '1883',
        PARAM_INT
    ));

    $settings->add(new admin_setting_configselect(
        'local_polelo/default_grade',
        get_string('default_grade', 'local_polelo'),
        get_string('default_grade_desc', 'local_polelo'),
        8,
        array(5 => 'Grade 5', 7 => 'Grade 7', 8 => 'Grade 8', 9 => 'Grade 9', 10 => 'Grade 10', 11 => 'Grade 11', 12 => 'Grade 12')
    ));

    $settings->add(new admin_setting_configtext(
        'local_polelo/webhook_secret',
        get_string('webhook_secret', 'local_polelo'),
        get_string('webhook_secret_desc', 'local_polelo'),
        '',
        PARAM_ALPHANUMEXT
    ));
}