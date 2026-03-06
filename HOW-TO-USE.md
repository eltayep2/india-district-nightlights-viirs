# How to Use This Pipeline

A step-by-step guide to get from zero to a complete India district-level nighttime lights dataset.

---

## Just Want the Data? (No Setup Needed)

The pre-built dataset is already included in this repo:

- **CSV** (8,333 rows = 641 districts x 13 years): [`output/csv/nightlights_district_panel.csv`](output/csv/nightlights_district_panel.csv)
- **GeoJSON** (one file per year, with district polygons): [`output/geojson/`](output/geojson/)

Clone the repo and use the data directly -- no Python, no Earth Engine, no setup required.

**You only need the rest of this guide if you want to re-run the pipeline** with custom parameters (different year range, resolution, boundary definitions, etc.).

---

## Prerequisites

- **Python 3.10 or higher** ([download](https://www.python.org/downloads/))
- **Git** ([download](https://git-scm.com/downloads))
- **A Google account** (for Earth Engine access)

---

## Step 1: Setting Up Google Earth Engine

This is the most important step. The pipeline uses Google Earth Engine (GEE) to download VIIRS satellite imagery. You need a GEE-enabled Google Cloud project.

### 1.1 Register for Earth Engine

1. Go to [https://code.earthengine.google.com/register](https://code.earthengine.google.com/register)
2. Sign in with your Google account
3. Accept the Terms of Service
4. Wait for approval (usually instant for academic/research use)

### 1.2 Create a Google Cloud Project

1. Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Sign in with the **same Google account** you used for Earth Engine
3. In the top-left, click **"Select a project"** dropdown
4. Click **"New Project"**
5. Enter a name (e.g., `nightlights-pipeline`)
6. Click **"Create"**
7. **Note your Project ID** -- it looks like `nightlights-pipeline` or `nightlights-pipeline-12345`. You will need this for the config file.

### 1.3 Enable the Earth Engine API

1. In the Google Cloud Console, go to **APIs & Services** > **Library** (or visit [https://console.cloud.google.com/apis/library](https://console.cloud.google.com/apis/library))
2. Search for **"Earth Engine"**
3. Click **"Google Earth Engine API"**
4. Click **"Enable"**
5. Wait a few seconds for it to activate

### 1.4 Authenticate (Choose One Option)

#### Option A: OAuth -- Recommended for Personal Use

This is the simplest option. Run these two commands in your terminal:

```bash
# Step 1: Authenticate (opens browser)
earthengine authenticate

# Step 2: Set your default project
earthengine set_project YOUR_PROJECT_ID
```

Replace `YOUR_PROJECT_ID` with the Project ID from Step 1.2.

When you run `earthengine authenticate`:
- Your browser will open
- Sign in with your Google account
- Click "Allow" to grant access
- You'll see a confirmation message in the terminal

#### Option B: Service Account -- For Servers or Automated Runs

Use this if you're running the pipeline on a server without a browser, or if you want fully unattended execution.

1. Go to [https://console.cloud.google.com/iam-admin/serviceaccounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Make sure your project is selected in the top dropdown
3. Click **"+ Create Service Account"**
4. Enter a name (e.g., `nightlights-sa`)
5. Click **"Create and Continue"**
6. Under "Grant this service account access to project", select the role: **Earth Engine > Earth Engine Resource Viewer**
7. Click **"Done"**
8. In the service accounts list, click your new service account
9. Go to the **"Keys"** tab
10. Click **"Add Key"** > **"Create new key"**
11. Choose **JSON** format
12. Click **"Create"** -- a JSON file will download
13. Rename the downloaded file to `sa-key.json`
14. Place it in the root of this project (next to `README.md`)
15. Register the service account email for Earth Engine:
    - Go to [https://signup.earthengine.google.com/#!/service_accounts](https://signup.earthengine.google.com/#!/service_accounts)
    - Enter the service account email (looks like `nightlights-sa@your-project.iam.gserviceaccount.com`)
    - Submit

---

## Step 2: Clone and Install

```bash
# Clone the repository
git clone https://github.com/yashveeeeeer/india-district-nightlights-viirs.git
cd india-district-nightlights-viirs

# Create a virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 3: Configure

Open `configs/config.yaml` in any text editor.

The only **required** change is setting your Google Cloud Project ID:

```yaml
nightlights:
  viirs:
    ee_project: "your-project-id-here"    # <-- CHANGE THIS
```

If you're using a **service account** (Option B above), also set:

```yaml
    ee_service_account_key: "sa-key.json"  # <-- path to your key file
```

If you're using **OAuth** (Option A above), leave it as:

```yaml
    ee_service_account_key: null           # <-- leave as null
```

### Optional Config Tweaks

| Key | Default | What It Does |
|-----|---------|-------------|
| `nightlights.years.start` | `2012` | First year to process (VIIRS data starts at 2012) |
| `nightlights.years.end` | `2024` | Last year to process |
| `nightlights.viirs.ee_scale` | `1000` | Output resolution in meters (1000m = ideal for districts) |
| `nightlights.viirs.use_earth_engine` | `true` | Set to `false` to use EOG direct download instead |
| `processing.metrics` | `[mean, median, sum, std, min, max]` | Which zonal statistics to compute |

---

## Step 4: Run the Pipeline

### Option A: One Command (Recommended)

```bash
python -m ntl_pipeline.cli run-all
```

This runs all 4 steps automatically:
1. Downloads Census 2011 district boundaries from DataMeet
2. Downloads VIIRS satellite rasters from Earth Engine (this takes the longest)
3. Computes zonal statistics per district per year
4. Exports GeoJSON files with district polygons + stats

### Option B: Step by Step

If you want more control, run each step individually:

```bash
# 1. Download district boundaries (~50 MB)
python -m ntl_pipeline.cli download-boundaries

# 2. Download VIIRS rasters from Earth Engine (~100 MB per year)
python -m ntl_pipeline.cli download-viirs

# 3. Compute zonal statistics per district
python -m ntl_pipeline.cli zonal-stats

# 4. Export year-wise GeoJSON files
python -m ntl_pipeline.cli export-geojson
```

All commands use `configs/config.yaml` by default. To use a different config: `--config path/to/your/config.yaml`

---

## Step 5: Understanding Your Output

### CSV: `output/csv/nightlights_district_panel.csv`

Each row is one district in one year. Columns:

| Column | Description |
|--------|-------------|
| `district_id` | Census 2011 district code |
| `district_name` | District name |
| `state_name` | State/UT name |
| `year` | Year (2012-2024) |
| `mean` | Mean radiance across all pixels in the district |
| `median` | Median radiance |
| `sum` | Total radiance (proxy for total economic activity) |
| `std` | Standard deviation of radiance |
| `min` | Minimum pixel radiance |
| `max` | Maximum pixel radiance |
| `valid_pixel_count` | Number of valid (non-null) pixels in the district |
| `log1p_mean` | `log(1 + mean)` -- useful for regression models |
| `log1p_median` | `log(1 + median)` -- useful for regression models |

### GeoJSON: `output/geojson/nightlights_districts_YYYY.geojson`

One file per year. Each feature is a district polygon with all the stats columns above as properties. Use these for mapping in QGIS, Kepler.gl, or any GIS tool.

---

## Step 6: Quick Analysis Examples

### Python (pandas)

```python
import pandas as pd

df = pd.read_csv("output/csv/nightlights_district_panel.csv")

# State-level average radiance by year
state_trends = df.groupby(["state_name", "year"])["mean"].mean().reset_index()
print(state_trends.head(20))

# Brightest districts in 2024
top_2024 = df[df.year == 2024].nlargest(10, "mean")[["district_name", "state_name", "mean"]]
print(top_2024)
```

### R

```r
df <- read.csv("output/csv/nightlights_district_panel.csv")

# State-level trends
library(dplyr)
state_trends <- df %>%
  group_by(state_name, year) %>%
  summarise(avg_radiance = mean(mean, na.rm = TRUE))

head(state_trends, 20)
```

### Stata

```stata
import delimited "output/csv/nightlights_district_panel.csv", clear
collapse (mean) mean, by(state_name year)
list in 1/20
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Configuration errors: nightlights.viirs.ee_project is not set` | You didn't set your project ID in config.yaml | Open `configs/config.yaml` and set `ee_project` to your Google Cloud Project ID |
| `EE default auth failed` | Earth Engine credentials not set up | Run `earthengine authenticate` and `earthengine set_project YOUR_PROJECT_ID` |
| `Service account key 'sa-key.json' not found` | Key file missing or wrong path | Place your key file in the project root, or set `ee_service_account_key: null` to use OAuth |
| `HttpError 403: Earth Engine API has not been used` | API not enabled in GCP | Go to GCP Console > APIs & Services > Enable "Google Earth Engine API" |
| `HttpError 429: Quota exceeded` | Too many requests to Earth Engine | Wait a few minutes and try again, or reduce the year range |
| `Download attempt X/3 failed` | Network issue | The pipeline retries automatically 3 times. Check your internet connection |
| `District shapefile not found` | Boundary download didn't complete | Run `python -m ntl_pipeline.cli download-boundaries` first |
| `Missing raster for YYYY` | VIIRS download didn't complete for that year | Run `python -m ntl_pipeline.cli download-viirs` first |
