import os
import sys
import shutil
import json
import logging
from typing import Dict, Any
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_config
from src.evaluate import evaluate_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_model_gate(
    config_path: str = "config/config.yaml",
    test_data_path: str = "data/processed/test_holdout.csv"
) -> bool:
    """
    Champion vs. Challenger automated model evaluation gate.
    Returns True if Candidate is promoted to Champion, False otherwise.
    """
    config = load_config(config_path)
    model_cfg = config.get("model", {})
    gate_cfg = config.get("gate", {})
    data_cfg = config.get("data", {})

    candidate_path = model_cfg.get("candidate_model_path", "models/candidate_model.joblib")
    champion_path = model_cfg.get("champion_model_path", "models/champion/model.joblib")
    champion_dir = os.path.dirname(champion_path)
    os.makedirs(champion_dir, exist_ok=True)

    target_col = data_cfg.get("target_column", "pm2_5")
    min_r2 = gate_cfg.get("min_r2", 0.60)
    max_rmse = gate_cfg.get("max_rmse", 50.0)
    max_r2_drop = gate_cfg.get("max_r2_drop_tolerance", 0.03)

    if not os.path.exists(candidate_path):
        logger.error(f"Candidate model artifact missing at {candidate_path}!")
        return False

    if not os.path.exists(test_data_path):
        logger.error(f"Test holdout dataset missing at {test_data_path}!")
        return False

    test_df = pd.read_csv(test_data_path)
    logger.info(f"Evaluating Candidate model on {len(test_df)} test samples...")
    candidate_metrics = evaluate_model(candidate_path, test_df, target_col=target_col)

    # CASE 1: No Champion exists yet (Cold start / initial run)
    if not os.path.exists(champion_path):
        logger.info("No Champion model currently exists. Applying absolute quality gate...")
        passed = (candidate_metrics["r2"] >= min_r2) and (candidate_metrics["rmse"] <= max_rmse)

        if passed:
            logger.info(
                f"✅ Candidate PASSED cold-start quality gate! "
                f"(R2: {candidate_metrics['r2']:.4f} >= {min_r2}, RMSE: {candidate_metrics['rmse']:.2f} <= {max_rmse})"
            )
            shutil.copyfile(candidate_path, champion_path)
            champion_metrics_path = os.path.join(champion_dir, "metrics.json")
            with open(champion_metrics_path, "w") as f:
                json.dump({"champion": candidate_metrics}, f, indent=2)
            logger.info(f"Candidate successfully promoted to Champion at {champion_path}")
            return True
        else:
            logger.error(
                f"❌ Candidate FAILED cold-start quality gate: "
                f"R2={candidate_metrics['r2']:.4f} (Required >= {min_r2}), "
                f"RMSE={candidate_metrics['rmse']:.2f} (Required <= {max_rmse})"
            )
            return False

    # CASE 2: Champion exists -> Champion vs Challenger competition
    logger.info("Evaluating existing Champion model on current test set...")
    champion_metrics = evaluate_model(champion_path, test_df, target_col=target_col)

    logger.info("--- Model Gate Comparison ---")
    logger.info(f"Champion   -> R2: {champion_metrics['r2']:.4f}, RMSE: {champion_metrics['rmse']:.2f}")
    logger.info(f"Challenger -> R2: {candidate_metrics['r2']:.4f}, RMSE: {candidate_metrics['rmse']:.2f}")

    r2_diff = candidate_metrics["r2"] - champion_metrics["r2"]
    rmse_diff = candidate_metrics["rmse"] - champion_metrics["rmse"]
    logger.info(f"Delta: R2 diff = {r2_diff:+.4f}, RMSE diff = {rmse_diff:+.2f}")

    # Challenger must beat Champion or be within acceptable tolerance without degradation
    is_r2_acceptable = candidate_metrics["r2"] >= (champion_metrics["r2"] - max_r2_drop)
    is_rmse_acceptable = candidate_metrics["rmse"] <= (champion_metrics["rmse"] * 1.05)
    beats_absolute_min = (candidate_metrics["r2"] >= min_r2) and (candidate_metrics["rmse"] <= max_rmse)

    if is_r2_acceptable and is_rmse_acceptable and beats_absolute_min:
        logger.info("✅ Challenger ACCEPTED! Promoting to new Champion...")
        # Backup old champion
        backup_path = os.path.join(champion_dir, "model_backup.joblib")
        shutil.copyfile(champion_path, backup_path)

        # Promote challenger
        shutil.copyfile(candidate_path, champion_path)
        champion_metrics_path = os.path.join(champion_dir, "metrics.json")
        with open(champion_metrics_path, "w") as f:
            json.dump({
                "champion": candidate_metrics,
                "previous_champion": champion_metrics
            }, f, indent=2)

        logger.info(f"Challenger successfully promoted to {champion_path}. Backup saved to {backup_path}.")
        return True
    else:
        logger.warning("❌ Challenger REJECTED. Champion retains production status.")
        return False


if __name__ == "__main__":
    promoted = run_model_gate()
    if not promoted:
        sys.exit(1)
    sys.exit(0)
