<?php
// polelo_mqtt_bridge.php - publishes real-time translation requests to the MQTT broker.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

// MQTT over TCP is not part of the PHP standard library; this bridge uses Mosquitto's
// mosquitto PHP extension when available, and otherwise falls back to a publish-only
// HTTP bridge (the Polelo broker endpoint) so the plugin remains installable everywhere.

/**
 * polelo_mqtt_bridge - MQTT publish for real-time translation requests.
 */
class polelo_mqtt_bridge {
    /** @var string Broker host. */
    protected $broker;
    /** @var int Broker port. */
    protected $port;
    /** @var bool Whether the php-mosquitto extension is available. */
    protected $native;

    public function __construct($broker = null, $port = null) {
        $config = get_config('local_polelo');
        $this->broker = $broker ?: (isset($config->mqtt_broker) ? $config->mqtt_broker : 'localhost');
        $this->port = (int)($port ?: (isset($config->mqtt_port) ? $config->mqtt_port : 1883));
        $this->native = class_exists('Mosquitto\Client');
    }

    /**
     * Publish a translation request for a concept.
     *
     * @param string $conceptid
     * @param string $term English term.
     * @param array $gradelevels
     * @return bool true if the publish was attempted/delivered.
     */
    public function publish_translation_request($conceptid, $term, $gradelevels = array()) {
        $payload = json_encode(array(
            'concept_id' => $conceptid,
            'term' => $term,
            'grade_levels' => array_map('intval', $gradelevels),
            'request_id' => bin2hex(random_bytes(8)),
            'source' => 'local_polelo',
        ));
        return $this->publish('translation.request', $payload);
    }

    /**
     * Publish an arbitrary message on a topic.
     *
     * @param string $topic
     * @param string $payload
     * @return bool
     */
    public function publish($topic, $payload) {
        if ($this->native) {
            return $this->publish_native($topic, $payload);
        }
        return $this->publish_via_http($topic, $payload);
    }

    protected function publish_native($topic, $payload) {
        try {
            $client = new \Mosquitto\Client('polelo-moodle-' . random_int(1000, 9999));
            $client->connect($this->broker, $this->port, 10);
            $client->publish($topic, $payload, 1);
            $client->disconnect();
            return true;
        } catch (Throwable $e) {
            debugging('polelo_mqtt_bridge native publish failed: ' . $e->getMessage(), DEBUG_DEVELOPER);
            return false;
        }
    }

    protected function publish_via_http($topic, $payload) {
        // Requires an MQTT-over-HTTP bridge on the Polelo server (e.g. /mqtt/publish).
        $config = get_config('local_polelo');
        $base = rtrim(isset($config->polelo_url) ? $config->polelo_url : '', '/');
        if (!$base) {
            return false;
        }
        try {
            $curl = new \curl();
            $raw = $curl->post($base . '/mqtt/publish', json_encode(array(
                'topic' => $topic,
                'payload' => json_decode($payload, true),
            )));
            return $curl->errno === 0;
        } catch (Throwable $e) {
            debugging('polelo_mqtt_bridge http publish failed: ' . $e->getMessage(), DEBUG_DEVELOPER);
            return false;
        }
    }
}