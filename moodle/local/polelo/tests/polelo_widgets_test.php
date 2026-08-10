<?php
// PHPUnit tests for the widget markup helper.
// This file is part of the local_polelo plugin - Polelo STEM Sepedi translation layer.

namespace local_polelo;

defined('MOODLE_INTERNAL') || die();

use advanced_testcase;

/**
 * Tests for polelo_widgets markup builders.
 *
 * @covers \local_polelo\polelo_widgets
 */
class polelo_widgets_test extends advanced_testcase {
    public function test_translation_widget_contains_concept_id(): void {
        $html = polelo_widgets::translation_widget('abc-123-xyz', 8, 'light');
        $this->assertStringContainsString('data-concept-id="abc-123-xyz"', $html);
        $this->assertStringContainsString('data-grade="8"', $html);
        $this->assertStringContainsString('data-theme="light"', $html);
    }

    public function test_quiz_widget_contains_count(): void {
        $html = polelo_widgets::quiz_widget('abc-123-xyz', 8, 10, 'dark');
        $this->assertStringContainsString('data-count="10"', $html);
        $this->assertStringContainsString('data-theme="dark"', $html);
    }

    public function test_iframe_uses_configured_base_url(): void {
        $html = polelo_widgets::translation_iframe('abc-123-xyz', 8, 'https://polelo.taip.co.za');
        $this->assertStringContainsString(
            'src="https://polelo.taip.co.za/embed/translate?concept_id=abc-123-xyz&grade=8"',
            $html
        );
    }
}