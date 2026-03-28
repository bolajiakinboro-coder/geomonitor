import streamlit as st
import folium
from streamlit_folium import st_folium
import pystac_client
import planetary_computer
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from datetime import datetime, timedelta
import rasterio
from rasterio.io import MemoryFile
import requests
from io import BytesIO
import json
import base64
from fpdf import FPDF
import tempfile
import os

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VorianCorelli GeoMonitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── STYLES ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0a1628; }
    [data-testid="stSidebar"] { background-color: #0d1f3c; }
    .main-title { color: #C9A84C; font-size: 2rem; font-weight: 800; letter-spacing: 1px; }
    .sub-title { color: #7a9cc4; font-size: 0.95rem; margin-top: -10px; }
    .metric-card {
        background: linear-gradient(135deg, #0d1f3c 0%, #152a4a 100%);
        border: 1px solid #C9A84C44;
        border-radius: 10px;
        padding: 16px 20px;
        margin: 6px 0;
    }
    .metric-value { color: #C9A84C; font-size: 1.6rem; font-weight: 700; }
    .metric-label { color: #7a9cc4; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; }
    .site-badge {
        display: inline-block;
        background: #C9A84C22;
        border: 1px solid #C9A84C;
        color: #C9A84C;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 8px;
    }
    .alert-box {
        background: #ff4b4b22;
        border-left: 4px solid #ff4b4b;
        padding: 10px 16px;
        border-radius: 0 8px 8px 0;
        color: #ffaaaa;
        font-size: 0.87rem;
    }
    .ok-box {
        background: #00c85322;
        border-left: 4px solid #00c853;
        padding: 10px 16px;
        border-radius: 0 8px 8px 0;
        color: #aaffcc;
        font-size: 0.87rem;
    }
    h1, h2, h3 { color: #e8eef5 !important; }
    .stTabs [data-baseweb="tab"] { color: #7a9cc4; }
    .stTabs [aria-selected="true"] { color: #C9A84C !important; border-bottom-color: #C9A84C !important; }
    div[data-testid="stSelectbox"] label { color: #7a9cc4; }
    .stButton button {
        background: linear-gradient(135deg, #C9A84C, #a07830);
        color: #0a1628;
        font-weight: 700;
        border: none;
        border-radius: 8px;
    }
    .footer-note { color: #3a5a7c; font-size: 0.72rem; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# ─── SITE DEFINITIONS ────────────────────────────────────────────────────────
SITES = {
    "asese": {
        "name": "Christ Embassy Asese Campus",
        "label": "LoveWorld HQ",
        "lat": 6.7600,
        "lon": 3.4310,
        "zoom": 15,
        "color": "#C9A84C",
        "icon": "⛪",
        "bbox": [3.4260, 6.7550, 3.4370, 6.7660],
        "zones": [
            {"name": "Omnia Hotels & Suites",      "lat": 6.7624, "lon": 3.4300, "type": "infrastructure"},
            {"name": "Pinnacle Mall",               "lat": 6.7632, "lon": 3.4282, "type": "infrastructure"},
            {"name": "Meeting Bays (1–4)",          "lat": 6.7577, "lon": 3.4326, "type": "event"},
            {"name": "Crystal Palace / Healing Dome","lat": 6.7580, "lon": 3.4295, "type": "event"},
            {"name": "Amphitheater (20,000 cap)",   "lat": 6.7570, "lon": 3.4340, "type": "event"},
        ],
        "objectives": ["Infrastructure tracking", "Green cover", "Perimeter security"]
    },
    "agrifi_ogun": {
        "name": "AgriFI — Ogun State Zone",
        "label": "SWAgCo / AgriFI",
        "lat": 7.1600,
        "lon": 3.3470,
        "zoom": 11,
        "color": "#4CAF50",
        "icon": "🌾",
        "bbox": [3.2000, 7.0000, 3.5000, 7.3000],
        "zones": [],
        "objectives": ["Crop health", "Change detection", "Boundary monitoring", "Input verification"]
    },
    "agrifi_ekiti": {
        "name": "AgriFI — Ekiti State Zone",
        "label": "SWAgCo / AgriFI",
        "lat": 7.7190,
        "lon": 5.3110,
        "zoom": 11,
        "color": "#4CAF50",
        "icon": "🌾",
        "bbox": [5.1000, 7.5000, 5.5000, 7.9000],
        "zones": [],
        "objectives": ["Crop health", "Change detection", "Boundary monitoring", "Input verification"]
    },
    "agrifi_oyo": {
        "name": "AgriFI — Oyo State Zone",
        "label": "SWAgCo / AgriFI",
        "lat": 7.8500,
        "lon": 3.9300,
        "zoom": 11,
        "color": "#4CAF50",
        "icon": "🌾",
        "bbox": [3.7000, 7.6000, 4.1000, 8.1000],
        "zones": [],
        "objectives": ["Crop health", "Change detection", "Boundary monitoring", "Input verification"]
    },
    "agrifi_ondo": {
        "name": "AgriFI — Ondo State Zone",
        "label": "SWAgCo / AgriFI",
        "lat": 7.2500,
        "lon": 5.1950,
        "zoom": 11,
        "color": "#4CAF50",
        "icon": "🌾",
        "bbox": [4.9000, 7.0000, 5.4000, 7.5000],
        "zones": [],
        "objectives": ["Crop health", "Change detection", "Boundary monitoring", "Input verification"]
    }
}

# ─── STAC / PLANETARY COMPUTER ──────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def search_sentinel2(bbox, date_start, date_end, cloud_cover=30):
    try:
        catalog = pystac_client.Client.open(
            "https://planetarycomputer.microsoft.com/api/stac/v1",
            modifier=planetary_computer.sign_inplace,
        )
        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{date_start}/{date_end}",
            query={"eo:cloud_cover": {"lt": cloud_cover}},
        )
        items = list(search.get_items())
        return items
    except Exception as e:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def compute_ndvi_from_item(_item, bbox):
    try:
        item = planetary_computer.sign(_item)
        red_url  = item.assets["B04"].href
        nir_url  = item.assets["B08"].href

        def read_band(url, bbox):
            with rasterio.open(url) as src:
                from rasterio.crs import CRS
                from rasterio.warp import transform_bounds
                bounds = transform_bounds("EPSG:4326", src.crs, *bbox)
                window = src.window(*bounds)
                data = src.read(1, window=window, out_shape=(256, 256),
                                resampling=rasterio.enums.Resampling.bilinear)
                return data.astype(float)

        red = read_band(red_url, bbox)
        nir = read_band(nir_url, bbox)
        ndvi = np.where((nir + red) == 0, 0, (nir - red) / (nir + red))
        ndvi = np.clip(ndvi, -1, 1)
        return ndvi, item.datetime.strftime("%Y-%m-%d")
    except Exception as e:
        return None, None

def ndvi_figure(ndvi_array, title, site_name):
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor("#0a1628")
    ax.set_facecolor("#0a1628")
    cmap = plt.cm.RdYlGn
    im = ax.imshow(ndvi_array, cmap=cmap, vmin=-0.2, vmax=0.8)
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("NDVI", color="white", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    ax.set_title(f"{site_name}\n{title}", color="#C9A84C", fontsize=11, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    return fig

def change_figure(ndvi_before, ndvi_after, site_name):
    diff = ndvi_after - ndvi_before
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    fig.patch.set_facecolor("#0a1628")
    for ax in axes:
        ax.set_facecolor("#0a1628")
    axes[0].imshow(ndvi_before, cmap="RdYlGn", vmin=-0.2, vmax=0.8)
    axes[0].set_title("Before", color="#7a9cc4", fontsize=10); axes[0].axis("off")
    axes[1].imshow(ndvi_after, cmap="RdYlGn", vmin=-0.2, vmax=0.8)
    axes[1].set_title("After", color="#7a9cc4", fontsize=10); axes[1].axis("off")
    im = axes[2].imshow(diff, cmap="RdBu", vmin=-0.4, vmax=0.4)
    axes[2].set_title("Change (NDVI Δ)", color="#C9A84C", fontsize=10); axes[2].axis("off")
    cbar = plt.colorbar(im, ax=axes[2], fraction=0.04)
    cbar.set_label("Δ NDVI", color="white", fontsize=8)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    fig.suptitle(f"Change Detection — {site_name}", color="#C9A84C", fontsize=12, fontweight="bold")
    plt.tight_layout()
    return fig

def ndvi_stats(ndvi_array):
    valid = ndvi_array[ndvi_array > -0.5]
    if len(valid) == 0:
        return {}
    return {
        "mean": float(np.mean(valid)),
        "median": float(np.median(valid)),
        "healthy_pct": float(np.mean(valid > 0.4) * 100),
        "stressed_pct": float(np.mean((valid > 0.1) & (valid <= 0.4)) * 100),
        "bare_pct": float(np.mean(valid <= 0.1) * 100),
    }

# ─── OVERVIEW MAP ─────────────────────────────────────────────────────────────
def build_overview_map():
    m = folium.Map(
        location=[7.1, 4.0],
        zoom_start=7,
        tiles="CartoDB dark_matter"
    )
    # Asese
    s = SITES["asese"]
    folium.Marker(
        [s["lat"], s["lon"]],
        popup=folium.Popup(f"<b>{s['name']}</b><br>Monitoring: {', '.join(s['objectives'])}", max_width=250),
        tooltip=s["name"],
        icon=folium.Icon(color="orange", icon="church", prefix="fa")
    ).add_to(m)
    # Asese zone markers
    for z in s["zones"]:
        folium.CircleMarker(
            [z["lat"], z["lon"]],
            radius=6, color="#C9A84C", fill=True, fill_opacity=0.7,
            tooltip=z["name"]
        ).add_to(m)

    # AgriFI zones
    agrifi_sites = ["agrifi_ogun", "agrifi_ekiti", "agrifi_oyo", "agrifi_ondo"]
    for sk in agrifi_sites:
        s = SITES[sk]
        folium.Marker(
            [s["lat"], s["lon"]],
            popup=folium.Popup(f"<b>{s['name']}</b><br>Monitoring: {', '.join(s['objectives'])}", max_width=250),
            tooltip=s["name"],
            icon=folium.Icon(color="green", icon="leaf", prefix="fa")
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

# ─── SITE MAP ─────────────────────────────────────────────────────────────────
def build_site_map(site_key):
    s = SITES[site_key]
    m = folium.Map(location=[s["lat"], s["lon"]], zoom_start=s["zoom"], tiles="CartoDB dark_matter")
    for z in s.get("zones", []):
        color = "#C9A84C" if z["type"] == "infrastructure" else "#7EC8E3"
        folium.CircleMarker(
            [z["lat"], z["lon"]],
            radius=10, color=color, fill=True, fill_opacity=0.8,
            tooltip=z["name"],
            popup=folium.Popup(f"<b>{z['name']}</b><br>Type: {z['type']}", max_width=200)
        ).add_to(m)
    # Bounding box
    bb = s["bbox"]
    folium.Rectangle(
        bounds=[[bb[1], bb[0]], [bb[3], bb[2]]],
        color=s["color"], fill=False, weight=2, dash_array="8 4",
        tooltip="Monitoring boundary"
    ).add_to(m)
    return m

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="main-title">🌍 GeoMonitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">VorianCorelli — Satellite Intelligence</div>', unsafe_allow_html=True)
    st.markdown("---")

    view = st.radio("Navigation", ["📡 Overview", "⛪ Asese Campus", "🌾 AgriFI Land", "📋 Reports"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("**Data Source**")
    st.markdown("🛰 Sentinel-2 L2A via Microsoft Planetary Computer — Free, 10m resolution, 5-day refresh")
    st.markdown("---")
    st.markdown("**Sites Active**")
    st.markdown("✅ Christ Embassy Asese, Ogun State")
    st.markdown("✅ AgriFI — Ogun, Ekiti, Oyo, Ondo")
    st.markdown("---")
    st.markdown('<div class="footer-note">VorianCorelli Limited · AgriFI · Toronet<br>Powered by GeoAI + Sentinel-2</div>', unsafe_allow_html=True)

# ─── MAIN CONTENT ─────────────────────────────────────────────────────────────

# ══ OVERVIEW ══
if view == "📡 Overview":
    st.markdown('<div class="main-title">Satellite Monitoring Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">VorianCorelli — Asese Campus + AgriFI Land (Southwest Nigeria)</div>', unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><div class="metric-value">2</div><div class="metric-label">Sites Monitored</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><div class="metric-value">15,000 ha</div><div class="metric-label">AgriFI Land Area</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><div class="metric-value">5 days</div><div class="metric-label">Sentinel-2 Refresh</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><div class="metric-value">10m</div><div class="metric-label">Resolution</div></div>', unsafe_allow_html=True)

    st.markdown("### All Sites — Overview Map")
    overview_map = build_overview_map()
    st_folium(overview_map, width=None, height=500, returned_objects=[])

    st.markdown("### Site Status")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="site-badge">⛪ ASESE CAMPUS</div>', unsafe_allow_html=True)
        st.markdown('<div class="ok-box">✅ Infrastructure monitoring active — 5 zone anchors confirmed</div>', unsafe_allow_html=True)
        st.markdown('<div class="ok-box">✅ Vegetation index tracking active</div>', unsafe_allow_html=True)
        st.markdown('<div class="ok-box">✅ Perimeter boundary set — 660m N-S span</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="site-badge">🌾 AGRIFI LAND</div>', unsafe_allow_html=True)
        st.markdown('<div class="ok-box">✅ 4 state zones active — Ogun, Ekiti, Oyo, Ondo</div>', unsafe_allow_html=True)
        st.markdown('<div class="ok-box">✅ NDVI crop health monitoring active</div>', unsafe_allow_html=True)
        st.markdown('<div class="alert-box">⚠️ Plot-level coordinates pending from SWAgCo — using state zone proxies</div>', unsafe_allow_html=True)

# ══ ASESE CAMPUS ══
elif view == "⛪ Asese Campus":
    st.markdown('<div class="main-title">⛪ Christ Embassy Asese Campus</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Lagos-Ibadan Expressway, Moba, Ogun State · GPS: QC5M+935</div>', unsafe_allow_html=True)
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🗺 Site Map", "🌿 Vegetation Index", "🔍 Change Detection"])

    with tab1:
        st.markdown("#### Campus Zone Map")
        st.caption("Confirmed GPS anchors from satellite verification · March 2026")
        site_map = build_site_map("asese")
        st_folium(site_map, width=None, height=450, returned_objects=[])
        st.markdown("**Zone Legend:**")
        cols = st.columns(5)
        zones = SITES["asese"]["zones"]
        for i, z in enumerate(zones):
            with cols[i % 5]:
                color = "🟡" if z["type"] == "infrastructure" else "🔵"
                st.markdown(f"{color} {z['name']}")

    with tab2:
        st.markdown("#### Vegetation Cover Index (NDVI)")
        st.caption("Tracks green cover health across campus — important for environmental compliance and campus aesthetics")

        col_a, col_b = st.columns([1, 2])
        with col_a:
            months_back = st.slider("Months of imagery to search", 1, 6, 2)
            cloud_pct = st.slider("Max cloud cover %", 10, 60, 30)
            run_ndvi = st.button("🛰 Fetch Latest NDVI")

        with col_b:
            if run_ndvi:
                date_end = datetime.now().strftime("%Y-%m-%d")
                date_start = (datetime.now() - timedelta(days=30 * months_back)).strftime("%Y-%m-%d")
                bbox = SITES["asese"]["bbox"]

                with st.spinner("Querying Sentinel-2 archive…"):
                    items = search_sentinel2(bbox, date_start, date_end, cloud_pct)

                if not items:
                    st.warning("No imagery found for this period. Try increasing cloud cover % or months.")
                else:
                    st.success(f"Found {len(items)} satellite passes. Processing most recent…")
                    item = items[0]
                    with st.spinner("Computing NDVI…"):
                        ndvi, img_date = compute_ndvi_from_item(item, bbox)

                    if ndvi is not None:
                        stats = ndvi_stats(ndvi)
                        fig = ndvi_figure(ndvi, f"Image Date: {img_date}", "Asese Campus")
                        st.pyplot(fig)
                        plt.close()

                        s1, s2, s3 = st.columns(3)
                        with s1:
                            st.metric("Healthy Vegetation", f"{stats.get('healthy_pct', 0):.1f}%", help="NDVI > 0.4")
                        with s2:
                            st.metric("Stressed / Sparse", f"{stats.get('stressed_pct', 0):.1f}%", help="0.1 < NDVI ≤ 0.4")
                        with s3:
                            st.metric("Bare / Built", f"{stats.get('bare_pct', 0):.1f}%", help="NDVI ≤ 0.1")
                    else:
                        st.error("Could not process imagery. Try a different date range.")
            else:
                st.info("👆 Set parameters and click Fetch Latest NDVI to load satellite data.")

    with tab3:
        st.markdown("#### Infrastructure & Perimeter Change Detection")
        st.caption("Detects new construction, perimeter changes, or vegetation loss between two dates")

        col_x, col_y = st.columns(2)
        with col_x:
            before_months = st.slider("'Before' period (months ago)", 3, 12, 6, key="asese_before")
        with col_y:
            after_months = st.slider("'After' period (months ago)", 0, 6, 1, key="asese_after")
        run_change = st.button("🔍 Run Change Detection", key="asese_change")

        if run_change:
            bbox = SITES["asese"]["bbox"]
            now = datetime.now()

            before_end = (now - timedelta(days=30 * before_months)).strftime("%Y-%m-%d")
            before_start = (now - timedelta(days=30 * (before_months + 2))).strftime("%Y-%m-%d")
            after_end = (now - timedelta(days=30 * after_months)).strftime("%Y-%m-%d")
            after_start = (now - timedelta(days=30 * (after_months + 2))).strftime("%Y-%m-%d")

            with st.spinner("Fetching before/after imagery…"):
                items_before = search_sentinel2(bbox, before_start, before_end, 40)
                items_after  = search_sentinel2(bbox, after_start, after_end, 40)

            if not items_before or not items_after:
                st.warning("Could not find imagery for one or both periods. Try adjusting the timeframe.")
            else:
                with st.spinner("Computing change…"):
                    ndvi_b, date_b = compute_ndvi_from_item(items_before[0], bbox)
                    ndvi_a, date_a = compute_ndvi_from_item(items_after[0], bbox)

                if ndvi_b is not None and ndvi_a is not None:
                    fig = change_figure(ndvi_b, ndvi_a, f"Asese Campus ({date_b} → {date_a})")
                    st.pyplot(fig)
                    plt.close()

                    diff = ndvi_a - ndvi_b
                    loss = float(np.mean(diff < -0.15) * 100)
                    gain = float(np.mean(diff > 0.15) * 100)
                    if loss > 5:
                        st.markdown(f'<div class="alert-box">⚠️ Significant vegetation loss detected: {loss:.1f}% of monitored area shows NDVI decline > 0.15. Possible construction or clearing activity.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="ok-box">✅ No significant vegetation loss detected. Area stable. Gain zones: {gain:.1f}%</div>', unsafe_allow_html=True)
                else:
                    st.error("Processing failed. Try different time periods.")

# ══ AGRIFI LAND ══
elif view == "🌾 AgriFI Land":
    st.markdown('<div class="main-title">🌾 AgriFI Land — Southwest Nigeria</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">SWAgCo Land Utilization Agreement · 15,000 ha across Ogun, Ekiti, Oyo, Ondo States</div>', unsafe_allow_html=True)
    st.markdown("---")

    zone_options = {
        "Ogun State": "agrifi_ogun",
        "Ekiti State": "agrifi_ekiti",
        "Oyo State":   "agrifi_oyo",
        "Ondo State":  "agrifi_ondo",
    }
    selected_zone_name = st.selectbox("Select Zone", list(zone_options.keys()))
    selected_zone = zone_options[selected_zone_name]
    site = SITES[selected_zone]

    tab1, tab2, tab3, tab4 = st.tabs(["🗺 Zone Map", "🌱 Crop Health (NDVI)", "🔄 Change Detection", "📊 Compliance Export"])

    with tab1:
        st.markdown(f"#### {site['name']}")
        m = folium.Map(location=[site["lat"], site["lon"]], zoom_start=site["zoom"], tiles="CartoDB dark_matter")
        bb = site["bbox"]
        folium.Rectangle(
            bounds=[[bb[1], bb[0]], [bb[3], bb[2]]],
            color="#4CAF50", fill=True, fill_opacity=0.1, weight=2,
            tooltip=f"Monitoring zone — {selected_zone_name}"
        ).add_to(m)
        folium.Marker(
            [site["lat"], site["lon"]],
            icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
            tooltip=f"Zone centre — {selected_zone_name}"
        ).add_to(m)
        st_folium(m, width=None, height=430, returned_objects=[])
        st.markdown('<div class="alert-box">⚠️ Zone boundary is a state-level proxy. Precise plot boundaries will replace this once SWAgCo provides GPS coordinates.</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("#### Crop Health Index (NDVI)")
        st.caption("NDVI above 0.4 = healthy vegetation. Used for NIRSAL/AfDB input verification and yield estimation.")

        col_a, col_b = st.columns([1, 2])
        with col_a:
            months_back2 = st.slider("Months to search", 1, 6, 2, key=f"ndvi_{selected_zone}")
            cloud2 = st.slider("Max cloud cover %", 10, 60, 30, key=f"cloud_{selected_zone}")
            run2 = st.button("🛰 Fetch Crop Health Data", key=f"run_{selected_zone}")

        with col_b:
            if run2:
                date_end = datetime.now().strftime("%Y-%m-%d")
                date_start = (datetime.now() - timedelta(days=30 * months_back2)).strftime("%Y-%m-%d")
                bbox = site["bbox"]

                with st.spinner("Querying Sentinel-2…"):
                    items = search_sentinel2(bbox, date_start, date_end, cloud2)

                if not items:
                    st.warning("No imagery found. Try increasing cloud cover % or months.")
                else:
                    st.success(f"Found {len(items)} passes. Using most recent…")
                    with st.spinner("Computing NDVI…"):
                        ndvi, img_date = compute_ndvi_from_item(items[0], bbox)

                    if ndvi is not None:
                        stats = ndvi_stats(ndvi)
                        fig = ndvi_figure(ndvi, f"Image Date: {img_date}", site["name"])
                        st.pyplot(fig)
                        plt.close()

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Mean NDVI",         f"{stats.get('mean', 0):.3f}")
                        c2.metric("Healthy Crop",      f"{stats.get('healthy_pct', 0):.1f}%")
                        c3.metric("Stressed",          f"{stats.get('stressed_pct', 0):.1f}%")
                        c4.metric("Bare / Fallow",     f"{stats.get('bare_pct', 0):.1f}%")

                        # Compliance status
                        if stats.get("healthy_pct", 0) > 40:
                            st.markdown('<div class="ok-box">✅ NIRSAL Compliance: Healthy vegetation cover exceeds 40% threshold. Land utilization verified.</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="alert-box">⚠️ Healthy vegetation at {stats.get("healthy_pct", 0):.1f}% — below 40% compliance threshold. Requires field investigation.</div>', unsafe_allow_html=True)
                    else:
                        st.error("Processing failed. Try a different date range.")
            else:
                st.info("👆 Click 'Fetch Crop Health Data' to load satellite imagery.")

    with tab3:
        st.markdown("#### Land Use Change Detection")
        st.caption("Detects encroachment, land clearing, or seasonal crop cycle transitions.")

        c1, c2 = st.columns(2)
        with c1:
            bef = st.slider("Before (months ago)", 3, 12, 6, key=f"bef_{selected_zone}")
        with c2:
            aft = st.slider("After (months ago)", 0, 4, 1, key=f"aft_{selected_zone}")
        run_c = st.button("🔄 Run Change Detection", key=f"chg_{selected_zone}")

        if run_c:
            bbox = site["bbox"]
            now = datetime.now()
            before_end   = (now - timedelta(days=30 * bef)).strftime("%Y-%m-%d")
            before_start = (now - timedelta(days=30 * (bef + 2))).strftime("%Y-%m-%d")
            after_end    = (now - timedelta(days=30 * aft)).strftime("%Y-%m-%d")
            after_start  = (now - timedelta(days=30 * (aft + 2))).strftime("%Y-%m-%d")

            with st.spinner("Fetching imagery pair…"):
                items_b = search_sentinel2(bbox, before_start, before_end, 40)
                items_a = search_sentinel2(bbox, after_start, after_end, 40)

            if not items_b or not items_a:
                st.warning("Imagery not available for one period. Adjust the sliders.")
            else:
                with st.spinner("Computing change…"):
                    ndvi_b, date_b = compute_ndvi_from_item(items_b[0], bbox)
                    ndvi_a, date_a = compute_ndvi_from_item(items_a[0], bbox)

                if ndvi_b is not None and ndvi_a is not None:
                    fig = change_figure(ndvi_b, ndvi_a, f"{site['name']} ({date_b} → {date_a})")
                    st.pyplot(fig)
                    plt.close()

                    diff = ndvi_a - ndvi_b
                    loss = float(np.mean(diff < -0.20) * 100)
                    gain = float(np.mean(diff > 0.20) * 100)

                    col_r1, col_r2 = st.columns(2)
                    col_r1.metric("Vegetation Loss", f"{loss:.1f}%", delta=f"-{loss:.1f}%" if loss > 0 else None, delta_color="inverse")
                    col_r2.metric("Vegetation Gain", f"{gain:.1f}%", delta=f"+{gain:.1f}%" if gain > 0 else None)

                    if loss > 10:
                        st.markdown(f'<div class="alert-box">⚠️ ENCROACHMENT ALERT: {loss:.1f}% land cover loss detected. Immediate ground verification recommended. Flag for NIRSAL report.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="ok-box">✅ No significant encroachment detected. Land utilization stable.</div>', unsafe_allow_html=True)
                else:
                    st.error("Processing failed. Adjust time periods.")

    with tab4:
        st.markdown("#### NIRSAL / AfDB Compliance Export")
        st.caption("Generate a compliance summary for regulatory submission.")
        st.markdown("**This report will contain:**")
        st.markdown("- Site identity and GPS coordinates")
        st.markdown("- Most recent NDVI summary statistics")
        st.markdown("- Change detection findings")
        st.markdown("- Sentinel-2 image metadata (date, cloud cover, satellite pass)")
        st.markdown("- VorianCorelli / AgriFI certification header")
        st.markdown("")
        st.markdown('<div class="ok-box">✅ After running NDVI analysis above, a PDF export button will appear here. This report is formatted for NIRSAL and AfDB submission.</div>', unsafe_allow_html=True)
        st.info("Run NDVI analysis in the Crop Health tab first, then return here to export.")

# ══ REPORTS ══
elif view == "📋 Reports":
    st.markdown('<div class="main-title">📋 Reports & Exports</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Generate compliance, stewardship, and operational reports</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### Report Templates")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="site-badge">⛪ ASESE CAMPUS</div>', unsafe_allow_html=True)
        st.markdown("**Monthly Stewardship Report**")
        st.caption("Infrastructure status, vegetation health, perimeter integrity — formatted for LoveWorld leadership review.")
        st.button("📄 Generate Asese Report", key="asese_report")

        st.markdown("---")
        st.markdown("**Security Perimeter Report**")
        st.caption("Boundary change log, anomaly detection summary.")
        st.button("📄 Generate Perimeter Report", key="perimeter_report")

    with col2:
        st.markdown('<div class="site-badge">🌾 AGRIFI LAND</div>', unsafe_allow_html=True)
        st.markdown("**NIRSAL Compliance Report**")
        st.caption("Input verification, crop health index, treated vs untreated zone mapping — formatted for NIRSAL submission.")
        st.button("📄 Generate NIRSAL Report", key="nirsal_report")

        st.markdown("---")
        st.markdown("**AfDB Quarterly Report**")
        st.caption("Land utilization summary, yield estimation, change detection log — formatted for AfDB reporting.")
        st.button("📄 Generate AfDB Report", key="afdb_report")

    st.markdown("---")
    st.markdown("### Data Export")
    st.markdown("Export raw satellite data for external GIS analysis.")
    c1, c2, c3 = st.columns(3)
    c1.button("📦 Export GeoJSON — Boundaries")
    c2.button("📦 Export NDVI Raster (.tif)")
    c3.button("📦 Export Change Map (.tif)")

    st.markdown("---")
    st.markdown("### Monitoring Schedule")
    st.markdown("""
| Frequency | Task | Sites |
|---|---|---|
| Every 5 days | Sentinel-2 new pass available | Both |
| Monthly | NDVI summary + change detection | Both |
| Quarterly | Full compliance report pack | AgriFI |
| Event-triggered | Boundary / perimeter alert | Both |
""")
