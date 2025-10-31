import os, io, base64, urllib.parse
import requests
import streamlit as st
from PIL import Image

# --- Settings (we read these from Streamlit Secrets if available) ---
API_BASE = st.secrets.get("API_BASE", os.getenv("API_BASE", "").strip())
OCR_SPACE_KEY = st.secrets.get("OCR_SPACE_KEY", os.getenv("OCR_SPACE_KEY", "").strip())

# --- Helpers ---
def ocr_space_image_bytes(image_bytes: bytes, api_key: str) -> str:
    """Call OCR.space free API with image bytes."""
    if not api_key:
        return ""  # run without OCR if no key yet
    url_api = "https://api.ocr.space/parse/image"
    files = {"filename": ("upload.jpg", image_bytes)}
    data = {"apikey": api_key, "language": "eng", "OCREngine": 2, "isTable": False}
    try:
        r = requests.post(url_api, files=files, data=data, timeout=30)
        r.raise_for_status()
        js = r.json()
        if js.get("IsErroredOnProcessing"):
            return ""
        parsed = js.get("ParsedResults", [])
        text = " ".join([p.get("ParsedText", "") for p in parsed])
        return (text or "").strip()
    except Exception:
        return ""

def api_search(query: str):
    if not API_BASE:
        return {"count": 0, "results": []}
    url = f"{API_BASE.rstrip('/')}/search?q={urllib.parse.quote(query)}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def pretty_card(item: dict):
    col1, col2 = st.columns([1,2])
    with col1:
        img_url = item.get("image_url") or ""
        if img_url:
            try:
                st.image(img_url, use_column_width=True)
            except Exception:
                st.write("No image")
        else:
            st.write("No image")
    with col2:
        st.markdown(f"### {item.get('part_name','(unknown)')}")
        st.write(f"**Brand:** {item.get('brand','')}")
        st.write(f"**MPN:** {item.get('mpn','')}")
        alt = item.get("alt_mpn","")
        if str(alt).strip() and str(alt).strip().upper() != "N/A":
            st.write(f"**Alt MPN:** {alt}")
        st.write(f"**Category:** {item.get('category','')}")
        desc = item.get("description","")
        if desc: st.write(desc)
        comp = item.get("compatible_models","")
        if comp: st.caption(f"Compatible: {comp}")
        ds = item.get("datasheet_url","")
        if ds:
            st.link_button("Open datasheet", ds, use_container_width=True)

# --- UI ---
st.set_page_config(page_title="PlumbID – Advanced ID", page_icon="🛠️", layout="centered")
st.title("PlumbID – Parts Identification (Advanced)")
st.write("Type a few words and/or upload a photo. We’ll OCR any labels and combine it with your query.")

with st.form("query_form"):
    q = st.text_input("Describe the part / symptoms / model", placeholder="e.g., Vaillant diverter valve 178978 ecoTEC 835")
    photo = st.file_uploader("Optional photo (jpg/png)", type=["jpg","jpeg","png"])
    submitted = st.form_submit_button("Search")

if submitted:
    ocr_text = ""
    if photo is not None:
        try:
            image_bytes = photo.read()
            # Show preview
            st.image(Image.open(io.BytesIO(image_bytes)), caption="Uploaded", use_column_width=True)
            # OCR
            ocr_text = ocr_space_image_bytes(image_bytes, OCR_SPACE_KEY)
            if ocr_text:
                with st.expander("OCR text found"):
                    st.code(ocr_text)
        except Exception as e:
            st.warning(f"Could not process image: {e}")

    combined_query = " ".join([q or "", ocr_text or ""]).strip()
    if not combined_query:
        st.warning("Please type something or upload a photo.")
    else:
        st.write(f"Searching for: **{combined_query}**")
        try:
            data = api_search(combined_query)
            items = data.get("results") or data.get("items") or []
            count = data.get("count", len(items))
            st.success(f"Found {count} result(s).")
            for item in items:
                pretty_card(item)
                st.divider()
            if count == 0:
                st.info("No matches. Try another angle: brand + model, or clearer photo of the label/part.")
        except Exception as e:
            st.error(f"Search failed: {e}")

with st.sidebar:
    st.header("Settings")
    st.write("These come from Streamlit Secrets.")
    st.write(f"API set: {'✅' if API_BASE else '❌'}")
    st.write(f"OCR key set: {'✅' if OCR_SPACE_KEY else '❌ (optional)'}")
    st.caption("Tip: Even without OCR, text search works. Add an OCR key later for better matches.")
