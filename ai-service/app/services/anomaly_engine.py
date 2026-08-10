"""Anomaly detection engine for receiving discrepancies.

Uses Isolation Forest (scikit-learn) to flag unusual receiving patterns:
- Unexpected quantity variance (SHORT / EXCESS)
- Unusual supplier/item combinations
- Timing anomalies (off-hours, weekend deliveries)

V1: Tabular features + Isolation Forest
V2 (future): Autoencoder or LLM classifier for rich text context
"""

import json
import logging
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import httpx
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.config import settings
from app.models.discrepancy_alert import AlertSeverity, AlertStatus, DiscrepancyAlert

logger = logging.getLogger(__name__)

# Model checkpoint path
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/tmp/ai-models"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = MODEL_DIR / "isolation_forest.pkl"


class FeatureVector:
    """Feature extraction for a receiving event."""

    # Feature order matters — must match training
    FEATURE_NAMES = [
        "expected_qty",
        "scanned_qty",
        "qty_ratio",
        "hour_of_day_sin",
        "hour_of_day_cos",
        "day_of_week_sin",
        "day_of_week_cos",
        "item_category_encoded",
        "supplier_encoded",
        "dock_location_encoded",
        "operator_tenure_days",
        "vehicle_type_encoded",
        "asn_line_count",
        "avg_line_qty",
    ]
    NUM_FEATURES = len(FEATURE_NAMES)

    def __init__(self, raw_data: dict[str, Any]):
        self.raw = raw_data
        self.vector = self._build()

    def _build(self) -> np.ndarray:
        """Convert raw receiving event into a normalized feature vector."""
        d = self.raw

        expected = float(d.get("expected_qty", 0) or 0)
        scanned = float(d.get("scanned_qty", 0) or 0)
        qty_ratio = scanned / expected if expected > 0 else 1.0

        # Cyclical time encoding
        ts = d.get("scan_timestamp")
        if ts:
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            hour = ts.hour
            dow = ts.weekday()
        else:
            hour = 12
            dow = 0

        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        dow_sin = np.sin(2 * np.pi * dow / 7)
        dow_cos = np.cos(2 * np.pi * dow / 7)

        # Categoricals — simple hash-based encoding for V1
        # In production these should be learned embeddings or label encoders
        def _hash_encode(val: str, buckets: int = 100) -> float:
            if not val:
                return 0.0
            return (hash(val) % buckets) / buckets

        features = [
            expected,
            scanned,
            qty_ratio,
            hour_sin,
            hour_cos,
            dow_sin,
            dow_cos,
            _hash_encode(d.get("item_category")),
            _hash_encode(d.get("supplier_id")),
            _hash_encode(d.get("dock_location")),
            float(d.get("operator_tenure_days", 0) or 0),
            _hash_encode(d.get("vehicle_type")),
            float(d.get("asn_line_count", 1) or 1),
            float(d.get("avg_line_qty", expected) or expected),
        ]
        return np.array(features, dtype=np.float32)

    def to_dict(self) -> dict[str, Any]:
        return {name: float(val) for name, val in zip(self.FEATURE_NAMES, self.vector)}


class AnomalyEngine:
    """Train and run Isolation Forest for discrepancy detection."""

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model: Optional[IsolationForest] = None
        self._load_model()

    def _load_model(self) -> None:
        if MODEL_PATH.exists():
            try:
                with open(MODEL_PATH, "rb") as f:
                    self.model = pickle.load(f)
                logger.info("Loaded Isolation Forest model from %s", MODEL_PATH)
            except Exception as e:
                logger.warning("Failed to load model: %s", e)
                self.model = None

    def _save_model(self) -> None:
        if self.model:
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(self.model, f)
            logger.info("Saved Isolation Forest model to %s", MODEL_PATH)

    def is_trained(self) -> bool:
        return self.model is not None

    def train(self, feature_vectors: list[np.ndarray]) -> None:
        """Train (or retrain) the Isolation Forest on historical data.

        Args:
            feature_vectors: list of 1-D numpy arrays (one per historical event)
        """
        if len(feature_vectors) < 50:
            logger.warning("Insufficient data (%d samples) to train model", len(feature_vectors))
            return

        X = np.vstack(feature_vectors)
        logger.info("Training Isolation Forest on %d samples, %d features", X.shape[0], X.shape[1])

        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(X)
        self._save_model()

    def predict(self, feature_vector: np.ndarray) -> dict[str, Any]:
        """Score a single receiving event.

        Returns:
            {
                "anomaly_score": float,  # raw Isolation Forest decision function score
                "is_anomaly": bool,
                "severity": str,  # low | medium | high | critical
                "confidence": float,  # 0-1
            }
        """
        if self.model is None:
            return {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "severity": "low",
                "confidence": 0.0,
                "message": "Model not trained yet — insufficient historical data",
            }

        # Decision function: negative = more anomalous
        score = float(self.model.decision_function(feature_vector.reshape(1, -1))[0])

        # Isolation Forest threshold (lower = more anomalous)
        is_anomaly = score < -0.6

        # Severity bands
        if score < -0.8:
            severity = AlertSeverity.CRITICAL
        elif score < -0.6:
            severity = AlertSeverity.HIGH
        elif score < -0.4:
            severity = AlertSeverity.MEDIUM
        else:
            severity = AlertSeverity.LOW

        # Confidence: how far from 0 (normal boundary)
        confidence = min(1.0, abs(score) / 0.8)

        return {
            "anomaly_score": score,
            "is_anomaly": is_anomaly,
            "severity": severity.value,
            "confidence": confidence,
        }

    async def detect(
        self,
        scan_data: dict[str, Any],
        db: Session,
        organization_id: Optional[UUID] = None,
        warehouse_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Full detection pipeline: feature extraction → model inference → alert creation.

        Returns the prediction result + alert_id if an anomaly was flagged.
        """
        # Build feature vector
        fv = FeatureVector(scan_data)
        result = self.predict(fv.vector)

        alert_id = None
        if result["is_anomaly"]:
            alert = DiscrepancyAlert(
                scan_session_id=scan_data.get("scan_session_id"),
                asn_order_id=scan_data.get("asn_order_id"),
                asn_order_number=scan_data.get("asn_order_number"),
                organization_id=organization_id,
                warehouse_id=warehouse_id,
                anomaly_score=result["anomaly_score"],
                severity=AlertSeverity(result["severity"]),
                alert_type=scan_data.get("alert_type", "pattern_anomaly"),
                suggested_action=self._suggest_action(scan_data, result),
                feature_vector=fv.to_dict(),
                status=AlertStatus.OPEN,
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            alert_id = alert.id
            logger.warning(
                "Discrepancy alert created: id=%s score=%.3f severity=%s",
                alert_id, result["anomaly_score"], result["severity"],
            )

        return {
            **result,
            "alert_id": str(alert_id) if alert_id else None,
            "feature_vector": fv.to_dict(),
        }

    @staticmethod
    def _suggest_action(scan_data: dict, result: dict) -> str:
        """Generate a human-readable suggested action based on the anomaly type."""
        expected = scan_data.get("expected_qty", 0)
        scanned = scan_data.get("scanned_qty", 0)

        if scanned < expected:
            return f"SHORT detected: expected {expected}, scanned {scanned}. Recommend recount and flag supplier."
        if scanned > expected:
            return f"EXCESS detected: expected {expected}, scanned {scanned}. Recommend recount and verify ASN."
        if result["severity"] in ("high", "critical"):
            return "Unusual receiving pattern detected. Recommend supervisor review before put-away."
        return "Anomaly detected. Verify quantities and check for damage before proceeding."


def get_anomaly_engine() -> AnomalyEngine:
    """Factory: return an AnomalyEngine instance."""
    return AnomalyEngine()
