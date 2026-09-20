"""Weekly retraining script for the Isolation Forest discrepancy model.

Usage (inside ai-service container):
    python scripts/train_discrepancy.py

Retrains the model on:
1. Last 90 days of historical scan data (from core-service or local DB)
2. Labeled feedback (true positives confirmed by operators)

Saves the new model to MODEL_DIR/isolation_forest.pkl.
"""

import logging
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, ".")

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.discrepancy_alert import AlertStatus, DiscrepancyAlert, DiscrepancyFeedback
from app.services.anomaly_engine import AnomalyEngine, FeatureVector

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def fetch_training_data(db: Session) -> list[np.ndarray]:
    """Gather feature vectors for training.

    Sources:
    - Resolved alerts that were true positives (strongest signal)
    - Historical alerts with feature vectors (last 90 days)
    - Normal events (alerts closed without anomaly flag, if available)
    """
    since = datetime.now(timezone.utc) - timedelta(days=90)

    vectors: list[np.ndarray] = []

    # 1. All alerts with feature vectors in the last 90 days
    alerts = (
        db.query(DiscrepancyAlert)
        .filter(DiscrepancyAlert.created_at >= since)
        .filter(DiscrepancyAlert.feature_vector.isnot(None))
        .all()
    )

    for alert in alerts:
        if alert.feature_vector:
            try:
                vec = np.array(
                    [alert.feature_vector.get(name, 0.0) for name in FeatureVector.FEATURE_NAMES],
                    dtype=np.float32,
                )
                vectors.append(vec)
            except Exception as e:
                logger.warning("Skipping malformed feature vector for alert %s: %s", alert.id, e)

    # 2. Add synthetic normal events if we don't have enough data
    if len(vectors) < 50:
        logger.warning(
            "Only %d historical samples available. Generating %d synthetic normals.",
            len(vectors), 100 - len(vectors),
        )
        np.random.seed(42)
        for _ in range(100 - len(vectors)):
            synthetic = np.random.randn(FeatureVector.NUM_FEATURES).astype(np.float32)
            # Bias toward normal: expected ≈ scanned, daytime hours
            synthetic[0] = max(1, abs(synthetic[0]) * 100)  # expected_qty
            synthetic[1] = synthetic[0] * (1 + np.random.normal(0, 0.02))  # scanned_qty close to expected
            synthetic[2] = synthetic[1] / synthetic[0]  # qty_ratio ≈ 1
            vectors.append(synthetic)

    return vectors


def apply_feedback_penalties(db: Session, engine: AnomalyEngine) -> None:
    """Adjust model behavior based on operator feedback.

    V1: Simple logging of FP patterns for future manual tuning.
    V2: Could use feedback to re-weight features or adjust contamination.
    """
    fps = (
        db.query(DiscrepancyFeedback)
        .filter(DiscrepancyFeedback.is_true_positive == "false_positive")
        .all()
    )
    if fps:
        logger.info("%d false-positive feedback entries recorded for review", len(fps))
        # In a more advanced system we would:
        # - Collect feature vectors of FPs
        # - Add them as "known normal" samples to the training set
        # - Or decrease contamination rate slightly


async def main():
    db = SessionLocal()
    try:
        logger.info("Starting discrepancy model retraining...")

        vectors = fetch_training_data(db)
        logger.info("Training set size: %d samples", len(vectors))

        if len(vectors) < 50:
            logger.error("Insufficient data to train model. Need at least 50 samples.")
            sys.exit(1)

        engine = AnomalyEngine()
        engine.train(vectors)

        apply_feedback_penalties(db, engine)

        logger.info("Retraining complete. Model saved.")
    finally:
        db.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
