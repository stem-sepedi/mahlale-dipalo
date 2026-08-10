<?php
// Language strings for the local_polelo plugin - Polelo STEM Sepedi translation layer.
// This file is part of Moodle: https://moodle.org/

$string['pluginname'] = 'Polelo STEM Sepedi';
$string['polelo:view'] = 'View Polelo content widgets';
$string['polelo:manage'] = 'Manage Polelo integration settings';

$string['polelo_url'] = 'Polelo server URL';
$string['polelo_url_desc'] = 'Base URL of your Polelo instance (e.g. https://polelo.taip.co.za)';
$string['api_key'] = 'Polelo API key';
$string['api_key_desc'] = 'The API key issued by Polelo for this Moodle instance (X-Moodle-Key)';
$string['mqtt_broker'] = 'MQTT broker host';
$string['mqtt_broker_desc'] = 'Host of the MQTT broker for real-time translation requests';
$string['mqtt_port'] = 'MQTT broker port';
$string['mqtt_port_desc'] = 'TCP port of the MQTT broker (default 1883)';
$string['default_grade'] = 'Default grade level';
$string['default_grade_desc'] = 'Grade level used when rendering Polelo widgets and quizzes';
$string['webhook_secret'] = 'Webhook secret';
$string['webhook_secret_desc'] = 'Shared secret used to sign webhook events sent to Polelo (HMAC-SHA256)';

$string['polelo_transport_error'] = 'Failed to reach the Polelo server: {$a}';
$string['polelo_bad_response'] = 'The Polelo server returned an unexpected response: {$a}';
$string['polelo_tokenerror'] = 'Polelo could not obtain an LTI Advantage access token';

$string['widget_translate'] = 'Polelo translation';
$string['widget_quiz'] = 'Polelo quiz';
$string['synchronise'] = 'Synchronise with Polelo';
$string['sync_success'] = 'Synchronisation complete: {$a->concepts} concepts, {$a->quizzes} quizzes pulled.';
$string['sync_failed'] = 'Synchronisation with Polelo failed: {$a}';

$string['settingheader'] = 'Polelo integration settings';