import json
import time
import streamlit as st
from pyproj import Transformer
from xml.sax.saxutils import escape
import io
import zipfile
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from mistralai.client import Mistral  # mistralai v2.x
    MISTRAL_AVAILABLE = True
except ImportError:
    try:
        from mistralai import Mistral  # mistralai v1.x fallback
        MISTRAL_AVAILABLE = True
    except ImportError:
        MISTRAL_AVAILABLE = False


# KML helpers

def ring_lonlat(points_xy, transformer):
    coords = [transformer.transform(x, y) for x, y in points_xy]
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords

def centroid_avg(coords):
    pts = coords[:-1] if len(coords) > 1 else coords
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return lon, lat

def esc(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return escape("; ".join(str(x) for x in v))
    if isinstance(v, dict):
        return escape(str(v))
    return escape(str(v))

def sarcini_names(p):
    sarcini = p.get("sarcini") or []
    names = []
    for s in sarcini:
        if isinstance(s, dict):
            d = s.get("descriere")
            if d:
                names.append(str(d))
    return "; ".join(names)

def build_description(p):
    return f"""
<b>CF:</b> {escape(str(p.get('nr_cadastral')))}<br/>
<b>Proprietar:</b> {escape((p.get('proprietar') or ''))}<br/>
<b>Localitate:</b> {escape((p.get('localitate') or ''))}<br/>
<b>Județ:</b> {escape((p.get('judet') or ''))}<br/>
<b>Detalii:</b> {escape((p.get('observatii') or ''))}<br/>
<b>Sarcini (denumire):</b> {esc(sarcini_names(p))}<br/>
"""

def json_dict_to_kml(data, crs_from="EPSG:3844"):
    transformer = Transformer.from_crs(crs_from, "EPSG:4326", always_xy=True)
    placemarks = []

    for p in data.get("parcels", []):
        pts = p.get("points_xy") or []
        if len(pts) < 3:
            continue

        coords = ring_lonlat(pts, transformer)
        poly_coords = "\n".join(f"{lon},{lat},0" for lon, lat in coords)

        lon_c, lat_c = centroid_avg(coords)
        label = f'{p.get("nr_cadastral")}'
        desc = build_description(p)

        placemarks.append(f"""
  <Placemark>
    <name>Parcel {escape(str(p.get("nr_cadastral")))}</name>
    <description><![CDATA[{desc}]]></description>
    <styleUrl>#polyStyle</styleUrl>
    <Polygon>
      <tessellate>1</tessellate>
      <outerBoundaryIs>
        <LinearRing>
          <coordinates>
{poly_coords}
          </coordinates>
        </LinearRing>
      </outerBoundaryIs>
    </Polygon>
  </Placemark>

  <Placemark>
    <name>{escape(label)}</name>
    <description><![CDATA[{desc}]]></description>
    <styleUrl>#labelStyle</styleUrl>
    <Point>
      <coordinates>{lon_c},{lat_c},0</coordinates>
    </Point>
  </Placemark>
""")

    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Parcele</name>

  <Style id="polyStyle">
    <LineStyle>
      <width>2</width>
    </LineStyle>
    <PolyStyle>
      <color>61FAFF7F</color>
      <outline>1</outline>
    </PolyStyle>
  </Style>

  <Style id="labelStyle">
    <LabelStyle>
      <scale>1.3</scale>
    </LabelStyle>
    <IconStyle>
      <scale>0</scale>
    </IconStyle>
  </Style>

{''.join(placemarks)}
</Document>
</kml>
"""
    return kml


# GeoJSON helpers

def ensure_ring(coords):
    if coords and coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    return coords

def parcel_properties(p):
    props = dict(p)
    props.pop("points_xy", None)
    return props

def json_dict_to_geojson(data, crs_from="EPSG:3844", out_crs="EPSG:4326", include_label_points=True):
    transformer = Transformer.from_crs(crs_from, out_crs, always_xy=True)
    features = []

    for p in data.get("parcels", []):
        pts = p.get("points_xy") or []
        if len(pts) < 3:
            continue

        ring = [transformer.transform(x, y) for x, y in pts]
        ring = ensure_ring(ring)
        poly_coords = [[[lon, lat] for lon, lat in ring]]
        props = parcel_properties(p)

        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": poly_coords}
        })

        if include_label_points:
            lon_c, lat_c = centroid_avg(ring)
            features.append({
                "type": "Feature",
                "properties": {**props, "feature_type": "label_point"},
                "geometry": {"type": "Point", "coordinates": [lon_c, lat_c]}
            })

    return {
        "type": "FeatureCollection",
        "name": "parcels",
        "crs": {"type": "name", "properties": {"name": out_crs}},
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "features": features
    }


# JSON schema for structured output

PARCEL_SCHEMA_ONLY = {
    "type": "object",
    "properties": {
      "crs": {"type": ["string", "null"]},
      "parcels": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "IE": {"type": ["string", "null"]},
            "nr_cadastral": {"type": ["integer", "null"]},
            "proprietar": {"type": ["string", "null"]},
            "localitate": {"type": ["string", "null"]},
            "judet": {"type": ["string", "null"]},
            "categorie_folosinta": {"type": ["string", "null"]},
            "intravilan": {"type": ["boolean", "null"]},
            "suprafata_mp": {"type": ["integer", "null"]},
            "tarla": {"type": ["string", "null"]},
            "parcela": {"type": ["string", "null"]},
            "nr_topo": {"type": ["string", "null"]},
            "observatii": {"type": ["string", "null"]},
            "sarcini": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "tip": {"type": ["string", "null"]},
                  "descriere": {"type": ["string", "null"]},
                  "act": {"type": ["string", "null"]},
                  "data": {"type": ["string", "null"]},
                  "referinta": {"type": ["string", "null"]}
                },
                "required": ["tip","descriere","act","data","referinta"],
                "additionalProperties": False
              }
            },
            "points_xy": {
              "type": "array",
              "items": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"type": "number"}
              }
            }
          },
          "required": [
            "IE","nr_cadastral","proprietar","localitate","judet",
            "categorie_folosinta","intravilan","suprafata_mp","tarla","parcela",
            "nr_topo","observatii","sarcini","points_xy"
          ],
          "additionalProperties": False
        }
      }
    },
    "required": ["crs","parcels"],
    "additionalProperties": False
}

EXTRACTION_PROMPT = """You are an expert Romanian cadastral / land-registry document extraction agent (ANCPI / OCPI "Extras de Carte Funciară", "Anexa", "Detalii liniare imobil").

TASK
Extract structured data from the provided PDF and return ONLY valid JSON that matches the schema.
- Use ONLY information explicitly present in the PDF.
- Do NOT hallucinate values.
- If a field is missing/unclear, set it to null.
- If "Partea III. SARCINI" states "NU SUNT", set "sarcini": [].

SARCINI RULES (CRITICAL)
- For each entry in "Partea III. SARCINI", create ONE object in "sarcini".
- "tip":
  - Use a short label ONLY if explicitly stated (e.g. "ipotecă", "servitute", "interdicție").
- "descriere":
  - Extract ONLY the NAME of the creditor / beneficiary / holder if present.
  - This is usually the line starting with "1)", "2)", etc.
  - DO NOT include act numbers, dates, values, legal text, or the word "Intabulare".
  - If no explicit name is listed, set "descriere": null.
- "act", "data", "referinta":
  - Extract ONLY if explicitly present; otherwise set to null.
- If "Partea III. SARCINI" states "NU SUNT", set "sarcini": [].

CRS RULE
- If the PDF mentions "Stereo 70", output: "crs": "EPSG:3844".
- Otherwise set "crs" to null.

GEOMETRY RULES (points_xy)
- Extract boundary coordinates from "DETALII LINIARE IMOBIL" / segment tables.
- Convert Romanian number formatting to floats (e.g., "576.907,216" => 576907.216).
- Keep X,Y order as written.
- Use each unique vertex once, in the order implied by the boundary listing.
- Do not invent points. Do not reorder.
- Do not explicitly close the polygon unless the document explicitly closes it.

OWNER RULES
- Extract owner names exactly as written (with diacritics).
- If multiple owners, separate with "; ".

OBSERVATII RULES
- Create a concise observation string ONLY from document facts (e.g., extravilan/intravilan, category of use, surface, tarla/parcela).

Return exactly ONE parcel inside parcels[] for this PDF.
"""


# OpenAI extraction

def extract_one_pdf_openai(client: "OpenAI", pdf_bytes: bytes, filename: str, model: str) -> dict:
    up = client.files.create(
        file=(filename, pdf_bytes, "application/pdf"),
        purpose="assistants"
    )

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": EXTRACTION_PROMPT},
                    {"type": "input_file", "file_id": up.id},
                ],
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "parcels_schema",
                "schema": PARCEL_SCHEMA_ONLY,
                "strict": True
            }
        },
    )

    return json.loads(resp.output_text)


# Mistral extraction: two-step OCR then structured chat extraction

def _mistral_call_with_retry(fn, max_retries=4):
    """Retry a Mistral API call on 429 rate-limit errors with exponential backoff."""
    delay = 15
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if "1300" in str(e) or "429" in str(e) or "rate_limit" in str(e).lower():
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
            raise
    return fn()

def extract_one_pdf_mistral(client: "Mistral", pdf_bytes: bytes, filename: str, model: str) -> dict:
    # Step 1: OCR the PDF using the dedicated OCR endpoint
    uploaded = client.files.upload(
        file={"file_name": filename, "content": pdf_bytes},
        purpose="ocr",
    )
    signed = client.files.get_signed_url(file_id=uploaded.id)

    ocr_result = _mistral_call_with_retry(
        lambda: client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "document_url", "document_url": signed.url},
        )
    )

    pages_text = "\n\n".join(
        getattr(page, "markdown", "") or ""
        for page in (ocr_result.pages or [])
    )

    # Step 2: extract structured JSON from the OCR text using a chat model
    resp = _mistral_call_with_retry(
        lambda: client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": f"{EXTRACTION_PROMPT}\n\n---\nDOCUMENT TEXT:\n{pages_text}",
                }
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "parcels_schema",
                    "schema": PARCEL_SCHEMA_ONLY,
                    "strict": True,
                },
            },
        )
    )

    return json.loads(resp.choices[0].message.content)


# Streamlit UI

st.set_page_config(page_title="Land Book Extracts → KML/GeoJSON", layout="wide")
st.title("Land Book Extracts → KML + GeoJSON")

with st.sidebar:
    st.header("Settings")

    provider = st.radio(
        "AI Provider",
        options=["OpenAI", "Mistral"],
        horizontal=True,
    )

    if provider == "OpenAI":
        if not OPENAI_AVAILABLE:
            st.error("openai package not installed. Run: pip install openai")
        api_key = st.text_input(
            "OpenAI API key",
            type="password",
            value="",
            help="Recommended: set OPENAI_API_KEY in .streamlit/secrets.toml",
        )
        model = st.text_input(
            "Model",
            value="gpt-4.1-mini",
            help="e.g. gpt-4.1-mini, gpt-4o",
        )
    else:
        if not MISTRAL_AVAILABLE:
            st.error("mistralai package not installed. Run: pip install mistralai")
        api_key = st.text_input(
            "Mistral API key",
            type="password",
            value="",
            help="Recommended: set MISTRAL_API_KEY in .streamlit/secrets.toml",
        )
        model = st.text_input(
            "Extraction model",
            value="mistral-small-latest",
            help="Chat model used for structured extraction. OCR is always performed with mistral-ocr-latest. e.g. mistral-small-latest, mistral-large-latest",
        )

    st.divider()
    st.markdown("""
### About
This application extracts parcel data from Romanian Land Registry PDFs (ANCPI / OCPI)
and generates structured JSON, GeoJSON and KML files.

⚠️ **Important limitation:**
The application works only if the uploaded extract contains boundary coordinates
("Detalii liniare imobil" / coordinate tables).
If no coordinates are present in the document, the parcel cannot be converted into KML/GeoJSON.
""")

    st.divider()
    st.header("What the app does")
    st.text("""
    1. Uploads one or multiple cadastral PDF documents (Land Book Extracts)

    2. Uses AI structured extraction to:
       - Identify parcel metadata
       - Extract owners
       - Extract encumbrances (Sarcini)
       - Extract boundary coordinates
       - Detect coordinate reference system (Stereo 70 -> EPSG:3844)

    3. Generates:
       - Clean, validated JSON and GeoJSON files
       - Ready-to-use .kml file for Google Earth
""")


uploaded = st.file_uploader(
    "Upload one or more PDFs (Land Book Extracts)",
    type=["pdf"],
    accept_multiple_files=True,
)

provider_ready = (provider == "OpenAI" and OPENAI_AVAILABLE) or (provider == "Mistral" and MISTRAL_AVAILABLE)
run_btn = st.button(
    "Generate parcels.json + GeoJSON + KML (ZIP)",
    type="primary",
    disabled=not (uploaded and api_key and provider_ready),
)

if run_btn:
    parcels = []
    crs_values = []
    errors = []

    if provider == "OpenAI":
        client = OpenAI(api_key=api_key)
        extract_fn = extract_one_pdf_openai
    else:
        client = Mistral(api_key=api_key)
        extract_fn = extract_one_pdf_mistral

    with st.spinner(f"Processing PDFs with {provider} AI..."):
        for f in uploaded:
            try:
                data_one = extract_fn(client, f.read(), f.name, model=model)
                crs_values.append(data_one.get("crs"))
                parcels.extend(data_one.get("parcels", []))
            except Exception as e:
                errors.append((f.name, str(e)))

    combined_crs = (
        "EPSG:3844"
        if any(c == "EPSG:3844" for c in crs_values)
        and not any((c is not None and c != "EPSG:3844") for c in crs_values)
        else None
    )

    data = {"crs": combined_crs, "parcels": parcels}

    st.success(f"Extracted {len(parcels)} parcel(s) from {len(uploaded)} PDF(s).")

    if errors:
        st.warning("Some files failed during extraction:")
        for name, err in errors:
            st.write(f"- {name}: {err}")

    parcels_json_bytes = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    crs_for_transform = data.get("crs") or "EPSG:3844"

    try:
        with st.spinner("Generating KML + GeoJSON..."):
            kml_text = json_dict_to_kml(data, crs_from=crs_for_transform)
            kml_bytes = kml_text.encode("utf-8")

            geojson_obj = json_dict_to_geojson(
                data,
                crs_from=crs_for_transform,
                out_crs="EPSG:4326",
                include_label_points=False,
            )
            geojson_bytes = json.dumps(geojson_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

        missing_geom = [
            p.get("nr_cadastral")
            for p in parcels
            if not (p.get("points_xy") and len(p["points_xy"]) >= 3)
        ]
        if missing_geom:
            st.warning(
                "Warning: some parcels have fewer than 3 coordinate points and were excluded from KML/GeoJSON: "
                + ", ".join(str(x) for x in missing_geom)
            )

    except Exception as e:
        st.error(f"Error generating KML/GeoJSON: {e}")
        kml_bytes = b""
        geojson_bytes = b""

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("parcels.json", parcels_json_bytes)
        z.writestr("parcels.geojson", geojson_bytes)
        z.writestr("parcels_all.kml", kml_bytes)

    zip_buffer.seek(0)

    st.download_button(
        "Download export (ZIP)",
        data=zip_buffer,
        file_name="parcels_export.zip",
        mime="application/zip",
    )
