"""
Reference Implementation: Multi-Stage Contextual Metadata Verification Gates
& Dynamic Risk-Weighted Threshold Calibration for Restricted Party Screening (RPS)
Author: Mohammad Haider Talat (ORCID: 0009-0007-8781-9623)
License: MIT
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ScreeningPayload:
    entity_name: str
    raw_lexical_score: float          # S_raw in [0.0, 1.0]
    has_distinct_statutory_id: bool   # Gate 1: LEI / DUNS / VAT / Registry mismatch
    geospatial_divergence: float      # Gate 2: Normalized physical distance score [0.0, 1.0]
    verified_role_continuity: float   # Gate 3: Historical audited relationship score [0.0, 1.0]
    jurisdiction_risk_index: float    # R_geo in [0.0, 1.0]
    item_control_sensitivity: float   # R_ind in [0.0, 1.0] (ECCN / Dual-use sensitivity)


def compute_metadata_confidence(
    payload: ScreeningPayload,
    w1: float = 0.45,
    w2: float = 0.35,
    w3: float = 0.20,
) -> float:
    """Computes aggregate non-lexical metadata disambiguation confidence C_meta."""
    c1 = 1.0 if payload.has_distinct_statutory_id else 0.0
    c2 = max(0.0, min(1.0, payload.geospatial_divergence))
    c3 = max(0.0, min(1.0, payload.verified_role_continuity))
    return round((w1 * c1) + (w2 * c2) + (w3 * c3), 4)


def calibrate_effective_threshold(
    c_meta: float,
    r_geo: float,
    r_ind: float,
    t_base: float = 0.80,
    alpha: float = 0.15,
    beta: float = 0.10,
    gamma: float = 0.18,
    t_min: float = 0.65,
    t_max: float = 0.96,
) -> float:
    """
    Computes transaction-specific decision threshold:
    T_eff = clamp(T_base - alpha * R_geo - beta * R_ind + gamma * C_meta, T_min, T_max)
    """
    raw_threshold = t_base - (alpha * r_geo) - (beta * r_ind) + (gamma * c_meta)
    return round(max(t_min, min(t_max, raw_threshold)), 4)


def adjudicate_screening_hit(payload: ScreeningPayload) -> Dict[str, Any]:
    """Evaluates raw lexical score against dynamically calibrated threshold."""
    if payload.raw_lexical_score < 0.65:
        return {"decision": "AUTO_RELEASE_PREFILTER", "raw_score": payload.raw_lexical_score}

    c_meta = compute_metadata_confidence(payload)
    t_eff = calibrate_effective_threshold(
        c_meta=c_meta,
        r_geo=payload.jurisdiction_risk_index,
        r_ind=payload.item_control_sensitivity,
    )

    decision = "HOLD_FOR_COMPLIANCE_REVIEW" if payload.raw_lexical_score >= t_eff else "AUTO_RELEASE_VERIFIED"
    return {
        "entity": payload.entity_name,
        "decision": decision,
        "raw_lexical_score": payload.raw_lexical_score,
        "metadata_confidence_c_meta": c_meta,
        "calibrated_threshold_t_eff": t_eff,
    }


if __name__ == "__main__":
    sample_tx = ScreeningPayload(
        entity_name="Apex Precision Components GmbH",
        raw_lexical_score=0.84,
        has_distinct_statutory_id=True,
        geospatial_divergence=0.92,
        verified_role_continuity=0.88,
        jurisdiction_risk_index=0.10,
        item_control_sensitivity=0.15,
    )
    print(adjudicate_screening_hit(sample_tx))
