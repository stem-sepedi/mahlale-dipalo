-- Polelo STEM Sepedi Translation Layer — Question Triage Schema
-- Migration: 003_question_triage.sql
--
-- M10 — Question triage to LLM via Forgejo/Gitea issues.
-- Student questions are persisted here and mirrored to a Forgejo issue whose
-- labels track the LLM lifecycle (LLM_BACKLOG -> LLM_WIP -> LLM_DONE ->
-- HUMAN_VERIFIED / REJECTED).

-- ============================================================
-- QUESTIONS
-- ============================================================

CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_text TEXT NOT NULL,
    grade SMALLINT,
    subject VARCHAR(64),
    student_ref VARCHAR(128),
    submitted_by UUID REFERENCES users(id),
    forgejo_issue_number INTEGER,
    forgejo_issue_url TEXT,
    -- new | answered | similar | dispatched | answered_complete | verified | rejected
    triage_status VARCHAR(32) NOT NULL DEFAULT 'new',
    matching_issue_number INTEGER,
    matching_question_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_questions_triage_status ON questions (triage_status);
CREATE INDEX idx_questions_grade ON questions (grade);
CREATE INDEX idx_questions_subject ON questions (subject);
CREATE INDEX idx_questions_issue_number ON questions (forgejo_issue_number);

-- ============================================================
-- QUESTION ANSWERS
-- ============================================================

CREATE TABLE question_answers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    answer_sep TEXT NOT NULL,
    confidence_score REAL,
    -- llm_done | human_verified | rejected
    status VARCHAR(32) NOT NULL DEFAULT 'llm_done',
    generated_by VARCHAR(64) NOT NULL DEFAULT 'AI Agent',
    reviewed_by UUID REFERENCES users(id),
    review_comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_question_answers_question ON question_answers (question_id);
CREATE INDEX idx_question_answers_status ON question_answers (status);
