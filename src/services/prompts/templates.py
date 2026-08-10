"""Prompt templates for STEM translation and explanation generation."""


def translate_prompt(
    term: str,
    domain: str,
    grade_levels: list[int],
    context_sep: str = "",
) -> str:
    """Generate a Sepedi translation prompt for a STEM term."""
    grades = ", ".join(str(g) for g in sorted(grade_levels))
    context_line = f"\nContext in Sepedi: {context_sep}" if context_sep else ""

    return f"""You are a Sepedi-language STEM translator.
Translate the following English STEM term into Sepedi (Northern Sotho).

Term: {term}
Domain: {domain}
Target grade levels: {grades}{context_line}

Rules:
- Provide the most natural Sepedi translation used in school textbooks.
- If the term is borrowed from English, indicate it as (borrowed).
- Provide 2-4 alternative forms with register labels (formal, informal, textbook).
- Rate your confidence from 0.0 to 1.0.

Return ONLY valid JSON in this exact format:
{{
  "sepedi_term": "main translation",
  "confidence_score": 0.85,
  "alternative_forms": [
    {{"form": "alternative 1", "register": "formal"}},
    {{"form": "alternative 2", "register": "informal"}}
  ]
}}"""


def explain_prompt(term: str, domain: str, grade_level: int) -> str:
    """Generate a Sepedi explanation prompt for a STEM concept."""
    return f"""You are a Sepedi-language STEM educator.
Explain the following concept for a grade {grade_level} learner in Sepedi (Northern Sotho).

Concept: {term}
Domain: {domain}
Grade level: {grade_level}

Rules:
- Use simple, age-appropriate language.
- Include a real-world example from South African context.
- If the term has no standard Sepedi equivalent, provide the English term in parentheses.
- Keep the explanation between 100-300 words.

Return ONLY valid JSON in this exact format:
{{
  "content_sep": "Full explanation in Sepedi...",
  "examples_sep": ["Example 1 in Sepedi", "Example 2 in Sepedi"]
}}"""


def question_answer_prompt(
    question: str,
    grade: int | None = None,
    subject: str | None = None,
) -> str:
    """Generate a prompt that answers a learner's question in Sepedi."""
    grade_line = f"\nLearner grade level: {grade}" if grade is not None else ""
    subject_line = f"\nSubject: {subject}" if subject else ""

    return f"""You are a Sepedi-language STEM educator answering a learner's question.
Answer clearly and correctly in Sepedi (Northern Sotho), keeping the explanation
age-appropriate. If there is no standard Sepedi term, include the English term in
parentheses. Aim for 100-250 words.{grade_line}{subject_line}

Learner question: {question}

Return ONLY valid JSON in this exact format:
{{
  "answer_sep": "Full answer in Sepedi...",
  "confidence_score": 0.9
}}"""


def quiz_prompt(term: str, domain: str, grade_level: int, count: int = 5) -> str:
    """Generate a quiz prompt for a STEM concept."""
    return f"""You are a Sepedi-language STEM quiz generator.
Generate {count} quiz questions for the following concept.

Concept: {term}
Domain: {domain}
Grade level: {grade_level}

Rules:
- Mix question types: fill_in_blank, multiple_choice, short_answer.
- All questions and answers must be in Sepedi (Northern Sotho).
- Multiple choice questions must have exactly 4 options.
- Include the correct answer for each question.

Return ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "question_type": "multiple_choice",
      "question_sep": "Question text in Sepedi?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A"
    }},
    {{
      "question_type": "fill_in_blank",
      "question_sep": "Mohlala wa ___ ke ___",
      "options": [],
      "correct_answer": "word"
    }}
  ]
}}"""
