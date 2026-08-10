<?php
// grades.php - assignment grade passback to the course (LTI Advantage).
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

defined('MOODLE_INTERNAL') || die();

require_once(__DIR__ . '/jwt_grant.php');

/**
 * polelo_lti_grades - sends quiz/assignment results back to the Moodle gradebook
 * via the LTI Advantage lineitem + SCORE result endpoints.
 */
class polelo_lti_grades {

    /**
     * Create a lineitem on the platform for a concept assignment.
     *
     * @param string $lineitemurl Platform lineitem create URL from the launch claims.
     * @param string $conceptid
     * @param string $name
     * @param float $maxscore
     * @param string $selectedgrade (LTI 1.3 evidence: a JSON Activity Progress)
     * @return array decoded platform response.
     */
    public function create_lineitem($lineitemurl, $conceptid, $name, $maxscore = 100.0) {
        $payload = array(
            'scoreMaximum' => (float)$maxscore,
            'label' => 'Polelo: ' . $name,
            'resourceId' => 'polelo:' . $conceptid,
            'tag' => 'polelo-sepedi',
        );
        $token = $this->access_token($lineitemurl);
        $curl = new \curl();
        $raw = $curl->post(
            $lineitemurl,
            json_encode($payload),
            array(
                'CUSTOMREQUEST' => 'POST',
                'HEADER' => $this->auth_headers($token),
            )
        );
        return json_decode($raw, true) ?: array();
    }

    /**
     * Send a scored result for a user to a lineitem URL.
     *
     * @param string $resulturl Lineitem URL (activity-level) from the platform.
     * @param string $userid Moodle user id.
     * @param float $scorepct 0..100
     * @param string $activityprogress completed|submitted.
     * @return array
     */
    public function send_result($resulturl, $userid, $scorepct, $activityprogress = 'completed') {
        $normalised = max(0.0, min(1.0, (float)$scorepct / 100.0));
        $payload = array(
            'userId' => (string)$userid,
            'comment' => 'Polelo Sepedi quiz result',
            'resultScore' => $normalised,
            'resultMaximum' => 1.0,
            'activityProgress' => $activityprogress,
            'gradingProgress' => 'FullyGraded',
            'timestamp' => date('c', time()),
        );
        $token = $this->access_token($resulturl);
        $curl = new \curl();
        $raw = $curl->post(
            $resulturl,
            json_encode($payload),
            array(
                'CUSTOMREQUEST' => 'POST',
                'HEADER' => $this->auth_headers($token),
            )
        );
        return json_decode($raw, true) ?: array();
    }

    /**
     * Request an LTI Advantage access token for the given resource URL.
     *
     * @param string $platformurl
     * @return string bearer token.
     */
    protected function access_token($platformurl) {
        $config = get_config('local_polelo');
        $issuer = rtrim(isset($config->polelo_url) ? $config->polelo_url : '', '/');
        $clientid = isset($config->lti_client_id) ? $config->lti_client_id : 'polelo';

        $grant = polelo_jwt_grant::grant_token($issuer, $this->platform_issuer($platformurl), $clientid, array(
            'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
            'https://purl.imsglobal.org/spec/lti-ags/scope/result.readonly',
        ));

        $tokenurl = rtrim($platformurl) . '/mod/lti/token.php';
        $curl = new \curl();
        $raw = $curl->post($tokenurl, http_build_query(array(
            'grant_type' => 'client_credentials',
            'client_assertion_type' => 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion' => $grant,
            'scope' => 'https://purl.imsglobal.org/spec/lti-ags/scope/lineitem',
        )));
        $decoded = json_decode($raw, true);
        if (isset($decoded['access_token'])) {
            return $decoded['access_token'];
        }
        throw new moodle_exception('polelo_tokenerror', 'local_polelo');
    }

    protected function auth_headers($token) {
        return "Authorization: Bearer " . $token . "\r\nContent-Type: application/vnd.ims.lti.v1.lineitem+json\r\n";
    }

    protected function platform_issuer($url) {
        $parts = parse_url($url);
        return isset($parts['scheme']) ? $parts['scheme'] . '://' . $parts['host'] : $url;
    }
}