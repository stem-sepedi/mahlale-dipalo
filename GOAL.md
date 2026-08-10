### `GOAL.md`

```markdown
# GOAL.md
# STEM Sepedi Translation Layer
Version: 0.1
Target Language: Sepedi (Sesotho sa Leboa)
Target Population: ~4.7 million South African Sepedi speakers

---

# Goal

Build an open-source translation and education platform that makes STEM
(Science, Technology, Engineering and Mathematics) understandable in
natural Sepedi.

The project is NOT a literal dictionary.

Its purpose is to explain difficult scientific concepts using culturally
appropriate language, examples and illustrations while preserving
scientific correctness.

The platform should eventually support every STEM subject taught from
Grade R through University.

---

# Primary Objectives

* Explain STEM concepts in simple Sepedi.
* Preserve scientific accuracy.
* Support multiple reading levels.
* Support learners, teachers and parents.
* Operate completely offline.
* Operate on inexpensive hardware.
* Support AI-assisted explanations.
* Support voice in future versions.
* Support diagrams in future versions.
* Support community review.
* Support versioned translations.

---

# Long-term Vision

Every South African learner should be able to ask:

    "Explain photosynthesis in Sepedi."

and receive an explanation equivalent in quality to an English textbook.

---

# Design Principles

* Open Source
* Offline First
* AI Assisted
* Human Verified
* Version Controlled
* Modular
* API First
* Mobile Friendly
* Teacher Friendly
* Community Driven

---

# Success Metrics

* 100,000 STEM concepts translated
* 1 million explanation examples
* Grade-specific explanations
* Human review workflow
* <2 second response time
* Fully offline deployment
* Docker deployment
* LAN deployment
* Raspberry Pi compatible

---

# Non Goals

* Machine translation only
* Literal dictionary
* English replacement
* Proprietary datasets
```

---

# `AGENTS.md`

```markdown
# AGENTS.md

Every AI agent participating in this repository MUST follow these rules.

---

## General Rules

1. Never edit files without understanding their purpose.
2. Always update TODO.md.
3. Every feature lives on its own Git branch.
4. Never commit broken code.
5. Every new file requires documentation.
6. Every change requires tests.
7. Every feature requires rollback instructions.
8. Keep commits atomic.
9. Prefer simple implementations.
10. Document assumptions.

---

## Translation Agent

Responsibilities

* Translate STEM terminology.
* Preserve scientific meaning.
* Detect ambiguous words.
* Suggest multiple translations.
* Maintain translation history.

Output

translation.json

---

## Explanation Agent

Responsibilities

Generate learner-friendly explanations.

Levels

* Grade R
* Foundation
* Intermediate
* Senior
* FET
* University

---

## Validation Agent

Checks

* Grammar
* Terminology
* Consistency
* Duplicates
* Missing references

---

## AI Agent

Uses local Ollama only.

Never call cloud APIs.

Supports

* explanation
* simplification
* examples
* quizzes

---

## Queue Agent

Consumes MQTT messages.

Retries failed jobs.

Dead-letter queue support.

---

## Archive Agent

Stores immutable versions in S3.

---

## Review Agent

Human approval workflow.

Status

Draft

↓

Pending Review

↓

Approved

↓

Published

---

## Documentation Agent

Maintains

GOAL.md

SPEC.md

ARCHITECTURE.md

TODO.md

CHANGELOG.md
```

---

# `ARCHITECTURE.md`

```markdown
# ARCHITECTURE.md

                     +----------------------+
                     | Browser              |
                     | HTML CSS JS PHP      |
                     +----------+-----------+
                                |
                                |
                                v
                    REST / WebSocket / MQTT
                                |
                                v
                  +----------------------------+
                  | MQTT Broker                |
                  | Translation Queue          |
                  +------+---------------------+
                         |
         +---------------+---------------+
         |                               |
         v                               v

+--------------------+       +----------------------+
| Python API         |       | Worker Pool          |
| FastAPI            |       | Translation Jobs     |
+---------+----------+       +----------+-----------+
          |                            |
          |                            |
          v                            v

+-------------------+        +----------------------+
| Ollama            |        | TimescaleDB          |
| Local LLM         |        | Concepts             |
+---------+---------+        | Explanations         |
          |                  | Versions             |
          |                  +----------+-----------+
          |                             |
          |                             |
          +-------------+---------------+
                        |
                        v

                 +--------------+
                 | S3 Archive   |
                 | Immutable    |
                 | Snapshots    |
                 +--------------+

---------------------------------------------------

Frontend

HTML

CSS

JavaScript

PHP

Backend

Python 3

FastAPI

TimescaleDB

Ollama

Workers

MQTT Queue

Storage

S3

Deployment

Docker Compose

Offline

LAN

API First

No Internet Required
```

---

# `SPEC.md`

```markdown
# SPEC.md

Version 0.1

---

Project Name

STEM Sepedi Translation Layer

---

Purpose

Translate and explain STEM concepts using AI and human review.

---

Core Features

✓ Concept search

✓ Translation

✓ Multi-level explanations

✓ Examples

✓ Images

✓ Quiz generation

✓ Teacher notes

✓ Offline AI

✓ Version history

✓ Review workflow

✓ S3 archive

---

Concept Structure

Concept

↓

Definition

↓

Translation

↓

Explanation

↓

Examples

↓

Diagram

↓

Quiz

↓

References

---

API

GET

/concepts

GET

/concept/{id}

POST

/translate

POST

/explain

POST

/review

POST

/publish

---

Queue Topics

translation.request

translation.completed

translation.failed

review.pending

review.approved

archive.store

---

Database

concepts

translations

examples

media

reviews

versions

users

audit_log

---

Roles

Admin

Teacher

Translator

Reviewer

Learner

AI Worker

---

Performance

Response <2 seconds

Offline mode

Supports 100 concurrent users

Horizontal workers

Immutable archives

---

Security

JWT

RBAC

Audit logs

HTTPS

Signed archives
```

---

# `TODO.md`

```markdown
# TODO.md

Version 0.1

---

## Phase 1

- [ ] Repository
- [ ] Docker Compose
- [ ] Python API
- [ ] TimescaleDB
- [ ] Ollama
- [ ] MQTT Broker
- [ ] PHP Frontend
- [ ] Login
- [ ] Search
- [ ] Translation API

---

## Phase 2

- [ ] Explanation Engine
- [ ] Example Generator
- [ ] Grade Levels
- [ ] Image Support
- [ ] Quiz Generator
- [ ] Voice API

---

## Phase 3

- [ ] Human Review
- [ ] Version Control
- [ ] Translation History
- [ ] Community Contributions
- [ ] Moderation

---

## Phase 4

- [ ] S3 Archive
- [ ] Snapshots
- [ ] Disaster Recovery
- [ ] Backup Validation

---

## Phase 5

- [ ] Mobile UI
- [ ] PWA
- [ ] Offline Cache
- [ ] Raspberry Pi Deployment

---

## Phase 6

- [ ] Grade R Curriculum
- [ ] Foundation Phase
- [ ] Intermediate Phase
- [ ] Senior Phase
- [ ] FET
- [ ] TVET
- [ ] University STEM

---

## Phase 7

- [ ] Physics
- [ ] Chemistry
- [ ] Biology
- [ ] Mathematics
- [ ] Engineering
- [ ] Computer Science
- [ ] Robotics
- [ ] Astronomy
- [ ] Agriculture
- [ ] Environmental Science

---

## Continuous Tasks

- [ ] Update documentation
- [ ] Run automated tests
- [ ] Verify translations
- [ ] Improve explanations
- [ ] Benchmark Ollama
- [ ] Monitor MQTT queues
- [ ] Archive approved releases
- [ ] Maintain API compatibility
```
