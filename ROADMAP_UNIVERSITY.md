# ROADMAP_UNIVERSITY.md

Extending Polelo from school (Grade R–12) to university-level STEM.

Version: 0.1

---

## Context

The schema reserves `99 = University` alongside the school grades (`0=Grade R, 1–12`), but the
university tier is currently unimplemented. University content differs from school content in:

- **Register**: formal academic Sepedi, not learner-friendly textbook Sepedi.
- **Domain depth**: first-year ↔ third-year ↔ honours/postgrad are different difficulty tiers; a
  single `grade_level` is insufficient — a `tier` concept is needed.
- **Subjects**: university domains go beyond the current `domain_type` enum (Biology, Physics,
  Chemistry, Mathematics, Geography, Computer Science, General) → engineering, statistics, biochemistry etc.
- **Terminology standardisation**: published academic glossaries, SIG-led terminology, citation of sources.
- **Delivery**: LMS (Moodle 4.1+ already integrated), lecture notes, tutorial sets, exam banks.

This roadmap treats University as a **separate tier** (not "grade 13") so school and university
content never mix in the same query path.

---

## Tier model

| Tier        | Key         | Typical year | Audience                        |
|-------------|-------------|--------------|---------------------------------|
| Foundation  | uni-foundation | Year 1   | First-years, extended programs, bridging |
| Core        | uni-core    | Year 2–3     | BSc majors                       |
| Advanced    | uni-advanced | Year 3–4    | Honours, capstone                |
| Postgrad    | uni-postgrad | Masters+     | Research, dissertations          |
| TVET        | tvet        | Any          | Technical/vocational programmes  |

Tier maps to a reserved grade slot for storage:
| storage grade | meaning |
|---------------|---------|
| 99 | University (any tier) |
| 100 | TVET |

---

## Milestone U1 — University Tier Foundation

**Goal:** Add the university tier as a first-class, query-safe layer.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| U1.1 | Tier enum + `uni_tier` column | Add `domain_type` additions (see U3) and `uni_tier` on `concepts`, `explanations`, `quiz_questions`; DB migration `002b_university_schema.sql` | Tier valid for all university-grade rows; school rows remain `NULL` |
| U1.2 | Rollback | `db/rollbacks/M/2/rollback-university.sh` | Drops tier additions without touching school data |
| U1.3 | Extended subjects | Extend `domain_type` enum with university subjects (see U3.1) | New enum values usable; old data intact (ALTER TYPE ... ADD VALUE) |
| U1.4 | Grade bounds | Central validator accepts `99`/`100` as university/TVET grade values | School queries reject 99 unless an explicit `tier=university` flag set |
| U1.5 | Config API | `GET /university/config` returns tier list, subjects, default register rules | Only university-tier data returned when requested |

**PR branch:** `roadmap/u1-tier-foundation`

---

## Milestone U2 — Academic Sepedi Register

**Goal:** Produce and maintain academically rigorous Sepedi content.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| U2.1 | Academic register prompt mode | New prompt set (`academic_*` in `src/services/prompts/`) with citation + formal register instructions | Same concept generates visibly different academic vs school output |
| U2.2 | Terminology authority feed | Table `acs_glossary_terms` seeded from an academic Sepedi glossary source (e.g. published university glossaries, language board lists) | Candidate terms flagged as "glossary-backed" vs "provisional" |
| U2.3 | Standardisation workflow | Reviewer role for academic terminology; `SIG`-style curation queue per subject | Terms only pending until an academic reviewer approves |
| U2.4 | Citation tracking | `references` JSONB on concepts/explanations (publisher, edition, page) | Every approved university explanation lists ≥1 source |
| U2.5 | Register validation agent | Grammar check customised for academic Sepedi (title case, term citation rules) | Academic register violations flagged before publish |

**PR branch:** `roadmap/u2-academic-register`

---

## Milestone U3 — Subject Coverage Expansion

**Goal:** Cover university STEM subjects beyond the school enum.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| U3.1 | Extended subject enum | Add `Engineering`, `Statistics`, `Biochemistry`, `Computer Engineering`, `Applied Maths`, `Astronomy` etc. to `domain_type` | New subjects selectable in API + admin UI |
| U3.2 | Subject-specific prompt packs | Per-subject vocabulary rules, notation handling, worked-example formats | Physics uses physical notation; Stats uses statistical terminology |
| U3.3 | University course mapping | `moodle_courses` gains `uni_tier`; moodle_course→tier mapping in config | Moodle course year-2 maps to `uni-core` |
| U3.4 | Concept depth levels | `concepts` gets a `depth` smallint (1=single topic, 2=chapter, 3=interdisciplinary) | UI and API can filter by depth |
| U3.5 | Coverage dashboard (university) | `GET /coverage?tier=uni-core&domain=Engineering` | Missing core-subject topics surface per term |

**PR branch:** `roadmap/u3-subjects`

---

## Milestone U4 — Lecture, Tutorial & Assessment Assets

**Goal:** Beyond explanations: usable university teaching artefacts.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| U4.1 | Worked examples | `worked_examples` JSONB on university explanations (multi-step to solution) | Each rationale has ≥2 steps with Sepedi step labels |
| U4.2 | Tutorial problem sets | `quiz_questions` gain `tier` + difficulty ladder (Bloom) for university | Problem sets generate per tier and question type |
| U4.3 | Exam bank export | Extend Moodle XML export with tier-aware category and extended questions | `format=moodle_xml&tier=uni-core` exportable and importable |
| U4.4 | Lecture-note rendering | Endpoint `/notes/{concept_id}?tier=...` that renders structured lecture notes | Returns a print-ready, structured note; offline-exportable to PDF/PWA |
| U4.5 | Timed assessment | Experimental `attempt` tracking with time-boxed quizzes | Score + time recorded; adaptive retry suggested |

**PR branch:** `roadmap/u4-assets`

---

## Milestone U5 — University LMS Integration

**Goal:** Meet university where academics work: Moodle, and beyond.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| U5.1 | Tier in plugin settings | `local_polelo/settings.php` university tier picker + per-course tier | Course widget shows tier-appropriate content |
| U5.2 | LTI Advantage depth | Extend LTI 1.3 lineitem/result to tier-aware assets and grade passback (score per tier) | Grade passback uses tier-correct max score |
| U5.3 | Bulk university sync | `moodle_sync` polls university course mappings and pulls concepts/quizzes per tier | Sync state tracks tier alongside course |
| U5.4 | Assignment embedding | Widget/iframe embedding for assignments and worked examples pages | University course page shows inline tutorial widget |
| U5.5 | Public discovery | `/moodle/concepts` gains `tier` facet | University tier queryable via content-API |

**PR branch:** `roadmap/u5-lms-integration`

---

## Milestone U6 — Community & Academic Governance

**Goal:** Sustain quality with academic ownership.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| U6.1 | Academic reviewer role | `reviewer_academic` role with distinct review queue | University content reviewable only by academic role |
| U6.2 | Glossary contribution UI | Community submit proposed terms; SIG vote/approve | Only approved terms enter glossary-backed set |
| U6.3 | Versioning for academic content | Reuse `version_snapshots` with tier-aware archive keys | Academic content versioned/revertible independently of school content |
| U6.4 | Attribution & provenance | `archived_by` / citation rendering included in exports | Every export carries source attribution |
| U6.5 | Benchmark (university) | Complexity/register metrics for academic corpus | Academic register consistently above school register in metric |

**PR branch:** `roadmap/u6-governance`

---

## Milestone U7 — Pilot & Foundation Launch

**Goal:** One university partner, one subject, one tier end-to-end.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| U7.1 | Pilot pack | Docs + seed set for a first-year foundation Maths/Biology pilot | Uses `uni-foundation`, glossary-backed terms, worked examples |
| U7.2 | Offline university deployment | PWA/RPi offline cache for university subject packs | Offline load of `uni-founder` pack works |
| U7.3 | Feedback loop | Survey mechanism for lecturers | Config defaults tuned per department |
| U7.4 | DOAC cross-check | Reuse disaster-recovery path for tier data | Tier data restorable independently |

---

## Definition of Done

- University tier (99) and TVET (100) query-safe; never leak into school responses.
- Academic register mode, glossary-backed terms, citation tracking live.
- ≥2 university subjects (e.g. Mathematics, Biology) covered at `uni-foundation`.
- Moodle course→tier→content pipeline working end-to-end in a pilot.
- Rollback scripts for all migrations.

Related: `ROADMAP_GRADES_R12.md`, `GOAL.md` University level, `IMPLEMENTATION_PLAN.md` Phase 7 subject expansion, `Docker/Deployment` offline goals.