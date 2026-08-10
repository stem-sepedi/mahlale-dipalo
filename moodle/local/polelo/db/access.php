<?php
// Capability definitions for local_polelo - Polelo STEM Sepedi translation layer.
// This file is part of Moodle: https://moodle.org/

defined('MOODLE_INTERNAL') || die();

$capabilities = array(

    // Whether the user can view Polelo content widgets on a course page.
    'local/polelo:view' => array(
        'captype' => 'read',
        'contextlevel' => CONTEXT_COURSE,
        'archetypes' => array(
            'student' => CAP_ALLOW,
            'teacher' => CAP_ALLOW,
            'editingteacher' => CAP_ALLOW,
            'manager' => CAP_ALLOW,
        ),
    ),

    // Whether the user can configure the Polelo connection (API key, broker, URL).
    'local/polelo:manage' => array(
        'riskbitmask' => RISK_CONFIG,
        'captype' => 'write',
        'contextlevel' => CONTEXT_SYSTEM,
        'archetypes' => array(
            'manager' => CAP_ALLOW,
        ),
    ),
);