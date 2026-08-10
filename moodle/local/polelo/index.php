<?php
// index.php - plugin landing page showing sync status and a manual sync button.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

require_once(__DIR__ . '/../../config.php');
require_once(__DIR__ . '/classes/polelo_api_client.php');

$courseid = optional_param('courseid', 0, PARAM_INT);
$sync = optional_param('sync', 0, PARAM_INT);

require_login();
$context = context_system::instance();
require_capability('local/polelo:view', $context);

$url = new moodle_url('/local/polelo/index.php', array('courseid' => $courseid));
$PAGE->set_url($url);
$PAGE->set_context($context);
$PAGE->set_title(get_string('pluginname', 'local_polelo'));
$PAGE->set_heading(get_string('pluginname', 'local_polelo'));

$syncresult = null;
if ($sync && $courseid) {
    require_sesskey();
    $client = new polelo_api_client();
    try {
        $data = $client->course_sync($courseid);
        $syncresult = array(
            'ok' => true,
            'concepts' => (int)$data['total_concepts'],
            'quizzes' => (int)$data['total_quizzes'],
        );
    } catch (moodle_exception $e) {
        $syncresult = array('ok' => false, 'error' => $e->getMessage());
    }
}

echo $OUTPUT->header();

echo html_writer::tag('h2', get_string('pluginname', 'local_polelo'));
echo html_writer::start_div('polelo-status');

if ($syncresult) {
    if ($syncresult['ok']) {
        echo $OUTPUT->notification(
            get_string('sync_success', 'local_polelo', array(
                'concepts' => $syncresult['concepts'],
                'quizzes' => $syncresult['quizzes'],
            )),
            'notifysuccess'
        );
    } else {
        echo $OUTPUT->notification(
            get_string('sync_failed', 'local_polelo', $syncresult['error']),
            'notifyerror'
        );
    }
}

$syncurl = new moodle_url('/local/polelo/index.php', array('courseid' => $courseid, 'sync' => 1, 'sesskey' => sesskey()));
echo $OUTPUT->single_button($syncurl, get_string('synchronise', 'local_polelo'), 'get');
echo html_writer::end_div();

echo $OUTPUT->footer();