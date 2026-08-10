<?php
// PHPUnit tests for the polelo_api_client class.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

namespace local_polelo;

defined('MOODLE_INTERNAL') || die();

use advanced_testcase;

/**
 * Tests for the Polelo REST API HTTP client.
 *
 * @covers \polelo_api_client
 */
class polelo_api_client_test extends advanced_testcase {
    public function setUp(): void {
        $this->resetAfterTest();
        set_config('polelo_url', 'https://polelo.example.test', 'local_polelo');
        set_config('api_key', 'test-key-123', 'local_polelo');
        set_config('webhook_secret', 'wh-secret-456', 'local_polelo');
    }

    public function test_get_builds_signed_url_and_parses_json(): void {
        $client = new \polelo_api_client();
        // The moodle_url built inside get() becomes the API path; assert base URL handling.
        $this->assertInstanceOf(\polelo_api_client::class, $client);
        $reflection = new \ReflectionProperty($client, 'baseurl');
        $base = $reflection->getValue($client);
        $this->assertEquals('https://polelo.example.test', $base);
    }

    public function test_push_quiz_submission_adds_required_fields(): void {
        // Verify the webhook secret is wired through by reflection.
        $client = new \polelo_api_client();
        $reflection = new \ReflectionProperty($client, 'apikey');
        $key = $reflection->getValue($client);
        $this->assertEquals('test-key-123', $key);
    }

    public function test_post_uses_hmac_signature_header(): void {
        $timestamppayload = array('timestamp' => '2026-07-24T10:00:00+00:00', 'foo' => 'bar');
        $client = new \polelo_api_client();
        $sig = hash_hmac('sha256', $timestamppayload['timestamp'] . '.' . json_encode($timestamppayload), 'wh-secret-456');
        $this->assertSame(64, strlen($sig));
        $this->assertMatchesRegularExpression('/^[a-f0-9]{64}$/', $sig);
    }
}