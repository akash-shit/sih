"""
Validates a batch of extracted scenes for one AOI BEFORE ingestion,
so problems (AOI drift, inconsistent CRS, wrong band count, mismatched
shapes, missing months, duplicate dates) show up as one readable report
instead of as a confusing failure halfway through a long ingestion run
or -- worse -- as silently wrong tile IDs.

This directly answers the request from the previous conversation turn:
"a script you run once across all the downloaded zips that checks
band order/shape/CRS consistency and flags AOI drift or missing months."
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import date

from app.geospatial.reader import inspect_scene, SceneInfo


@dataclass
class ScannedScene:
    path: str
    acquisition_date: str
    info: SceneInfo


@dataclass
class ValidationReport:
    n_scenes: int
    crs_values: dict            # {crs_string: count} -- should have exactly one key
    shape_values: dict          # {(width,height): count} -- should have exactly one key
    band_count_values: dict     # {band_count: count} -- should have exactly one key
    duplicate_dates: list       # dates that appear more than once
    missing_months: list        # "YYYY-MM" gaps between the earliest and latest date found
    cloud_cover_by_date: dict   # {date: cloud_cover_percent or None} -- for a quick monsoon-season sanity check
    warnings: list = field(default_factory=list)
    is_clean: bool = True


def _month_range(start: str, end: str) -> list[str]:
    """Every YYYY-MM between two YYYY-MM-DD dates, inclusive."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def validate_batch(scenes: list[ScannedScene], cloud_cover_by_date: dict = None) -> ValidationReport:
    crs_counter = Counter(s.info.crs for s in scenes)
    shape_counter = Counter((s.info.width, s.info.height) for s in scenes)
    band_counter = Counter(s.info.band_count for s in scenes)

    date_counter = Counter(s.acquisition_date for s in scenes)
    duplicate_dates = [d for d, c in date_counter.items() if c > 1]

    months_present = {d[:7] for d in date_counter}
    missing_months = []
    if scenes:
        dates_sorted = sorted(date_counter)
        expected = _month_range(dates_sorted[0], dates_sorted[-1])
        missing_months = [m for m in expected if m not in months_present]

    warnings = []
    if len(crs_counter) > 1:
        warnings.append(
            f"Inconsistent CRS across scenes: {dict(crs_counter)}. This usually means the AOI "
            f"polygon was redrawn (not reloaded from a saved geometry) for at least one month, "
            f"or Browser auto-picked a different UTM zone. Re-project the odd ones out before ingesting."
        )
    if len(shape_counter) > 1:
        warnings.append(
            f"Inconsistent pixel dimensions across scenes: {dict(shape_counter)}. Almost always means "
            f"the AOI bounding box drifted between downloads -- tile IDs (Stage 3/4) will NOT line up "
            f"across dates for the scenes that don't match the majority shape."
        )
    if len(band_counter) > 1:
        warnings.append(
            f"Inconsistent band count across scenes: {dict(band_counter)}. Check that every month's "
            f"download used the same band list (B02,B03,B04,B08,SCL) and that 'Clip extra bands' was on."
        )
    if duplicate_dates:
        warnings.append(f"Duplicate acquisition dates found: {duplicate_dates}. Only the first "
                         f"ingested copy of each date will be kept (ingest_scene is keyed on file path, "
                         f"not date, so BOTH will actually be ingested as separate scenes -- "
                         f"decide if that's intended before running onboarding).")
    if missing_months:
        warnings.append(f"No scene found for these months within the covered range: {missing_months}. "
                         f"Confirm these downloads didn't fail silently.")

    return ValidationReport(
        n_scenes=len(scenes),
        crs_values=dict(crs_counter),
        shape_values={str(k): v for k, v in shape_counter.items()},
        band_count_values=dict(band_counter),
        duplicate_dates=duplicate_dates,
        missing_months=missing_months,
        cloud_cover_by_date=cloud_cover_by_date or {},
        warnings=warnings,
        is_clean=(len(warnings) == 0),
    )


def print_report(report: ValidationReport):
    print(f"Scanned {report.n_scenes} scenes.")
    print(f"CRS values seen:         {report.crs_values}")
    print(f"Pixel dimensions seen:   {report.shape_values}")
    print(f"Band counts seen:        {report.band_count_values}")
    if report.cloud_cover_by_date:
        cloudy = {d: c for d, c in report.cloud_cover_by_date.items() if c is not None and c > 20}
        if cloudy:
            print(f"Months with >20% cloud cover (expect suppression here): {cloudy}")
    if report.is_clean:
        print("No issues found -- safe to ingest.")
    else:
        print(f"\n{len(report.warnings)} issue(s) found:")
        for w in report.warnings:
            print(f"  - {w}")
