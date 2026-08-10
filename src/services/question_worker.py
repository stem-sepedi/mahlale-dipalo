"""Question worker — consumes `question.answer.request` and persists LLM answers.

On receipt of a dispatched question it generates an answer via the Ollama LLM,
stores it in `question_answers`, updates the Forgejo issue to LLM_DONE +
HUMAN_BACKLOG, posts the answer back to the issue, and broadcasts completion on
`question.answer.completed`.
"""

import asyncio
import json
import logging
import os

import asyncpg

from src.services.mqtt_worker import (
    MQTT_TOPIC_QUESTION_ANSWER_REQUEST,
    MQTTProducer,
)

logger = logging.getLogger(__name__)


def _dsn() -> str:
    return os.getenv("DATABASE_URL", "postgresql://localhost/polelo")


async def _get_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(_dsn(), min_size=1, max_size=5)


async def handle_answer_request(payload: dict) -> dict:
    """Generate, persist, and broadcast an LLM answer for a question."""
    from src.services.forgejo_client import ForgejoClient
    from src.services.question_engine import QuestionAnswerEngine

    question_id = payload.get("question_id")
    if not question_id:
        raise ValueError("Missing question_id in payload")

    pool = await _get_pool()
    question = await pool.fetchrow("SELECT * FROM questions WHERE id = $1", question_id)
    if not question:
        raise ValueError(f"Question {question_id} not found")

    engine = QuestionAnswerEngine()
    result = await engine.answer(
        question["question_text"], question.get("grade"), question.get("subject")
    )
    answer_sep = result.get("answer_sep", "")
    confidence = float(result.get("confidence_score", 0.0))

    row = await pool.fetchrow(
        """INSERT INTO question_answers (question_id, answer_sep, confidence_score, status, generated_by)
           VALUES ($1, $2, $3, 'llm_done', 'AI Agent')
           RETURNING *""",
        question_id, answer_sep, confidence,
    )
    await pool.execute(
        "UPDATE questions SET triage_status = 'answered', updated_at = now() WHERE id = $1",
        question_id,
    )

    client = ForgejoClient()
    if client.is_configured and question.get("forgejo_issue_number"):
        try:
            label_map = await client.ensure_labels()
            await client.replace_labels(
                int(question["forgejo_issue_number"]),
                {"LLM_DONE", "HUMAN_BACKLOG"},
                label_map,
            )
            await client.post_comment(
                int(question["forgejo_issue_number"]),
                f"**Polelo LLM answer** (confidence {confidence:.2f}):\n\n{answer_sep}",
            )
        except Exception as exc:
            logger.warning("Forgejo label/comment update failed for %s: %s", question_id, exc)

    try:
        producer = MQTTProducer()
        producer.connect()
        producer.publish_question_answer_completed(question_id, answer_sep, confidence)
        producer.disconnect()
    except Exception as exc:
        logger.warning("Failed to broadcast question answer completed: %s", exc)

    logger.info("Answer persisted for question %s (confidence %.2f)", question_id, confidence)
    return {
        "question_id": question_id,
        "answer_id": str(row["id"]),
        "confidence_score": confidence,
    }


def consume_requests(stop_event=None):
    """Blocking loop subscribing to `question.answer.request`."""
    import paho.mqtt.client as mqtt

    broker = os.getenv("MQTT_BROKER", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))

    def _on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            logger.info("Question answer request: %s", data.get("question_id"))
            asyncio.run(handle_answer_request(data))
        except Exception as exc:
            logger.error("Failed to handle question answer request: %s", exc)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="polelo-question-worker")
    client.on_message = _on_message
    client.connect(broker, port, keepalive=60)
    client.subscribe(MQTT_TOPIC_QUESTION_ANSWER_REQUEST, qos=1)
    logger.info("Question worker subscribed to %s", MQTT_TOPIC_QUESTION_ANSWER_REQUEST)
    client.loop_forever()


if __name__ == "__main__":
    consume_requests()
