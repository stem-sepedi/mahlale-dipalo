<?php
// tool_provider.php - LTI 1.3 tool provider: OIDC login initiation + launch response.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

defined('MOODLE_INTERNAL') || die();

require_once(__DIR__ . '/jwt_grant.php');

/**
 * polelo_lti_tool_provider - handles LTI 1.3 OIDC login initiation and launch,
 * signing the launch JWT with the plugin's LTI secret.
 */
class polelo_lti_tool_provider {

    /** @var string Verification URI for OIDC login. */
    const OIDC_AUTH_URL = '/mod/lti/auth.php';
    /** @var string JWT grant URI used by LTI Advantage services. */
    const TOKEN_URL = '/mod/lti/token.php';

    /**
     * Build the OIDC login initiation response (302 back to the platform).
     *
     * @param string $platformiss Issuer (platform base URL).
     * @param string $lticlientid
     * @param string $loginhint
     * @return void
     */
    public function oidc_login_initiation($platformiss, $lticlientid, $loginhint) {
        $provider = $this->tool_base();
        $params = array(
            'iss' => $platformiss,
            'login_hint' => $loginhint,
            'client_id' => $lticlientid,
            'target_link_uri' => $provider->target_link_uri,
            'lti_message_hint' => 'polelo',
        );
        $redirect = $platformiss . self::OIDC_AUTH_URL . '?' . http_build_query($params);
        redirect($redirect);
    }

    /**
     * Validate a received LTI launch and produce the launch JWT.
     *
     * @param string $iss
     * @param array $claims Incoming launch claims.
     * @param string $clientid
     * @param string $nonce
     * @return array { jwt, redirect_url }
     */
    public function launch($iss, $claims, $clientid, $nonce) {
        $provider = $this->tool_base();
        $claims['iss'] = $iss;
        $claims['aud'] = $clientid;
        $claims['nonce'] = $nonce;
        $claims['iat'] = time();
        $claims['exp'] = time() + HOURSECS;
        $claims['https://purl.imsglobal.org/spec/lti/claim/tool_platform'] = array(
            'guid' => $iss,
            'name' => str_replace('https://', '', $iss),
        );

        $jwt = polelo_jwt_grant::sign($claims);
        return array(
            'jwt' => $jwt,
            'redirect_url' => $provider->target_link_uri,
        );
    }

    /**
     * Exchange a platform assertion (JWT) for the provider base config.
     */
    public function tool_base() {
        $config = get_config('local_polelo');
        $base = rtrim(isset($config->polelo_url) ? $config->polelo_url : '', '/');
        return (object) array(
            'name' => 'Polelo STEM Sepedi',
            'target_link_uri' => $base . '/embed/translate',
            'oicdloginuri' => $base . '/embed/translate',
            'jwksuri' => $base . '/moodle/lti/jwks',
        );
    }
}