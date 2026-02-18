# Land Book Extracts → JSON / GeoJSON / KML (Streamlit)

AI-powered extractor for Romanian cadastral / land-registry PDFs (ANCPI / OCPI).  
Upload one or more Land Book Extract PDFs and download a single ZIP containing:

- `parcels.json` (structured, schema-validated)
- `parcels.geojson` (GIS-ready)
- `parcels_all.kml` (Google Earth-ready)

---

## What this app does

1. **Uploads one or multiple cadastral PDF documents** (Land Book Extracts)
2. **Uses OpenAI Structured Outputs (JSON Schema enforced)** to extract:
   - parcel metadata (IE, cadastral number, locality/county, land use, surface, etc.)
   - owner(s)
   - encumbrances (Sarcini / Partea III)
   - boundary coordinates (`points_xy`)
   - coordinate reference system (Stereo 70 → `EPSG:3844` when mentioned)
3. **Generates geospatial outputs**
   - transforms coordinates to WGS84 (`EPSG:4326`)
   - builds polygons and exports KML + GeoJSON
4. **Downloads everything in one click** as a ZIP.

---

## Important limitation (required input)

⚠️ This app works **only if the uploaded PDF contains boundary coordinates**  
(e.g. **“Detalii liniare imobil” / coordinate tables**).

If the extract does **not** include coordinate tables, the parcel **cannot** be converted to **KML/GeoJSON**.

---

## Outputs

### `parcels.json`
A validated JSON object with:
- `crs`: detected CRS (or `null`)
- `parcels`: list of parcel objects including `points_xy`

### `parcels.geojson`
A `FeatureCollection` with Polygon features (and optional label points—currently disabled).

### `parcels_all.kml`
Google Earth compatible KML with:
- parcel polygons
- a centroid label point per parcel

### ZIP bundle
The app produces a single download:
- `parcels_export.zip` containing all three files.

---

## Coordinate Reference System (CRS)

- If the PDF mentions **Stereo 70**, the extractor outputs `crs="EPSG:3844"`.
- If CRS cannot be detected, the app uses a **fallback** for transforms:
  - `EPSG:3844` (Stereo 70)

Geospatial outputs are generated in:
- `EPSG:4326` (WGS84 lon/lat)

---

## Tech stack

- **Python**
- **Streamlit**
- **OpenAI Responses API** (Structured Outputs / JSON Schema)
- **pyproj** (CRS transformations)
- **KML/XML generation**
- **GeoJSON generation**
- **zipfile / io** (single-click ZIP download)

---

## License

Choose a license for your repository (e.g., MIT). Add a LICENSE file if needed.

⸻

## Author

Ana-Maria Hendre
Data Scientist / AI Engineer
