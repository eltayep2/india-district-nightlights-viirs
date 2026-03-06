from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats


def compute_zonal_stats(
    districts: gpd.GeoDataFrame,
    raster_path: Path,
    year: int,
    metrics: List[str],
    nodata: float | int | None = None,
) -> pd.DataFrame:
    with rasterio.open(raster_path) as src:
        if nodata is None:
            nodata = src.nodata

    # Include "count" in the single pass to avoid processing the raster twice
    stats_to_compute = list(metrics)
    if "count" not in stats_to_compute:
        stats_to_compute.append("count")

    zs = zonal_stats(
        districts,
        raster_path,
        stats=stats_to_compute,
        nodata=nodata,
        geojson_out=False,
        all_touched=False,
    )

    out = pd.DataFrame(zs)
    out.insert(0, "year", year)
    out.insert(0, "district_id", districts["district_id"].astype(str).values)
    out.insert(1, "district_name", districts["district_name"].values)
    out.insert(2, "state_name", districts["state_name"].values)

    # Extract valid pixel count from the single pass
    if "count" in out.columns:
        out["valid_pixel_count"] = out.pop("count").astype(float)
    else:
        out["valid_pixel_count"] = np.nan

    # Interpretable transforms
    for col in ["mean", "median"]:
        if col in out.columns:
            out[f"log1p_{col}"] = np.log1p(out[col].astype(float))

    return out
