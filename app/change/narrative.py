"""Deterministic, evidence-only text for change candidates."""


def build_narrative(
    *,
    before_date: str,
    after_date: str,
    change_region: str | None,
    changed_fraction: float | None,
    ndvi_change: float | None,
    spectral_delta: float | None,
    embedding_drift: float | None,
    combined_score: float | None,
    quality: str | None,
    change_type: str | None,
    confidence: float | None,
    earliest_supported_date: str | None,
) -> str:
    if quality == "source_unavailable":
        return "Source imagery unavailable; no change region or heatmap was generated."
    if not change_region:
        return (
            f"Evidence was compared between {before_date} and {after_date}, but a supported "
            "difference region is unavailable."
        )

    region = f" in {change_region}" if change_region else ""
    if change_type and confidence is not None and confidence >= 0.6:
        interpretation = f"The available classifier evidence is consistent with {change_type} ({confidence:.0%} confidence)."
    else:
        interpretation = "Significant spectral/visual change detected, but change type is uncertain."

    direction = "changed"
    if ndvi_change is not None:
        direction = "increased" if ndvi_change > 0.03 else "reduced" if ndvi_change < -0.03 else "changed only slightly"
    fraction = f"{changed_fraction:.1%} of valid pixels" if changed_fraction is not None else "an unavailable percentage of valid pixels"
    earliest = f" Earliest supported date: {earliest_supported_date}." if earliest_supported_date else ""
    signals = []
    if spectral_delta is not None:
        signals.append(f"spectral delta {spectral_delta:.3f}")
    if embedding_drift is not None:
        signals.append(f"semantic drift {embedding_drift:.3f}")
    score = f" Combined score: {combined_score:.3f}." if combined_score is not None else ""
    signal_text = f" Signals: {', '.join(signals)}." if signals else ""
    return (
        f"Vegetation {direction} in the highlighted region between {before_date} and {after_date}{region}; "
        f"the detected difference covers {fraction}. {interpretation}{signal_text}{score}{earliest}"
    )
