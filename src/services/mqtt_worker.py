"""MQTT worker — producer and consumer for the translation pipeline."""

import json
import logging
import os
from uuid import uuid4

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC_TRANSLATION_REQUEST = "translation.request"
MQTT_TOPIC_TRANSLATION_COMPLETED = "translation.completed"
MQTT_TOPIC_QUESTION_ANSWER_REQUEST = "question.answer.request"
MQTT_TOPIC_QUESTION_ANSWER_COMPLETED = "question.answer.completed"


class MQTTProducer:
    """Publishes translation requests to the MQTT broker."""

    def __init__(self, broker: str = MQTT_BROKER, port: int = MQTT_PORT):
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"polelo-producer-{uuid4().hex[:8]}")
        self._broker = broker
        self._port = port
        self._connected = False

    def connect(self):
        try:
            self._client.on_connect = self._on_connect
            self._client.connect(self._broker, self._port, keepalive=60)
            self._client.loop_start()
        except Exception as exc:
            logger.warning("MQTT producer connect failed: %s", exc)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        self._connected = True
        logger.info("MQTT producer connected (rc=%s)", rc)

    def publish_translation_request(self, concept_id: str, term: str, domain: str, grade_levels: list[int]):
        payload = json.dumps({
            "concept_id": concept_id,
            "term": term,
            "domain": domain,
            "grade_levels": grade_levels,
            "request_id": str(uuid4()),
        })
        result = self._client.publish(MQTT_TOPIC_TRANSLATION_REQUEST, payload, qos=1)
        logger.info("Published translation request for %s (mid=%s)", concept_id, result.mid)
        return result.mid

    def publish_question_answer_request(self, question_id: str) -> int:
        """Queue an LLM answer generation job for a learner question."""
        payload = json.dumps({
            "question_id": question_id,
            "request_id": str(uuid4()),
        })
        result = self._client.publish(MQTT_TOPIC_QUESTION_ANSWER_REQUEST, payload, qos=1)
        logger.info("Published question answer request for %s (mid=%s)", question_id, result.mid)
        return result.mid

    def publish_question_answer_completed(self, question_id: str, answer_sep: str, confidence_score: float) -> int:
        """Broadcast that an LLM answer has been persisted for a question."""
        payload = json.dumps({
            "question_id": question_id,
            "answer_sep": answer_sep,
            "confidence_score": confidence_score,
            "request_id": str(uuid4()),
        })
        result = self._client.publish(MQTT_TOPIC_QUESTION_ANSWER_COMPLETED, payload, qos=1)
        logger.info("Published question answer completed for %s (mid=%s)", question_id, result.mid)
        return result.mid

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False


class MQTTConsumer:
    """Subscribes to translation.completed and writes results to DB."""

    def __init__(self, broker: str = MQTT_BROKER, port: int = MQTT_PORT):
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"polelo-consumer-{uuid4().hex[:8]}")
        self._broker = broker
        self._port = port
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, on_message_callback=None):
        try:
            self._client.on_connect = self._on_connect
            self._client.on_message = on_message_callback or self._default_on_message
            self._client.connect(self._broker, self._port, keepalive=60)
            self._client.loop_start()
        except Exception as exc:
            logger.warning("MQTT consumer connect failed: %s", exc)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        self._connected = True
        client.subscribe(MQTT_TOPIC_TRANSLATION_COMPLETED, qos=1)
        logger.info("MQTT consumer connected and subscribed (rc=%s)", rc)

    def _default_on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info("Received translation result: %s", payload.get("concept_id", "unknown"))
        except Exception as exc:
            logger.error("Failed to process MQTT message: %s", exc)

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()
        self._connected = False
