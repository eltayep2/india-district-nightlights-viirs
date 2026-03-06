from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import typer
from rich import print

from .config import Config
from .boundaries import download_datameet_boundaries, load_districts
from .viirs_download import download_viirs
from .zonal import compute_zonal_stats
from .exporters import export_panel_csv, export_year_geojson

app = typer.Typer(add_completion=False)

# ---------------------------------------------------------------------------
# Path constants â€” single source of truth for data layout
# ---------------------------------------------------------------------------
DATA_RAW = Path("data/raw")
BOUNDARIES_DIR = DATA_RAW / "boundaries" / "datameet_districts_2011"
VIIRS_DIR = DATA_RAW / "viirs"

DEFAULT_CONFIG = "configs/config.yaml"


@app.command("download-boundaries")
def download_boundaries(config: Path = typer.Option(DEFAULT_CONFIG, "--config")):
    cfg = Config.load(config)
    shp = download_datameet_boundaries(cfg, DATA_RAW)
    print(f"[green]Boundaries ready:[/green] {shp}")


@app.command("download-viirs")
def download_viirs_cmd(config: Path = typer.Option(DEFAULT_CONFIG, "--config")):
    """Download VIIRS annual nightlight rasters (Earth Engine or EOG)."""
    cfg = Config.load(config)
    start = int(cfg.get("nightlights", "years", "start"))
    end = int(cfg.get("nightlights", "years", "end"))
    years = list(range(start, end + 1))

    use_ee = cfg.get("nightlights", "viirs", "use_earth_engine", default=True)
    eog_url = cfg.get("nightlights", "viirs", "eog_base_url")
    band = cfg.get("nightlights", "viirs", "product_band", default="average")
    ee_scale = int(cfg.get("nightlights", "viirs", "ee_scale", default=500))
    ee_project = cfg.get("nightlights", "viirs", "ee_project", default=None)
    ee_sa_key = cfg.get("nightlights", "viirs", "ee_service_account_key", default=None)

    paths = download_viirs(
        years=years,
        out_dir=VIIRS_DIR,
        use_earth_engine=use_ee,
        eog_base_url=eog_url,
        product_band=band,
        ee_scale=ee_scale,
        ee_project=ee_project,
        ee_sa_key=ee_sa_key,
    )
    print(f"[green]Downloaded {len(paths)} raster(s) to {VIIRS_DIR}[/green]")


@app.command("prep-rasters")
def prep_rasters(
    config: Path = typer.Option(DEFAULT_CONFIG, "--config"),
    source: str = typer.Option("viirs", "--source"),
):
    """Reproject rasters if needed (currently a no-op for VIIRS)."""
    print(
        f"[dim]prep-rasters: skipped for source={source}.[/dim]\n"
        f"[dim]  VIIRS data from Earth Engine is already in EPSG:4326.[/dim]\n"
        f"[dim]  This step is reserved for future data sources (e.g., DMSP).[/dim]"
    )


@app.command("zonal-stats")
def zonal_stats_cmd(config: Path = typer.Option(DEFAULT_CONFIG, "--config")):
    cfg = Config.load(config)
    start = int(cfg.get("nightlights", "years", "start"))
    end = int(cfg.get("nightlights", "years", "end"))
    metrics = list(cfg.get("processing", "metrics"))

    # boundaries
    shp_files = list(BOUNDARIES_DIR.glob("*.shp"))
    if not shp_files:
        print(f"[red]District shapefile not found in {BOUNDARIES_DIR}[/red]")
        print("Run first: python -m ntl_pipeline.cli download-boundaries")
        sys.exit(1)
    districts = load_districts(shp_files[0])

    # rasters
    rows = []
    for year in range(start, end + 1):
        raster_path = VIIRS_DIR / f"VIIRS_{year}.tif"
        if not raster_path.exists():
            print(f"[red]Missing raster for {year}: {raster_path}[/red]")
            print("Run first: python -m ntl_pipeline.cli download-viirs")
            sys.exit(1)
        print(f"Computing zonal stats for {year}...")
        rows.append(compute_zonal_stats(districts, raster_path, year, metrics))

    panel = pd.concat(rows, ignore_index=True)
    out_csv = Path(cfg.get("outputs", "csv_path"))
    export_panel_csv(panel, out_csv)
    print(f"[green]Wrote[/green] {out_csv}")


@app.command("export-geojson")
def export_geojson(config: Path = typer.Option(DEFAULT_CONFIG, "--config")):
    cfg = Config.load(config)
    csv_path = Path(cfg.get("outputs", "csv_path"))
    if not csv_path.exists():
        print(f"[red]Missing panel CSV: {csv_path}[/red]")
        print("Run first: python -m ntl_pipeline.cli zonal-stats")
        sys.exit(1)

    shp_files = list(BOUNDARIES_DIR.glob("*.shp"))
    if not shp_files:
        print(f"[red]District shapefile not found in {BOUNDARIES_DIR}[/red]")
        print("Run first: python -m ntl_pipeline.cli download-boundaries")
        sys.exit(1)
    districts = load_districts(shp_files[0])

    df = pd.read_csv(csv_path)
    out_dir = Path(cfg.get("outputs", "geojson_dir"))
    for year, ydf in df.groupby("year"):
        out_path = out_dir / f"nightlights_districts_{int(year)}.geojson"
        export_year_geojson(districts, ydf, out_path)
        print(f"[green]Wrote[/green] {out_path}")


def _preflight(cfg: Config, config_path: Path):
    """Run pre-flight checks before starting the full pipeline."""
    print("[bold]Pre-flight checks...[/bold]")

    # Config is already validated by Config.load(), but let's summarize
    start = int(cfg.get("nightlights", "years", "start"))
    end = int(cfg.get("nightlights", "years", "end"))
    years = list(range(start, end + 1))
    use_ee = cfg.get("nightlights", "viirs", "use_earth_engine", default=True)
    ee_project = cfg.get("nightlights", "viirs", "ee_project")

    print(f"  Config     : {config_path}")
    print(f"  Years      : {start}-{end} ({len(years)} years)")
    print(f"  Strategy   : {'Earth Engine' if use_ee else 'EOG direct download'}")
    if use_ee:
        print(f"  GCP Project: {ee_project}")
    print(f"  CSV output : {cfg.get('outputs', 'csv_path')}")
    print(f"  GeoJSON dir: {cfg.get('outputs', 'geojson_dir')}")

    # Test EE auth early so we fail fast (before downloading boundaries)
    if use_ee:
        print("\n  Testing Earth Engine connection...")
        try:
            from .viirs_download import _ee_init
            sa_key = cfg.get("nightlights", "viirs", "ee_service_account_key", default=None)
            _ee_init(project=ee_project, sa_key_path=sa_key)
            print("  [green]Earth Engine: OK[/green]")
        except Exception as e:
            print(f"  [red]Earth Engine auth failed: {e}[/red]")
            print("  Fix your credentials before running the pipeline.")
            print("  See HOW-TO-USE.md for setup instructions.")
            sys.exit(1)

    print()


@app.command("run-all")
def run_all(config: Path = typer.Option(DEFAULT_CONFIG, "--config")):
    """Run the full pipeline end-to-end: boundaries -> VIIRS -> zonal stats -> GeoJSON."""
    cfg = Config.load(config)

    _preflight(cfg, config)

    print("[bold]Step 1/4: Downloading district boundaries...[/bold]")
    download_boundaries(config)

    print("\n[bold]Step 2/4: Downloading VIIRS rasters...[/bold]")
    download_viirs_cmd(config)

    print("\n[bold]Step 3/4: Computing zonal statistics...[/bold]")
    zonal_stats_cmd(config)

    print("\n[bold]Step 4/4: Exporting GeoJSON files...[/bold]")
    export_geojson(config)

    print(f"\n[bold green]Done![/bold green]")
    print(f"  CSV  : {cfg.get('outputs', 'csv_path')}")
    print(f"  JSON : {cfg.get('outputs', 'geojson_dir')}/")


def main():
    app()


if __name__ == "__main__":
    main()
