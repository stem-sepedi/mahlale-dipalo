<?php
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

defined('MOODLE_INTERNAL') || die();

require_once($CFG->libdir . '/filelib.php');
require_once(__DIR__ . '/../../../../config.php');

/**
 * polelo_api_client - thin HTTP client for the Polelo REST content API.
 *
 * Used to pull concept feeds, quiz banks and course sync data from Polelo,
 * and to push completion/mastery results back.
 */
class polelo_api_client {
    /** @var string Base URL of the Polelo instance (no trailing slash). */
    protected $baseurl;
    /** @var string API key presented in the X-Moodle-Key header. */
    protected $apikey;

    /**
     * Create a client from the plugin config (or explicit values).
     *
     * @param string|null $baseurl
     * @param string|null $apikey
     */
    public function __construct($baseurl = null, $apikey = null) {
        $config = get_config('local_polelo');
        $this->baseurl = rtrim($baseurl ?: (isset($config->polelo_url) ? $config->polelo_url : ''), '/');
        $this->apikey = $apikey ?: (isset($config->api_key) ? $config->api_key : '');
    }

    /**
     * Perform a GET request against the Polelo API.
     *
     * @param string $path e.g. /moodle/concepts
     * @param array $params query string params
     * @return array decoded JSON response
     * @throws moodle_exception on transport or HTTP error.
     */
    public function get($path, $params = array()) {
        $url = $this->baseurl . $path;
        if (!empty($params)) {
            $url .= '?' . http_build_query($params);
        }
        $respond = $this->request($url, 'GET');
        return $this->decode($respond);
    }

    /**
     * Perform a POST request against the Polelo API with a JSON body.
     *
     * @param string $path
     * @param array $body
     * @return array decoded JSON response
     * @throws moodle_exception
     */
    public function post($path, $body = array()) {
        if (empty($body['timestamp'])) {
            $body['timestamp'] = date('c');
        }
        $signature = hash_hmac(
            'sha256',
            $this->timestamped_payload($body),
            $this->webhook_secret()
        );
        $respond = $this->request(
            $this->baseurl . $path,
            'POST',
            json_encode($body),
            array(
                'Content-Type: application/json',
                'X-Moodle-Signature: ' . $signature,
                'X-Moodle-Timestamp: ' . $body['timestamp'],
            )
        );
        return $this->decode($respond);
    }

    /**
     * Push a quiz-submission master/score event to Polelo.
     *
     * @param string $courseid Moodle course id.
     * @param string $conceptid Polelo concept UUID.
     * @param int $userid Moodle user id.
     * @param float $scorepct 0..100
     * @return array
     */
    public function push_quiz_submission($courseid, $conceptid, $userid, $scorepct) {
        return $this->post('/moodle/webhooks/quiz-submission', array(
            'event_type' => 'quiz-submission',
            'course_id' => (int)$courseid,
            'user_id' => (int)$userid,
            'score_pct' => (float)$scorepct,
            'concept_id' => $conceptid,
            'instance_url' => $this->baseurl,
        ));
    }

    /**
     * Push a course enrolment event to Polelo (triggers bulk translation).
     *
     * @param int $courseid
     * @return array
     */
    public function push_enrolment($courseid) {
        return $this->post('/moodle/webhooks/enrolment', array(
            'event_type' => 'enrolment',
            'course_id' => (int)$courseid,
            'instance_url' => $this->baseurl,
        ));
    }

    /**
     * Fetch the concept feed for a course.
     *
     * @param string $courseid
     * @return array decoded { concepts, total, ... }
     */
    public function course_sync($courseid) {
        return $this->get('/moodle/courses/' . urlencode($courseid) . '/sync');
    }

    /**
     * Internal curl helper.
     */
    protected function request($url, $method = 'GET', $postdata = null, $headers = array()) {
        $curl = new \curl();
        $headers = array_merge(array(
            'X-Moodle-Key: ' . $this->apikey,
        ), $headers);

        if ($method === 'GET') {
            $raw = $curl->get($url, array(), array('CUSTOMREQUEST' => 'GET', 'HEADER' => $this->curl_headers($headers)));
        } else {
            $raw = $curl->post($url, $postdata, array('CUSTOMREQUEST' => 'POST', 'HEADER' => $this->curl_headers($headers)));
        }
        if ($curl->errno) {
            throw new moodle_exception('polelo_transport_error', 'local_polelo', '', $curl->error);
        }
        return $raw;
    }

    protected function curl_headers($headers) {
        $out = '';
        foreach ($headers as $h) {
            $out .= $h . "\r\n";
        }
        return $out;
    }

    /**
     * Decode a JSON or XML response body.
     */
    protected function decode($raw) {
        $json = json_decode($raw, true);
        if (is_array($json)) {
            return $json;
        }
        $xml = simplexml_load_string($raw);
        if ($xml !== false) {
            return json_decode(json_encode($xml), true);
        }
        throw new moodle_exception('polelo_bad_response', 'local_polelo', '', $raw);
    }

    protected function webhook_secret() {
        $config = get_config('local_polelo');
        return isset($config->webhook_secret) ? $config->webhook_secret : '';
    }

    protected function timestamped_payload($body) {
        return $body['timestamp'] . '.' . json_encode($body);
    }
}