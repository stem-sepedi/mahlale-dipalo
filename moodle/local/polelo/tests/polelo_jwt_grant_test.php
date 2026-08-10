<?php
// PHPUnit tests for the LTI JWT signing helper.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

namespace local_polelo;

defined('MOODLE_INTERNAL') || die();

use advanced_testcase;

/**
 * Tests for the LTI 1.3 JWT grant helper.
 *
 * @covers \polelo_jwt_grant
 */
class polelo_jwt_grant_test extends advanced_testcase {
    public function test_sign_and_verify_roundtrip(): void {
        $claims = array('iss' => 'tool', 'sub' => 'user', 'exp' => time() + 3600);
        $token = \polelo_jwt_grant::sign($claims, 'test-secret');
        $decoded = \polelo_jwt_grant::verify($token, 'test-secret');
        $this->assertEquals('tool', $decoded['iss']);
        $this->assertEquals('user', $decoded['sub']);
    }

    public function test_verify_rejects_tampered_token(): void {
        $claims = array('iss' => 'tool', 'exp' => time() + 3600);
        $token = \polelo_jwt_grant::sign($claims, 'test-secret');
        $tampered = substr_replace($token, 'X', -4, 1);
        $this->assertNull(\polelo_jwt_grant::verify($tampered, 'test-secret'));
    }

    public function test_verify_rejects_expired_token(): void {
        $claims = array('iss' => 'tool', 'exp' => time() - 10);
        $token = \polelo_jwt_grant::sign($claims, 'test-secret');
        $this->assertNull(\polelo_jwt_grant::verify($token, 'test-secret'));
    }

    public function test_grant_token_contains_scopes(): void {
        $token = \polelo_jwt_grant::grant_token('tool', 'platform', 'client-id', array('scope:one'));
        $parts = explode('.', $token);
        $this->assertCount(3, $parts);
        $payload = json_decode(base64_decode(strtr($parts[1], '-_', '+/')), true);
        $this->assertEquals('tool', $payload['iss']);
        $this->assertEquals('platform', $payload['aud']);
        $this->assertEquals(array('scope:one'), $payload['scope']);
    }
}