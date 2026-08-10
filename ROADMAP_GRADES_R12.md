# ROADMAP_GRADES_R12.md

Configuring Polelo for every South African school grade, Grade R → 12.

Version: 0.1

---

## Context

Current state of grade handling:

- `grade_levels smallint[]` on `concepts` — `0` = Grade R, `1–12` = Grades 1–12.
- `explanations.grade_level` and `quiz_questions.grade_level` already store a single target grade.
- Prompts (`translate_prompt`, `explain_prompt`, `quiz_prompt`) receive a grade number but treat it
  as a single difficulty knob — there is **no per-grade pedagogical configuration**.
- UI defaults everywhere to grade 8.
- CAPS phases referenced in `GOAL.md` (Foundation, Intermediate, Senior, FET) are not enforced or
  configurable in the system.

Goal: let an operator (school, district, publisher) set up the tool for a specific grade — or a
whole phase — so terminology, register, explanation depth, examples and quiz difficulty follow the
CAPS curriculum for that grade.

---

## Grade → Phase map (South African CAPS)

| Grade(s) | Phase            | Band key     | Age band | Curriculum subjects (STEM)              |
|----------|------------------|--------------|----------|------------------------------------------|
| R        | Foundation       | foundation-r | 5–6      | Numeracy, Life Skills (science play)     |
| 1–3      | Foundation       | foundation   | 6–9      | Mathematics, Life Skills science         |
| 4–6      | Intermediate     | intermediate | 9–12     | Natural Sciences & Technology            |
| 7–9      | Senior           | senior       | 12–15    | Natural Sciences, Mathematics            |
| 10–12    | FET              | fet          | 15–18    | Physical Sciences, Mathematics, Life Sciences, Information Technology |

---

## Milestone R1 — Grade Catalog & Per-Grade Configuration

**Goal:** A first-class grade/phase registry that drives every grade-sensitive behaviour.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| R1.1 | `grade_catalog` table | `db/migrations/003_grade_catalog.sql`: rows for grade R (0)…12 and phase 13-99 (University); columns `grade`, `phase`, `band`, `name_en`, `name_sep`, `age_min`, `age_max`, `vocab_level` (1–6), `curriculum_ref` | Seeded with R–12 matching the table above; grade 8 resolves to `senior` band, vocab level 4 |
| R1.2 | Settings provider | `src/services/grade_config.py` — loads catalog, supports overrides per instance (JSON in a config table or env) | `get_grade_config(8)` returns band, vocab_level, age band, curriculum ref without DB round-trip per request |
| R1.3 | Grade spec endpoint | `GET /grades` (admin) + `GET /grades/{grade}` returns config and CAPS reference | Seeded data only; no write endpoint yet |
| R1.4 | Validate grade bounds | Migrate all `grade_level` validation to accept 0–12 and 99, reject others (central validator in `src/config.py` or a shared util) | `500`→`422` for grade 13; 0 and 99 accepted |
| R1.5 | Rollback script | `db/rollbacks/M/3/rollback.sh` | Drops catalog table cleanly |

**PR branch:** `roadmap/r1-grade-catalog`

---

## Milestone R2 — Per-Grade Prompting (Curriculum-Aligned Vocabulary)

**Goal:** Explanations, translations and quizzes change register and depth per grade.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| R2.1 | Vocab-level descriptors | Per-`vocab_level` (1–6) rule blocks in `src/services/prompts/banding.py`: sentence length, allowed register, concept count, example style | Levels 1 and 6 produce measurably different output (word-length + register heuristics) |
| R2.2 | Injected grade context | `explain_prompt` / `quiz_prompt` / `translate_prompt` take full grade config (band, age, curriculum ref, examples) instead of bare `int` | Prompt for grade R contains play/visual language; grade 12 prompt cites CAPS assessment verbs |
| R2.3 | Phase-aware rule sets | CAPS terminology packs per phase: Foundation (R-3), Intermediate (4-6), Senior (7-9), FET (10-12) stored as editable JSON in DB | Querying a concept at grade 6 returns Intermediate vocabulary; grade 11 same concept returns FET vocabulary |
| R2.4 | Sepedi register tables | A `registers` table mapping formal/textbook/informal register per phase | Standardised terms flagged correctly per phase, reusing existing `alternative_forms` structure |
| R2.5 | Grade-aware validation | Validation agent checks vocabulary fits the target grade band | Community review flags grade-8 term rejected when targeting grade R |

**PR branch:** `roadmap/r2-per-grade-prompts`

---

## Milestone R3 — Content Coverage per Phase

**Goal:** Concept catalogue aligned to the actual CAPS curriculum per grade.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| R3.1 | Curriculum concept import | Machine-readable CAPS-referenced concept lists (marker/docs): term-by-term topics per subject & grade | Import script validates every concept has ≥1 target grade |
| R3.2 | Coverage pipeline | Batch generate missing translations/explanations for a grade via MQTT (`translation.request`) | Queue fills for grade R concepts with 0 approved translations |
| R3.3 | Coverage dashboard | `GET /coverage?grade=8&domain=Physics` returns done/total per curriculum topic | Grade-level coverage visible per subject; gaps actionable |
| R3.4 | Seed curriculum concepts | Extend `db/seed.py` with a `--phase`, `--grade` filter | `python3 db/seed.py --grade=8` seeds only grade-8 concepts |
| R3.5 | Deprecation of stale grades | Concepts with no published content for a grade hidden from that grade's UI/API | Grade filter queries exclude empty grades |

**PR branch:** `roadmap/r3-coverage`

---

## Milestone R4 — Per-Grade UX & Operator Configuration

**Goal:** Teachers and admins configure the tool for their class in minutes.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| R4.1 | Grade selector UI | Primary-surface grade picker (R, 1…12) persisting in learner profile/PWA storage | Choosing grade 4 re-renders search, explanations and quiz widgets for that grade |
| R4.2 | Admin per-grade settings | Settings page: override vocab_level, default quiz type, Sepedi/English default, theme, per phase | Saved overrides apply to all API responses for that grade |
| R4.3 | Widget grade config | Widgets accept validated grade (not just 0-12 int); Moodle plugin reads grade from course config | `data-grade="13"` rejected client-side; course grade maps to a catalog grade |
| R4.4 | Teacher notes per grade | `teacher_notes` field on explanations, rendered for educators only | Teacher role sees notes; learner role does not |
| R4.5 | Moodle course↔grade mapping | `local_polelo/settings.php` grade select uses catalog (R–12 + University) | Setting a course grade R drives widgets + sync target |

**PR branch:** `roadmap/r4-grade-ux`

---

## Milestone R5 — Quiz & Assessment Alignment

**Goal:** Quizzes map to CAPS assessment standards per grade.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| R5.1 | Quiz difficulty ladder | `quiz_questions.grade_level` plus catalog vocab_level drive a difficulty ladder (1–6) | Grade R → level 1; grade 12 → level 6; mid-grades interpolate |
| R5.2 | CAPS verb set | Question stems use CAPS assessment verbs per grade (identify → describe → explain → evaluate) | Grade-appropriate stems in >80% of generated questions (validated) |
| R5.3 | Grade binding on export | Moodle XML export includes grade/phase in category names | `?grade=4` exports distance `$course$/Intermediate/Natural Sciences` |
| R5.4 | Adaptive re-quiz | `/quiz/validate` returns grade band + next-difficulty suggestion | Score <60% suggests level drop by one band |

**PR branch:** `roadmap/r5-quiz-alignment`

---

## Milestone R6 — Rollout & Quality per Phase

**Goal:** Validate quality phase-by-phase, pilot with schools, ship per grade.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| R6.1 | Complexity benchmark | Script measures word length / sentence length / register per grade across corpus | Monotonic increase R→12; grade-to-grade jump statistically significant |
| R6.2 | Phase pilot packs | Reviewer checklists per phase (docs + in-app review form) | Completed pilot pack per Foundation & Senior phases |
| R6.3 | Teacher acceptance survey | Response data drives config defaults per phase | Config defaults updated once per phase post-pilot |
| R6.4 | Offline PWA per grade | Service worker caches by grade; RPi image preloads grade packs | Offline grade-8 pack loads without network |

**PR branch:** `roadmap/r6-rollout`

---

## Definition of Done

- `grade_catalog` seeded R–12, referenced by prompts, UI, widgets, Moodle plugin.
- All grade-boundaries validated centrally (0–12, 99).
- Coverage per grade visible and gapped-filled for ≥2 pilot subjects.
- Complexity benchmark monotonic R→12.
- Rollback path for every migration.

Related: `ROADMAP_UNIVERSITY.md` (grade 99 tier), `GOAL.md` phases, `IMPLEMENTATION_PLAN.md` Phase 6–7.