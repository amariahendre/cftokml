📍 Land Book Extracts → GeoJSON + KML Generator

AI-powered extraction tool for Romanian Land Registry (ANCPI / OCPI) PDFs that generates:
	•	✅ Structured parcels.json
	•	✅ GIS-ready parcels.geojson
	•	✅ Google Earth–ready parcels_all.kml
	•	✅ Single ZIP export containing all files

Built with:
	•	Streamlit
	•	OpenAI Structured Outputs
	•	PyProj
	•	Pure Python (no heavy GIS dependencies)

⸻

🚀 What This App Does
	1.	Upload one or more Romanian Land Book Extract PDFs
	2.	Uses AI structured extraction to:
	•	Extract parcel metadata
	•	Extract owners
	•	Extract encumbrances (Sarcini)
	•	Extract boundary coordinates
	•	Detect CRS (Stereo 70 → EPSG:3844)
	3.	Generates:
	•	parcels.json
	•	parcels.geojson (WGS84 / EPSG:4326)
	•	parcels_all.kml
	4.	Provides a single downloadable ZIP export

⸻

⚠️ Important Limitation

The application works only if the PDF contains boundary coordinates
(“Detalii liniare imobil” / coordinate tables).

If no coordinates are present:
	•	Geometry cannot be generated
	•	Parcel will be excluded from KML/GeoJSON

⸻

🗂 Output Files

1️⃣ parcels.json

Raw structured data extracted from the PDF.

CRS:
	•	"EPSG:3844" if Stereo 70 is detected
	•	null otherwise

⸻

2️⃣ parcels.geojson

GIS-ready file.
	•	Geometry: Polygon only
	•	CRS: EPSG:4326 (WGS84)
	•	Ready for:
	•	QGIS
	•	ArcGIS
	•	PostGIS
	•	Leaflet / Mapbox

Label points are not included (use GIS labeling engine instead).

⸻

3️⃣ parcels_all.kml

Google Earth–ready file.

Contains:
	•	Polygon geometry
	•	Centroid label point

⸻

🧠 Extraction Logic

Structured extraction rules:
	•	Uses OpenAI JSON Schema (strict mode)
	•	No hallucinated values
	•	Missing fields → null
	•	“Partea III. SARCINI – NU SUNT” → empty array
	•	Geometry:
	•	Extracted from coordinate tables
	•	Romanian number formatting converted to floats
	•	X,Y order preserved
	•	Polygon ring auto-closed for export

⸻

🛠 Installation

git clone https://github.com/your-username/your-repo.git
cd your-repo
pip install -r requirements.txt

Required packages

streamlit
openai
pyproj


⸻

🔑 API Key Setup

Recommended: create .streamlit/secrets.toml

OPENAI_API_KEY = "your-api-key-here"

Or paste key directly in the sidebar input field.

⸻

▶ Run the App

streamlit run app.py


⸻

🗺 Using GeoJSON in QGIS
	1.	Open QGIS
	2.	Layer → Add Layer → Add Vector Layer
	3.	Select parcels.geojson
	4.	Enable labeling on nr_cadastral

Project CRS can be:
	•	EPSG:3844 (Stereo 70) for cadastral precision
	•	EPSG:3857 for web mapping

⸻

🏗 Architecture

PDF Upload
   ↓
OpenAI Structured Extraction
   ↓
Validated JSON Schema
   ↓
Geometry Transformation (PyProj)
   ↓
GeoJSON (WGS84)
   ↓
KML (Google Earth)
   ↓
ZIP Export


⸻

🎯 Design Decisions

Why GeoJSON in EPSG:4326?
	•	Maximum compatibility
	•	Web standard
	•	QGIS auto-reprojects on the fly

Why no mixed geometries in GeoJSON?

QGIS handles mixed geometry inconsistently.
Production exports use:
	•	GeoJSON → Polygons only
	•	KML → Polygons + label points

⸻

📌 Future Improvements
	•	INSPIRE-compliant GML export
	•	Direct PostGIS export
	•	Area validation vs suprafata_mp
	•	Batch cadastral portfolio processing
	•	API mode (FastAPI version)

⸻

🧑‍💻 Author

Ana-Maria Hendre
AI Engineer | Data Scientist | Automation Systems

⸻

📄 License

MIT License

