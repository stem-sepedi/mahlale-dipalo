<?php
// jwt_grant.php - JWT signing for LTI Advantage services.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

defined('MOODLE_INTERNAL') || die();

/**
 * polelo_jwt_grant - signs JWTs (LTI launch and LTI Advantage service grants)
 * using the plugin's LTI secret with HS256.
 */
class polelo_jwt_grant {

    /**
     * Sign a claim set into a compact JWS token (HS256).
     *
     * @param array $claims
     * @param string|null $secret override (defaults to local_polelo LTI secret).
     * @return string compact JWT.
     */
    public static function sign($claims, $secret = null) {
        $secret = $secret ?: static::secret();
        $header = self::b64url(json_encode(array('typ' => 'JWT', 'alg' => 'HS256')));
        $payload = self::b64url(json_encode($claims));
        $signature = self::b64url(hash_hmac('sha256', $header . '.' . $payload, $secret, true));
        return $header . '.' . $payload . '.' . $signature;
    }

    /**
     * Verify and decode a compact JWS token.
     *
     * @param string $token
     * @param string|null $secret
     * @return array decoded claims, or null if invalid.
     */
    public static function verify($token, $secret = null) {
        $secret = $secret ?: static::secret();
        $parts = explode('.', $token);
        if (count($parts) !== 3) {
            return null;
        }
        list($header, $payload, $signature) = $parts;
        $expected = self::b64url(hash_hmac('sha256', $header . '.' . $payload, $secret, true));
        if (!hash_equals($expected, $signature)) {
            return null;
        }
        $claims = json_decode(self::b64url_decode($payload), true);
        if (!is_array($claims)) {
            return null;
        }
        if (isset($claims['exp']) && time() > (int)$claims['exp']) {
            return null;
        }
        return $claims;
    }

    /**
     * Build an LTI Advantage access-token grant (JWT signed by the tool).
     *
     * @param string $issuer tool issuer.
     * @param string $audience platform issuer.
     * @param string $subject tool client id.
     * @param array $scopes
     * @return string signed grant JWT.
     */
    public static function grant_token($issuer, $audience, $subject, $scopes) {
        $claims = array(
            'iss' => $issuer,
            'aud' => $audience,
            'sub' => $subject,
            'iat' => time(),
            'exp' => time() + 3600,
            'jti' => bin2hex(random_bytes(8)),
        );
        foreach ($scopes as $scope) {
            $claims['scope'][] = $scope;
        }
        return self::sign($claims);
    }

    protected static function secret() {
        $config = get_config('local_polelo');
        $secret = isset($config->lti_secret) ? $config->lti_secret : '';
        if (!$secret) {
            $env = getenv('MoodleLtiSecret');
            $secret = $env ? $env : '';
        }
        return $secret;
    }

    protected static function b64url($data) {
        return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
    }

    protected static function b64url_decode($data) {
        $remainder = strlen($data) % 4;
        if ($remainder) {
            $data .= str_repeat('=', 4 - $remainder);
        }
        return base64_decode(strtr($data, '-_', '+/'));
    }
}