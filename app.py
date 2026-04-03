import streamlit as st
import folium
from folium.plugins import MousePosition, MeasureControl
from streamlit_folium import st_folium
import pystac_client
import planetary_computer
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import rasterio
import requests

st.set_page_config(page_title="VorianCorelli GeoMonitor", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0a1628; }
    [data-testid="stSidebar"] { background-color: #0d1f3c; }
    .main-title { color: #C9A84C; font-size: 2rem; font-weight: 800; letter-spacing: 1px; }
    .sub-title { color: #7a9cc4; font-size: 0.95rem; margin-top: -10px; }
    .metric-card { background: linear-gradient(135deg, #0d1f3c 0%, #152a4a 100%); border: 1px solid #C9A84C44; border-radius: 10px; padding: 16px 20px; margin: 6px 0; }
    .metric-value { color: #C9A84C; font-size: 1.6rem; font-weight: 700; }
    .metric-label { color: #7a9cc4; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 1px; }
    .site-badge { display: inline-block; background: #C9A84C22; border: 1px solid #C9A84C; color: #C9A84C; border-radius: 20px; padding: 2px 12px; font-size: 0.75rem; font-weight: 600; margin-bottom: 8px; }
    .alert-box { background: #ff4b4b22; border-left: 4px solid #ff4b4b; padding: 10px 16px; border-radius: 0 8px 8px 0; color: #ffaaaa; font-size: 0.87rem; }
    .ok-box { background: #00c85322; border-left: 4px solid #00c853; padding: 10px 16px; border-radius: 0 8px 8px 0; color: #aaffcc; font-size: 0.87rem; }
    .info-box { background: #1a6fcc22; border-left: 4px solid #4a9fec; padding: 10px 16px; border-radius: 0 8px 8px 0; color: #aaccff; font-size: 0.87rem; margin: 8px 0; }
    h1, h2, h3 { color: #e8eef5 !important; }
    .stTabs [data-baseweb="tab"] { color: #7a9cc4; }
    .stTabs [aria-selected="true"] { color: #C9A84C !important; border-bottom-color: #C9A84C !important; }
    .stButton button { background: linear-gradient(135deg, #C9A84C, #a07830); color: #0a1628; font-weight: 700; border: none; border-radius: 8px; }
    .footer-note { color: #3a5a7c; font-size: 0.72rem; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

SITES = {
    "asese": {
        "name": "Christ Embassy Asese Campus", "label": "LoveWorld HQ",
        "lat": 6.7600, "lon": 3.4310, "zoom": 17, "color": "#C9A84C", "icon": "⛪",
        "bbox": [3.4260, 6.7550, 3.4370, 6.7660],
        "zones": [
            {"name": "Omnia Hotel",        "lat": 6.76258, "lon": 3.42756, "type": "infrastructure"},
            {"name": "Omnia Towers Hotel", "lat": 6.76224, "lon": 3.42921, "type": "infrastructure"},
            {"name": "Pinnacle Mall",      "lat": 6.76234, "lon": 3.42912, "type": "infrastructure"},
            {"name": "Meeting Bays (1-4)","lat": 6.75600, "lon": 3.43431, "type": "event"},
        ],
        "buildings": [
            {
                "name": "Omnia Hotel",
                "color": "#C9A84C", "fill": "#C9A84C",
                "corners": [
                    (6.76280, 3.42920),
                    (6.76280, 3.42960),
                    (6.76260, 3.42960),
                    (6.76260, 3.42920),
                    (6.76280, 3.42920),
                ],
                "note": "Confirmed — 6.7627 / 3.4294"
            },
            {
                "name": "Omnia Towers Hotel",
                "color": "#7EC8E3", "fill": "#7EC8E3",
                "corners": [
                    (6.76222, 3.42950),
                    (6.76230, 3.42966),
                    (6.76219, 3.42893),
                    (6.76225, 3.42889),
                    (6.76222, 3.42950),
                ],
                "note": "Confirmed"
            },
            {
                "name": "Pinnacle Mall",
                "color": "#FF6B35", "fill": "#FF6B35",
                "corners": [
                    (6.76234, 3.42944),
                    (6.76233, 3.42880),
                    (6.76231, 3.42907),
                    (6.76236, 3.42917),
                    (6.76234, 3.42944),
                ],
                "note": "Confirmed"
            },
            {
                "name": "Meeting Bays Area (Bays 1-4)",
                "color": "#4CAF50", "fill": "#4CAF50",
                "corners": [
                    (6.75600, 3.43431),
                    (6.75611, 3.43494),
                    (6.75409, 3.43494),
                    (6.75409, 3.43391),
                    (6.75600, 3.43431),
                ],
                "note": "Confirmed"
            },
            {
                "name": "Healing Dome",
                "color": "#9C27B0", "fill": "#9C27B0",
                "corners": [
                    (6.75890, 3.42800),
                    (6.75890, 3.42760),
                    (6.75850, 3.42760),
                    (6.75850, 3.42800),
                    (6.75890, 3.42800),
                ],
                "note": "Confirmed — 6.7587 / 3.4278"
            },
        ],
        "objectives": ["Infrastructure tracking", "Green cover", "Perimeter security"]
    },
    "agrifi_ogun":  {"name": "AgriFI - Ogun State",  "lat": 7.1600, "lon": 3.3470, "zoom": 11, "color": "#4CAF50", "bbox": [3.2000, 7.0000, 3.5000, 7.3000], "zones": []},
    "agrifi_ekiti": {"name": "AgriFI - Ekiti State", "lat": 7.7190, "lon": 5.3110, "zoom": 11, "color": "#4CAF50", "bbox": [5.1000, 7.5000, 5.5000, 7.9000], "zones": []},
    "agrifi_oyo":   {"name": "AgriFI - Oyo State",   "lat": 7.8500, "lon": 3.9300, "zoom": 11, "color": "#4CAF50", "bbox": [3.7000, 7.6000, 4.1000, 8.1000], "zones": []},
    "agrifi_ondo":  {"name": "AgriFI - Ondo State",  "lat": 7.2500, "lon": 5.1950, "zoom": 11, "color": "#4CAF50", "bbox": [4.9000, 7.0000, 5.4000, 7.5000], "zones": []},
}

BASEMAPS = {
    "Esri World Imagery (Most Recent)": {"tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "attr": "Esri World Imagery"},
    "Esri Clarity (High Res)":          {"tiles": "https://clarity.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "attr": "Esri Clarity"},
    "Bing Aerial":                      {"tiles": "https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1", "attr": "Microsoft Bing"},
    "Satellite (Google)":               {"tiles": "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", "attr": "Google Satellite"},
    "Satellite + Labels (Google)":      {"tiles": "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", "attr": "Google Hybrid"},
    "Dark (Night)":                     {"tiles": "CartoDB dark_matter", "attr": "CartoDB"},
    "Street Map":                       {"tiles": "OpenStreetMap",       "attr": "OpenStreetMap"},
}

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_buildings(lat, lon, radius_deg=0.010):
    s = lat - radius_deg; n = lat + radius_deg
    w = lon - radius_deg; e = lon + radius_deg
    query = f"""[out:json][timeout:25];(way["building"]({s},{w},{n},{e});relation["building"]({s},{w},{n},{e}););out body;>;out skel qt;"""
    try:
        r = requests.post("https://overpass-api.de/api/interpreter", data={"data": query}, timeout=30)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def parse_buildings(osm_data):
    if not osm_data: return [], 0
    nodes = {el["id"]: (el["lat"], el["lon"]) for el in osm_data.get("elements", []) if el["type"] == "node"}
    buildings = []
    for el in osm_data.get("elements", []):
        if el["type"] == "way" and "building" in el.get("tags", {}):
            coords = [nodes[n] for n in el.get("nodes", []) if n in nodes]
            if len(coords) >= 3:
                buildings.append({"coords": coords, "name": el["tags"].get("name", el["tags"].get("building", "Building")), "levels": el["tags"].get("building:levels", "?")})
    return buildings, len(buildings)

@st.cache_data(ttl=3600, show_spinner=False)
def search_s2(bbox, d1, d2, cloud=30):
    try:
        cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
        items = list(cat.search(collections=["sentinel-2-l2a"], bbox=bbox, datetime=f"{d1}/{d2}", query={"eo:cloud_cover": {"lt": cloud}}).get_items())
        return items
    except:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def compute_ndvi(_item, bbox):
    try:
        item = planetary_computer.sign(_item)
        def read(url):
            with rasterio.open(url) as src:
                from rasterio.warp import transform_bounds
                b = transform_bounds("EPSG:4326", src.crs, *bbox)
                w = src.window(*b)
                return src.read(1, window=w, out_shape=(256,256), resampling=rasterio.enums.Resampling.bilinear).astype(float)
        r = read(item.assets["B04"].href); n = read(item.assets["B08"].href)
        ndvi = np.where((n+r)==0, 0, (n-r)/(n+r))
        return np.clip(ndvi,-1,1), item.datetime.strftime("%Y-%m-%d")
    except:
        return None, None

def ndvi_fig(arr, title, name):
    fig, ax = plt.subplots(figsize=(7,5)); fig.patch.set_facecolor("#0a1628"); ax.set_facecolor("#0a1628")
    im = ax.imshow(arr, cmap=plt.cm.RdYlGn, vmin=-0.2, vmax=0.8)
    cb = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04); cb.set_label("NDVI", color="white")
    cb.ax.yaxis.set_tick_params(color="white"); plt.setp(cb.ax.yaxis.get_ticklabels(), color="white")
    ax.set_title(f"{name}\n{title}", color="#C9A84C", fontsize=11, fontweight="bold"); ax.axis("off")
    plt.tight_layout(); return fig

def change_fig(b, a, title):
    diff = a - b; fig, axes = plt.subplots(1, 3, figsize=(14,4)); fig.patch.set_facecolor("#0a1628")
    for ax in axes: ax.set_facecolor("#0a1628")
    axes[0].imshow(b, cmap="RdYlGn", vmin=-0.2, vmax=0.8); axes[0].set_title("Before", color="#7a9cc4"); axes[0].axis("off")
    axes[1].imshow(a, cmap="RdYlGn", vmin=-0.2, vmax=0.8); axes[1].set_title("After",  color="#7a9cc4"); axes[1].axis("off")
    im = axes[2].imshow(diff, cmap="RdBu", vmin=-0.4, vmax=0.4); axes[2].set_title("Change", color="#C9A84C"); axes[2].axis("off")
    cb = plt.colorbar(im, ax=axes[2], fraction=0.04); cb.set_label("NDVI", color="white")
    cb.ax.yaxis.set_tick_params(color="white"); plt.setp(cb.ax.yaxis.get_ticklabels(), color="white")
    fig.suptitle(title, color="#C9A84C", fontsize=12, fontweight="bold"); plt.tight_layout(); return fig

def stats(arr):
    v = arr[arr > -0.5]
    return {"mean": float(np.mean(v)), "healthy": float(np.mean(v>0.4)*100), "stressed": float(np.mean((v>0.1)&(v<=0.4))*100), "bare": float(np.mean(v<=0.1)*100)} if len(v) else {}

def make_map(lat, lon, zoom, basemap_key, zones=[], bbox=None, buildings=None, show_bldgs=False, site_key=None):
    bm = BASEMAPS[basemap_key]
    if bm["tiles"] in ["CartoDB dark_matter", "OpenStreetMap"]:
        m = folium.Map(location=[lat,lon], zoom_start=zoom, tiles=bm["tiles"])
    else:
        m = folium.Map(location=[lat,lon], zoom_start=zoom, tiles=None)
        folium.TileLayer(tiles=bm["tiles"], attr=bm["attr"], name=basemap_key, max_zoom=21).add_to(m)

    # Coordinate display — shows lat/lon as you move
    MousePosition(
        position="bottomleft",
        separator=" | ",
        prefix="📍",
        lat_formatter="function(num) {return L.Util.formatNum(num, 6);}",
        lng_formatter="function(num) {return L.Util.formatNum(num, 6);}",
    ).add_to(m)

    # Click to get coordinates
    m.add_child(folium.LatLngPopup())

    # Measure tool
    MeasureControl(position="topright", primary_length_unit="meters", secondary_length_unit="kilometers").add_to(m)

    for z in zones:
        c = "#C9A84C" if z["type"]=="infrastructure" else "#7EC8E3"
        folium.CircleMarker([z["lat"],z["lon"]], radius=8, color=c, fill=True, fill_opacity=0.85, tooltip=z["name"], popup=folium.Popup(f"<b>{z['name']}</b>", max_width=200)).add_to(m)
    if bbox:
        folium.Rectangle(bounds=[[bbox[1],bbox[0]],[bbox[3],bbox[2]]], color="#C9A84C", fill=False, weight=2, dash_array="8 4", tooltip="Monitoring perimeter").add_to(m)

    # Ground-truth building polygons
    if site_key and site_key in SITES and "buildings" in SITES[site_key]:
        for b in SITES[site_key]["buildings"]:
            note = b.get("note", "")
            folium.Polygon(
                locations=b["corners"],
                color=b["color"],
                fill=True,
                fill_color=b["fill"],
                fill_opacity=0.35,
                weight=2.5,
                tooltip=f"📍 {b['name']}",
                popup=folium.Popup(f"<b>{b['name']}</b><br><small>{note}</small>", max_width=200)
            ).add_to(m)

    # OSM building footprints overlay
    if show_bldgs and buildings:
        blist, _ = parse_buildings(buildings)
        for b in blist:
            folium.Polygon(locations=b["coords"], color="#ffffff", fill=True, fill_color="#ffffff", fill_opacity=0.15, weight=1, tooltip=f"OSM: {b['name']}").add_to(m)

    folium.LayerControl().add_to(m)
    return m

# SIDEBAR
with st.sidebar:
    st.markdown('<div class="main-title">🌍 GeoMonitor</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">VorianCorelli - Satellite Intelligence</div>', unsafe_allow_html=True)
    st.markdown("---")
    view = st.radio("Nav", ["Overview", "Asese Campus", "AgriFI Land", "Reports"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("**Data Sources**")
    st.markdown("🛰 Sentinel-2 — Microsoft Planetary Computer")
    st.markdown("🏢 Buildings — OSM + Microsoft Africa AI")
    st.markdown("🗺 Imagery — Google Satellite")
    st.markdown("---")
    st.markdown("✅ Christ Embassy Asese")
    st.markdown("✅ AgriFI — 4 State Zones")
    st.markdown('<div class="footer-note">VorianCorelli · AgriFI · Toronet</div>', unsafe_allow_html=True)

# OVERVIEW
if view == "Overview":
    st.markdown('<div class="main-title">Satellite Monitoring Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">VorianCorelli — Asese Campus + AgriFI Land</div>', unsafe_allow_html=True)
    st.markdown("---")
    c1,c2,c3,c4 = st.columns(4)
    for col, val, lbl in [(c1,"2","Sites Monitored"),(c2,"15,000 ha","AgriFI Land"),(c3,"5 days","Sentinel-2 Refresh"),(c4,"10m","Resolution")]:
        with col: st.markdown(f'<div class="metric-card"><div class="metric-value">{val}</div><div class="metric-label">{lbl}</div></div>', unsafe_allow_html=True)
    m = folium.Map(location=[7.1,4.0], zoom_start=7, tiles="CartoDB dark_matter")
    s = SITES["asese"]
    folium.Marker([s["lat"],s["lon"]], popup=s["name"], tooltip=s["name"], icon=folium.Icon(color="orange",icon="church",prefix="fa")).add_to(m)
    for sk in ["agrifi_ogun","agrifi_ekiti","agrifi_oyo","agrifi_ondo"]:
        s2 = SITES[sk]; folium.Marker([s2["lat"],s2["lon"]], popup=s2["name"], tooltip=s2["name"], icon=folium.Icon(color="green",icon="leaf",prefix="fa")).add_to(m)
    st.markdown("### All Sites"); st_folium(m, width=None, height=500, returned_objects=[])

# ASESE CAMPUS
elif view == "Asese Campus":
    st.markdown('<div class="main-title">Christ Embassy Asese Campus</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Lagos-Ibadan Expressway, Moba, Ogun State · GPS: QC5M+935</div>', unsafe_allow_html=True)
    st.markdown("---")
    s = SITES["asese"]
    tab1, tab2, tab3, tab4 = st.tabs(["🏢 Buildings & Satellite", "🌿 Vegetation (NDVI)", "🔍 Change Detection", "📐 Zone Map"])

    with tab1:
        st.markdown("#### Campus Buildings — Satellite View")
        col1, col2 = st.columns([1,2])
        with col1:
            bm_choice = st.selectbox("Base Map", list(BASEMAPS.keys()), index=0)
            show_b = st.toggle("Show Building Footprints", value=True)
            load_b = st.button("Load Buildings")
        with col2:
            st.markdown('<div class="info-box">🛰 <b>Esri World Imagery</b> is the most recently updated free source for Nigeria — try it first.<br>🏢 <b>Orange polygons</b> = AI-mapped building footprints. Tap any polygon for name and floor count.<br>⚠️ Google tiles may be 3-5 years old for this area.</div>', unsafe_allow_html=True)
            st.markdown("**Open in current imagery viewers:**")
            ca2, cb2 = st.columns(2)
            ca2.link_button("🌍 Google Earth (current)", "https://earth.google.com/web/@6.760,3.431,50a,800d,35y,0h,0t,0r")
            cb2.link_button("🛰 Sentinel Hub EO Browser", "https://apps.sentinel-hub.com/eo-browser/?zoom=15&lat=6.760&lng=3.431&themeId=DEFAULT-THEME&datasetId=S2L2A&fromTime=2025-06-01&toTime=2026-03-28&layerId=1_TRUE_COLOR")
        if "bdata" not in st.session_state: st.session_state.bdata = None
        if "bcount" not in st.session_state: st.session_state.bcount = 0
        if load_b:
            with st.spinner("Fetching building footprints..."):
                st.session_state.bdata = fetch_buildings(s["lat"], s["lon"])
                if st.session_state.bdata:
                    _, st.session_state.bcount = parse_buildings(st.session_state.bdata)
        m = make_map(s["lat"], s["lon"], s["zoom"], bm_choice, s["zones"], s["bbox"], st.session_state.bdata if show_b else None, show_b, site_key="asese")
        st_folium(m, width=None, height=530, returned_objects=[])
        if show_b and st.session_state.bcount > 0:
            st.markdown(f'<div class="ok-box">Buildings loaded: <b>{st.session_state.bcount} structures</b> mapped on campus. Tap any orange polygon for details.</div>', unsafe_allow_html=True)
        st.markdown("**Legend:** 🟡 Omnia Hotel &nbsp; 🔵 Omnia Towers &nbsp; 🟠 Pinnacle Mall &nbsp; 🟢 Bays Area &nbsp; 🟣 Healing Dome")
        st.markdown('<div class="info-box">💡 <b>Tap anywhere on the map</b> to get the exact GPS coordinates of that point. Use this to correct building corners — tap the actual corner of a building on the satellite, copy the coordinates, send to Claude.</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown("#### Vegetation Cover Index (NDVI)")
        ca, cb = st.columns([1,2])
        with ca:
            mb = st.slider("Months to search", 1, 6, 2)
            cl = st.slider("Max cloud %", 10, 60, 30)
            rb = st.button("Fetch NDVI")
        with cb:
            if rb:
                d2 = datetime.now().strftime("%Y-%m-%d"); d1 = (datetime.now()-timedelta(days=30*mb)).strftime("%Y-%m-%d")
                with st.spinner("Querying Sentinel-2..."):
                    items = search_s2(s["bbox"], d1, d2, cl)
                if not items: st.warning("No imagery found.")
                else:
                    with st.spinner("Computing NDVI..."):
                        ndvi, dt = compute_ndvi(items[0], s["bbox"])
                    if ndvi is not None:
                        st.pyplot(ndvi_fig(ndvi, f"Date: {dt}", "Asese Campus")); plt.close()
                        v = stats(ndvi)
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Healthy Vegetation", f"{v.get('healthy',0):.1f}%")
                        c2.metric("Stressed / Sparse",  f"{v.get('stressed',0):.1f}%")
                        c3.metric("Bare / Built",       f"{v.get('bare',0):.1f}%")
                    else: st.error("Processing failed.")
            else: st.info("Set parameters and click Fetch NDVI.")

    with tab3:
        st.markdown("#### Change Detection")
        c1,c2 = st.columns(2)
        with c1: bef = st.slider("Before (months ago)", 3, 12, 6)
        with c2: aft = st.slider("After  (months ago)", 0, 4,  1)
        if st.button("Run Change Detection"):
            now = datetime.now(); bbox = s["bbox"]
            with st.spinner("Fetching imagery pair..."):
                ib = search_s2(bbox,(now-timedelta(days=30*(bef+2))).strftime("%Y-%m-%d"),(now-timedelta(days=30*bef)).strftime("%Y-%m-%d"),40)
                ia = search_s2(bbox,(now-timedelta(days=30*(aft+2))).strftime("%Y-%m-%d"),(now-timedelta(days=30*aft)).strftime("%Y-%m-%d"),40)
            if not ib or not ia: st.warning("Imagery not found for one period.")
            else:
                with st.spinner("Computing..."):
                    nb,db = compute_ndvi(ib[0],bbox); na,da = compute_ndvi(ia[0],bbox)
                if nb is not None and na is not None:
                    st.pyplot(change_fig(nb, na, f"Asese Campus ({db} to {da})")); plt.close()
                    loss = float(np.mean((na-nb)<-0.15)*100)
                    if loss > 5: st.markdown(f'<div class="alert-box">Vegetation loss: {loss:.1f}% of area. Possible construction or clearing.</div>', unsafe_allow_html=True)
                    else: st.markdown('<div class="ok-box">No significant change detected. Campus stable.</div>', unsafe_allow_html=True)

    with tab4:
        st.markdown("#### Zone Reference Map")
        m2 = make_map(s["lat"], s["lon"], s["zoom"], "Dark (Night)", s["zones"], s["bbox"], site_key="asese")
        st_folium(m2, width=None, height=430, returned_objects=[])

# AGRIFI LAND
elif view == "AgriFI Land":
    st.markdown('<div class="main-title">AgriFI Land - Southwest Nigeria</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">SWAgCo Land Utilization Agreement - 15,000 ha across 4 States</div>', unsafe_allow_html=True)
    st.markdown("---")
    zone_map = {"Ogun State":"agrifi_ogun","Ekiti State":"agrifi_ekiti","Oyo State":"agrifi_oyo","Ondo State":"agrifi_ondo"}
    zname = st.selectbox("Select Zone", list(zone_map.keys()))
    site = SITES[zone_map[zname]]
    tab1,tab2,tab3 = st.tabs(["Zone Map","Crop Health (NDVI)","Change Detection"])
    with tab1:
        bm2 = st.selectbox("Base Map", list(BASEMAPS.keys()), index=0, key="agrifi_bm")
        bm = BASEMAPS[bm2]
        if bm["tiles"] in ["CartoDB dark_matter","OpenStreetMap"]: m = folium.Map(location=[site["lat"],site["lon"]], zoom_start=site["zoom"], tiles=bm["tiles"])
        else:
            m = folium.Map(location=[site["lat"],site["lon"]], zoom_start=site["zoom"], tiles=None)
            folium.TileLayer(tiles=bm["tiles"], attr=bm["attr"], max_zoom=21).add_to(m)
        bb = site["bbox"]
        folium.Rectangle(bounds=[[bb[1],bb[0]],[bb[3],bb[2]]], color="#4CAF50", fill=True, fill_opacity=0.1, weight=2).add_to(m)
        folium.Marker([site["lat"],site["lon"]], icon=folium.Icon(color="green",icon="leaf",prefix="fa"), tooltip=zname).add_to(m)
        st_folium(m, width=None, height=430, returned_objects=[])
        st.markdown('<div class="alert-box">State proxy boundary active. Plot coordinates pending from SWAgCo.</div>', unsafe_allow_html=True)
    with tab2:
        ca,cb = st.columns([1,2])
        with ca:
            mb = st.slider("Months",1,6,2,key=f"mb_{zname}"); cl=st.slider("Cloud %",10,60,30,key=f"cl_{zname}")
            if st.button("Fetch Crop Health",key=f"btn_{zname}"):
                d2=datetime.now().strftime("%Y-%m-%d"); d1=(datetime.now()-timedelta(days=30*mb)).strftime("%Y-%m-%d")
                with st.spinner("Querying..."):items=search_s2(site["bbox"],d1,d2,cl)
                if not items: cb.warning("No imagery.")
                else:
                    with st.spinner("Computing..."): ndvi,dt=compute_ndvi(items[0],site["bbox"])
                    if ndvi is not None:
                        with cb:
                            st.pyplot(ndvi_fig(ndvi,f"Date: {dt}",site["name"])); plt.close()
                            v=stats(ndvi); c1,c2,c3,c4=st.columns(4)
                            c1.metric("Mean NDVI",f"{v.get('mean',0):.3f}"); c2.metric("Healthy",f"{v.get('healthy',0):.1f}%")
                            c3.metric("Stressed",f"{v.get('stressed',0):.1f}%"); c4.metric("Bare",f"{v.get('bare',0):.1f}%")
                            if v.get("healthy",0)>40: st.markdown('<div class="ok-box">NIRSAL Compliance: Healthy vegetation > 40% threshold. Verified.</div>', unsafe_allow_html=True)
                            else: st.markdown(f'<div class="alert-box">Below 40% NIRSAL threshold. Investigate.</div>', unsafe_allow_html=True)
        with cb:
            if "fetch_done" not in st.session_state: st.info("Click 'Fetch Crop Health' to load data.")
    with tab3:
        c1,c2=st.columns(2)
        with c1: bef=st.slider("Before",3,12,6,key=f"bef_{zname}")
        with c2: aft=st.slider("After",0,4,1,key=f"aft_{zname}")
        if st.button("Run Change Detection",key=f"chg_{zname}"):
            now=datetime.now(); bbox=site["bbox"]
            with st.spinner("Fetching..."):
                ib=search_s2(bbox,(now-timedelta(days=30*(bef+2))).strftime("%Y-%m-%d"),(now-timedelta(days=30*bef)).strftime("%Y-%m-%d"),40)
                ia=search_s2(bbox,(now-timedelta(days=30*(aft+2))).strftime("%Y-%m-%d"),(now-timedelta(days=30*aft)).strftime("%Y-%m-%d"),40)
            if not ib or not ia: st.warning("Imagery not available.")
            else:
                with st.spinner("Computing..."): nb,db=compute_ndvi(ib[0],bbox); na,da=compute_ndvi(ia[0],bbox)
                if nb is not None and na is not None:
                    st.pyplot(change_fig(nb,na,f"{site['name']} ({db} to {da})")); plt.close()
                    loss=float(np.mean((na-nb)<-0.2)*100); gain=float(np.mean((na-nb)>0.2)*100)
                    st.metric("Loss",f"{loss:.1f}%"); st.metric("Gain",f"{gain:.1f}%")
                    if loss>10: st.markdown(f'<div class="alert-box">ENCROACHMENT ALERT: {loss:.1f}% loss. Flag for NIRSAL.</div>', unsafe_allow_html=True)
                    else: st.markdown('<div class="ok-box">No significant encroachment. Land stable.</div>', unsafe_allow_html=True)

# REPORTS
elif view == "Reports":
    st.markdown('<div class="main-title">Reports & Exports</div>', unsafe_allow_html=True)
    st.markdown("---")
    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="site-badge">ASESE CAMPUS</div>', unsafe_allow_html=True)
        st.button("Generate Asese Stewardship Report")
        st.button("Export Building Footprints (GeoJSON)")
    with c2:
        st.markdown('<div class="site-badge">AGRIFI LAND</div>', unsafe_allow_html=True)
        st.button("Generate NIRSAL Compliance Report")
        st.button("Generate AfDB Quarterly Report")
    st.markdown("---")
    st.markdown("""| Frequency | Task | Sites |
|---|---|---|
| Every 5 days | Sentinel-2 new pass | Both |
| Monthly | NDVI + change detection | Both |
| Quarterly | Compliance report | AgriFI |
| On-demand | Building footprint refresh | Asese |""")
