from collections import defaultdict
from pathlib import Path
import re

import rasterio


_DATE_RE = re.compile(r"(20\d{2})[-_](\d{1,2})[-_](\d{1,2})")
_BAND_RE = re.compile(r"_B(02|03|04|08)_", re.IGNORECASE)


def _date_for(path: Path) -> str | None:
    match = _DATE_RE.search(path.parent.name) or _DATE_RE.search(path.name)
    if not match:
        return None
    year, month, day = (int(value) for value in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}"


def assemble_prepared_stacks(source_folder: Path, staging_dir: Path) -> list[Path]:
    staging_dir.mkdir(parents=True, exist_ok=True)
    groups: dict[str, dict[str, Path]] = defaultdict(dict)
    for path in sorted(source_folder.rglob("*")):
        if path.suffix.lower() not in {".tif", ".tiff"}:
            continue
        match = _BAND_RE.search(path.name)
        date = _date_for(path)
        if match and date:
            groups[date][f"B{match.group(1)}"] = path

    stacks = []
    for date in sorted(groups):
        bands = groups[date]
        if set(bands) != {"B02", "B03", "B04", "B08"}:
            continue
        output = staging_dir / f"prepared_{date}_multispectral.tif"
        if output.exists() and output.stat().st_mtime >= max(path.stat().st_mtime for path in bands.values()):
            stacks.append(output)
            continue
        with rasterio.open(bands["B02"]) as reference:
            profile = reference.profile.copy()
            profile.update(count=4, driver="GTiff")
            with rasterio.open(output, "w", **profile) as destination:
                for index, key in enumerate(("B02", "B03", "B04", "B08"), start=1):
                    with rasterio.open(bands[key]) as source:
                        if (source.crs, source.transform, source.width, source.height) != (
                            reference.crs, reference.transform, reference.width, reference.height
                        ):
                            raise ValueError(f"Inconsistent geospatial headers for {date}: {bands[key]}")
                        destination.write(source.read(1), index)
                destination.update_tags(
                    band_order="B02,B03,B04,B08",
                    scl_available="false",
                    source_files=";".join(str(bands[key]) for key in ("B02", "B03", "B04", "B08")),
                )
        stacks.append(output)
    return stacks