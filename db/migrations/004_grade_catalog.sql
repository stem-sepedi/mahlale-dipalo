-- Polelo STEM Sepedi Translation Layer — Grade Catalog Schema
-- Migration: 004_grade_catalog.sql
--
-- R1 — first-class grade/phase registry that drives every grade-sensitive
-- behaviour. Seeded for Grade R (0)…12 plus University tier (99).

-- ============================================================
-- GRADE CATALOG
-- ============================================================

CREATE TABLE grade_catalog (
    grade SMALLINT PRIMARY KEY,
    phase VARCHAR(32) NOT NULL,
    band VARCHAR(32) NOT NULL,
    name_en VARCHAR(64) NOT NULL,
    name_sep VARCHAR(64) NOT NULL,
    age_min SMALLINT NOT NULL,
    age_max SMALLINT NOT NULL,
    vocab_level SMALLINT NOT NULL CHECK (vocab_level BETWEEN 1 AND 6),
    curriculum_ref VARCHAR(256) NOT NULL DEFAULT ''
);

CREATE INDEX idx_grade_catalog_phase ON grade_catalog (phase);
CREATE INDEX idx_grade_catalog_band ON grade_catalog (band);

-- ============================================================
-- SEED — Grade R (0) … 12 + University (99)
-- ============================================================

INSERT INTO grade_catalog
    (grade, phase, band, name_en, name_sep, age_min, age_max, vocab_level, curriculum_ref)
VALUES
    ( 0, 'foundation', 'foundation-r', 'Grade R',           'Mphato wa R',  5,  6, 1,
     'CAPS Life Skills – Beginning Knowledge (play-based)'),
    ( 1, 'foundation', 'foundation',    'Grade 1',           'Mphato wa 1',  6,  7, 1,
     'CAPS Mathematics + Life Skills Science'),
    ( 2, 'foundation', 'foundation',    'Grade 2',           'Mphato wa 2',  7,  8, 2,
     'CAPS Mathematics + Life Skills Science'),
    ( 3, 'foundation', 'foundation',    'Grade 3',           'Mphato wa 3',  8,  9, 2,
     'CAPS Mathematics + Life Skills Science'),
    ( 4, 'intermediate', 'intermediate', 'Grade 4',          'Mphato wa 4',  9, 10, 2,
     'CAPS Natural Sciences & Technology'),
    ( 5, 'intermediate', 'intermediate', 'Grade 5',          'Mphato wa 5', 10, 11, 3,
     'CAPS Natural Sciences & Technology'),
    ( 6, 'intermediate', 'intermediate', 'Grade 6',          'Mphato wa 6', 11, 12, 3,
     'CAPS Natural Sciences & Technology'),
    ( 7, 'senior', 'senior',            'Grade 7',           'Mphato wa 7', 12, 13, 3,
     'CAPS Natural Sciences / Mathematics'),
    ( 8, 'senior', 'senior',            'Grade 8',           'Mphato wa 8', 13, 14, 4,
     'CAPS Natural Sciences / Mathematics'),
    ( 9, 'senior', 'senior',            'Grade 9',           'Mphato wa 9', 14, 15, 4,
     'CAPS Natural Sciences / Mathematics'),
    (10, 'fet', 'fet',                  'Grade 10',          'Mphato wa 10', 15, 16, 5,
     'CAPS Physical Sciences / Mathematics / Life Sciences / IT'),
    (11, 'fet', 'fet',                  'Grade 11',          'Mphato wa 11', 16, 17, 5,
     'CAPS Physical Sciences / Mathematics / Life Sciences / IT'),
    (12, 'fet', 'fet',                  'Grade 12',          'Mphato wa 12', 17, 18, 6,
     'CAPS Physical Sciences / Mathematics / Life Sciences / IT'),
    (99, 'university', 'university',    'University',        'Mphato wa yunibesithi', 18, 99, 6,
     'HEQF university tier — see ROADMAP_UNIVERSITY.md');
