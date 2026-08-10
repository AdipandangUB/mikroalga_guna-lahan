# -*- coding: utf-8 -*-
"""
Aplikasi Streamlit: Analisis Tata Guna Lahan, Faktor Meteorologis, dan
Keterkaitannya dengan Komunitas Mikroalga
Studi Kasus: Embung Wisdom Park (UGM) & Embung Langensari, Yogyakarta

Sumber data dasar (parameter fisika-kimia air & hasil identifikasi mikroalga):
Laporan "Identifikasi Komunitas Mikroalga pada Ekosistem Perairan Lentik"
(sampling 16 Januari 2026).

CATATAN PENTING:
Laporan sumber HANYA memuat data suhu air, pH, DO, dan TDS -- TIDAK memuat
data tata guna lahan (land use) maupun data meteorologis udara (suhu udara,
kelembaban, curah hujan). Oleh karena itu, modul Tata Guna Lahan dan Faktor
Meteorologis pada aplikasi ini disediakan sebagai KERANGKA KERJA INTERAKTIF:
nilai default yang tampil adalah ESTIMASI AWAL (indikatif, dari interpretasi
visual foto lokasi pada laporan) yang WAJIB divalidasi/diganti pengguna
dengan data primer (klasifikasi citra Sentinel-2/GEE, data BMKG, atau hasil
survei lapangan) sebelum digunakan sebagai dasar kesimpulan ilmiah.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import io
import base64
from pathlib import Path

# ----------------------------------------------------------------------------
# KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Analisis Tata Guna Lahan, Meteorologi & Mikroalga - Embung UGM/Langensari",
    page_icon="🌱",
    layout="wide",
)

# ----------------------------------------------------------------------------
# HEADER BACKGROUND IMAGE (embung-nglanggeran.jpg)
# ----------------------------------------------------------------------------
# Simpan file gambar di folder "assets/" pada root repo GitHub Anda
# (satu level dengan app.py), lalu deploy ulang ke Streamlit Cloud.
HEADER_IMG_PATH = Path(__file__).parent / "assets" / "embung-nglanggeran.jpg"


@st.cache_data
def get_base64_of_file(path: Path):
    """Encode file gambar lokal menjadi base64 agar bisa dipakai sebagai
    background-image di CSS tanpa perlu hosting eksternal (aman untuk
    Streamlit Community Cloud)."""
    if not path.exists():
        return None
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


def render_header_banner(title: str, subtitle: str, img_path: Path):
    """Render judul halaman di dalam banner dengan gambar latar."""
    img_b64 = get_base64_of_file(img_path)

    if img_b64:
        bg_layer = (
            f"linear-gradient(rgba(4, 30, 20, 0.55), rgba(4, 30, 20, 0.65)), "
            f"url('data:image/jpeg;base64,{img_b64}')"
        )
    else:
        # Fallback: gradasi hijau polos jika gambar belum tersedia di repo
        bg_layer = "linear-gradient(135deg, #14532d, #166534)"

    st.markdown(
        f"""
        <style>
        .header-banner {{
            background-image: {bg_layer};
            background-size: cover;
            background-position: center 65%;
            background-repeat: no-repeat;
            border-radius: 16px;
            padding: 2.75rem 2.25rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
        }}
        .header-banner h1 {{
            color: #ffffff !important;
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 6px rgba(0, 0, 0, 0.55);
        }}
        .header-banner p {{
            color: #f0fdf4 !important;
            font-size: 1.15rem;
            font-weight: 500;
            margin: 0;
            text-shadow: 0 2px 5px rgba(0, 0, 0, 0.55);
        }}
        </style>
        <div class="header-banner">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not img_b64:
        st.warning(
            f"⚠️ Gambar header tidak ditemukan di `{img_path}`. "
            "Unggah file `embung-nglanggeran.jpg` ke folder `assets/` pada "
            "repo GitHub Anda agar background foto embung tampil."
        )

# ----------------------------------------------------------------------------
# UTILITAS
# ----------------------------------------------------------------------------
def dms_to_dd(deg, minute, sec, hemisphere):
    """Konversi koordinat DMS (derajat-menit-detik) ke desimal derajat."""
    dd = deg + minute / 60 + sec / 3600
    if hemisphere in ("S", "W"):
        dd *= -1
    return dd


@st.cache_data
def load_kualitas_air():
    """Data Tabel 1 pada laporan: parameter fisika-kimia per sampel."""
    data = [
        ["Embung Wisdom Park", "Permukaan", 25.5, 6.96, 7.10, 126.9],
        ["Embung Wisdom Park", "Kedalaman (0.8-1 m)", 25.2, 6.83, 7.10, 143.0],
        ["Embung Langensari", "Permukaan", 25.7, 7.07, 4.11, 145.0],
        ["Embung Langensari", "Kedalaman (0.8-1 m)", 25.5, 7.22, 7.30, 205.0],
        ["Air Tampungan Rumah Tangga", "Permukaan", 26.0, 6.84, 6.80, 191.0],
    ]
    df = pd.DataFrame(
        data, columns=["Lokasi", "Titik", "Suhu_Air_C", "pH", "DO_mgL", "TDS_mgL"]
    )
    return df


@st.cache_data
def load_mikroalga():
    """Data Tabel 2-6 pada laporan: hasil identifikasi mikroalga per lokasi/titik."""
    rows = [
        # Lokasi, Titik, Kelas, Spesies, Dominan
        ("Embung Wisdom Park", "Permukaan", "Chlorophyceae", "Chlorococcum sp.", True),
        ("Embung Wisdom Park", "Permukaan", "Bacillariophyceae", "Aulacoseira sp.", False),
        ("Embung Wisdom Park", "Permukaan", "Bacillariophyceae", "Cyclotella sp.", False),
        ("Embung Wisdom Park", "Permukaan", "Euglenophyceae", "Phacus sp.", False),
        ("Embung Wisdom Park", "Permukaan", "Chlorophyceae", "Scenedesmus sp.", False),
        ("Embung Wisdom Park", "Permukaan", "Chlorophyceae", "Eudorina sp.", False),
        ("Embung Wisdom Park", "Kedalaman (0.8-1 m)", "Chlorophyceae", "Chlorococcum sp.", True),
        ("Embung Wisdom Park", "Kedalaman (0.8-1 m)", "Bacillariophyceae", "Aulacoseira sp.", False),
        ("Embung Wisdom Park", "Kedalaman (0.8-1 m)", "Chlorophyceae", "Golenkimia sp.", False),
        ("Embung Wisdom Park", "Kedalaman (0.8-1 m)", "Bacillariophyceae", "Cyclotella sp.", False),
        ("Embung Wisdom Park", "Kedalaman (0.8-1 m)", "Chlorophyceae", "Scenedesmus sp.", False),
        ("Embung Langensari", "Permukaan", "Bacillariophyceae", "Pinnularia sp.", True),
        ("Embung Langensari", "Permukaan", "Chlorophyceae", "Chlorococcum sp.", False),
        ("Embung Langensari", "Permukaan", "Chlorophyceae", "Scenedesmus sp.", False),
        ("Embung Langensari", "Permukaan", "Euglenophyceae", "Phacus sp.", False),
        ("Embung Langensari", "Kedalaman (0.8-1 m)", "Trebouxiophyceae", "Chlorella sp.", True),
        ("Embung Langensari", "Kedalaman (0.8-1 m)", "Chlorophyceae", "Chlorococcum sp.", True),
        ("Embung Langensari", "Kedalaman (0.8-1 m)", "Bacillariophyceae", "Pinnularia sp.", False),
        ("Embung Langensari", "Kedalaman (0.8-1 m)", "Bacillariophyceae", "Cyclotella sp.", False),
        ("Air Tampungan Rumah Tangga", "Permukaan", "Cyanophyceae", "Nostoc sp.", True),
    ]
    df = pd.DataFrame(rows, columns=["Lokasi", "Titik", "Kelas", "Spesies", "Dominan"])
    return df


@st.cache_data
def load_titik_koordinat():
    """Koordinat titik sampling dari Gambar 3 & 4 pada laporan (dikonversi ke desimal)."""
    raw = [
        # Lokasi, Titik, deg, min, sec (lat S), deg, min, sec (lon E)
        ("Embung Wisdom Park", "Titik 1", 7, 46, 10, 110, 22, 58),
        ("Embung Wisdom Park", "Titik 2", 7, 46, 7, 110, 22, 58),
        ("Embung Wisdom Park", "Titik 3", 7, 46, 7, 110, 23, 0),
        ("Embung Wisdom Park", "Titik 4", 7, 46, 9, 110, 22, 59),
        ("Embung Langensari", "Titik 1", 7, 47, 13, 110, 22, 54),
        ("Embung Langensari", "Titik 2", 7, 47, 12, 110, 22, 55),
        ("Embung Langensari", "Titik 3", 7, 47, 10, 110, 22, 52),
        ("Embung Langensari", "Titik 4", 7, 47, 10, 110, 22, 54),
    ]
    records = []
    for lok, tk, latd, latm, lats, lond, lonm, lons in raw:
        lat = dms_to_dd(latd, latm, lats, "S")
        lon = dms_to_dd(lond, lonm, lons, "E")
        records.append({"Lokasi": lok, "Titik": tk, "lat": lat, "lon": lon})
    return pd.DataFrame(records)


def default_land_use():
    """Estimasi awal komposisi tata guna lahan (indikatif, HARUS divalidasi pengguna)."""
    data = {
        "Lokasi": ["Embung Wisdom Park", "Embung Langensari"],
        "Vegetasi/RTH (%)": [55, 30],
        "Badan Air (%)": [20, 25],
        "Lahan Terbangun/Perkerasan (%)": [20, 35],
        "Lainnya (jalan setapak, dek, dll) (%)": [5, 10],
    }
    return pd.DataFrame(data)


def default_meteo():
    """Placeholder faktor meteorologis udara -- TIDAK ada di laporan sumber."""
    data = {
        "Lokasi": ["Embung Wisdom Park", "Embung Langensari"],
        "Suhu Udara (C)": [np.nan, np.nan],
        "Kelembaban Udara (%)": [np.nan, np.nan],
        "Curah Hujan Harian (mm)": [np.nan, np.nan],
        "Kecepatan Angin (m/s)": [np.nan, np.nan],
    }
    return pd.DataFrame(data)


# ----------------------------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------------------------
df_air = load_kualitas_air()
df_alga = load_mikroalga()
df_titik = load_titik_koordinat()

if "land_use_df" not in st.session_state:
    st.session_state.land_use_df = default_land_use()
if "meteo_df" not in st.session_state:
    st.session_state.meteo_df = default_meteo()

# ----------------------------------------------------------------------------
# SIDEBAR NAVIGASI
# ----------------------------------------------------------------------------
st.sidebar.title("🌱 Navigasi")
halaman = st.sidebar.radio(
    "Pilih halaman",
    [
        "Beranda",
        "1. Data Kualitas Air & Mikroalga",
        "2. Tata Guna Lahan",
        "3. Faktor Meteorologis",
        "4. Analisis Keterkaitan",
        "5. Peta Lokasi Sampling",
        "6. Ringkasan & Unduh Data",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Data kualitas air & mikroalga bersumber dari laporan lapangan "
    "(16 Januari 2026, kondisi cuaca cerah. Wisdom Park pukul 09.30–10.30 WIB; "
             "Langensari pukul 11.00–12.00 WIB."
)

# ----------------------------------------------------------------------------
# HALAMAN: BERANDA
# ----------------------------------------------------------------------------
if halaman == "Beranda":
    render_header_banner(
        title="Analisis Tata Guna Lahan, Faktor Meteorologis, dan Komunitas Mikroalga",
        subtitle="Studi Kasus: Embung Wisdom Park (UGM) & Embung Langensari, Yogyakarta",
        img_path=HEADER_IMG_PATH,
    )

    st.markdown("**Peneliti:**")
    st.markdown(
        "**Ir. Intan Supraba, S.T., M.Sc., Ph.D., IPM., ASEAN.Eng.** - "
        "Departemen Teknik Sipil Dan Teknik Lingkungan-UGM  \n"
        "**Adipandang Yudono, S.Si., MURP., PhD** - "
        "Departemen Perencanaan Wilayah dan Kota-UB"
    )

    st.markdown("--------------------------------------------------------------------------------------------------------------------------------")
    st.markdown(
        """
Riset ini menghubungkan tiga aspek pada dua embung di Yogyakarta:

1. **Kualitas air & komunitas mikroalga** — diambil dari data sampling lapangan
   (suhu air, pH, DO, TDS, dan hasil identifikasi mikroalga per titik/kedalaman).
2. **Tata guna lahan di sekitar embung** — modul interaktif untuk memasukkan
   komposisi lahan (vegetasi/RTH, badan air, lahan terbangun, dll).
3. **Faktor meteorologis udara** — modul interaktif untuk suhu udara,
   kelembaban, curah hujan, dan kecepatan angin.

Ketiganya kemudian dianalisis bersama pada halaman **Analisis Keterkaitan**
untuk membangun hipotesis tentang bagaimana kondisi lahan sekitar dan iklim
mikro berkaitan dengan dominansi kelas/spesies mikroalga tertentu.
        """
    )

    st.info(
        "⚠️ **Catatan metodologis:** Laporan sumber hanya memuat parameter "
        "suhu air, pH, DO, dan TDS. Data tata guna lahan dan meteorologi udara "
        "BELUM tersedia di laporan tersebut, sehingga pada aplikasi ini "
        "disediakan sebagai nilai estimasi/placeholder yang dapat (dan sebaiknya) "
        "Anda timpa dengan data primer -- misalnya hasil klasifikasi citra "
        "Sentinel-2 via Google Earth Engine, atau data harian BMKG terdekat."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Jumlah Lokasi", "3", help="Wisdom Park, Langensari, Air Tampungan RT")
    col2.metric("Jumlah Titik Sampling", "8", help="4 titik x 2 embung")
    col3.metric("Jumlah Spesies Teridentifikasi", f"{df_alga['Spesies'].nunique()}")


# ----------------------------------------------------------------------------
# HALAMAN 1: DATA KUALITAS AIR & MIKROALGA
# ----------------------------------------------------------------------------
elif halaman == "1. Data Kualitas Air & Mikroalga":
    st.header("1. Data Kualitas Air & Komunitas Mikroalga")

    st.subheader("1.1 Parameter Fisika-Kimia Air")
    st.dataframe(df_air, use_container_width=True)

    fig1 = px.bar(
        df_air, x="Lokasi", y=["Suhu_Air_C", "pH", "DO_mgL", "TDS_mgL"],
        facet_col="variable", facet_col_wrap=2, color="Titik", barmode="group",
        title="Perbandingan Parameter Fisika-Kimia Air antar Lokasi & Titik",
    )
    fig1.update_yaxes(matches=None)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("1.2 Hasil Identifikasi Mikroalga")
    lokasi_filter = st.multiselect(
        "Filter lokasi", options=df_alga["Lokasi"].unique(),
        default=list(df_alga["Lokasi"].unique())
    )
    df_alga_f = df_alga[df_alga["Lokasi"].isin(lokasi_filter)]
    st.dataframe(df_alga_f, use_container_width=True)

    st.markdown("**Spesies dominan per titik:**")
    dom = df_alga_f[df_alga_f["Dominan"]]
    st.table(dom[["Lokasi", "Titik", "Kelas", "Spesies"]].reset_index(drop=True))

    st.subheader("1.3 Komposisi Kelas Mikroalga per Lokasi")
    komposisi = df_alga_f.groupby(["Lokasi", "Kelas"]).size().reset_index(name="Jumlah Spesies")
    fig2 = px.bar(
        komposisi, x="Lokasi", y="Jumlah Spesies", color="Kelas",
        title="Jumlah Spesies per Kelas Mikroalga per Lokasi", barmode="stack",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ----------------------------------------------------------------------------
# HALAMAN 2: TATA GUNA LAHAN
# ----------------------------------------------------------------------------
elif halaman == "2. Tata Guna Lahan":
    st.header("2. Tata Guna Lahan Sekitar Embung")

    st.warning(
        "Data di bawah ini adalah **estimasi awal indikatif** (interpretasi visual "
        "foto lokasi pada laporan), BUKAN hasil klasifikasi citra satelit. "
        "Silakan edit langsung tabel berikut dengan hasil klasifikasi tata guna "
        "lahan Anda sendiri (contoh: hasil olahan citra Sentinel-2/GEE, atau "
        "digitasi RBI/peta rupabumi)."
    )

    edited = st.data_editor(
        st.session_state.land_use_df,
        num_rows="fixed",
        use_container_width=True,
        key="land_use_editor",
    )
    st.session_state.land_use_df = edited

    # validasi total 100%
    numeric_cols = edited.columns[1:]
    totals = edited[numeric_cols].sum(axis=1)
    for i, row in edited.iterrows():
        if abs(totals[i] - 100) > 0.5:
            st.error(
                f"Total persentase untuk **{row['Lokasi']}** = {totals[i]:.1f}%, "
                "sebaiknya berjumlah 100%."
            )

    st.subheader("Visualisasi Komposisi Lahan")
    c1, c2 = st.columns(2)
    for idx, col in zip([c1, c2], edited["Lokasi"]):
        row = edited[edited["Lokasi"] == col].iloc[0]
        fig = px.pie(
            names=numeric_cols, values=[row[c] for c in numeric_cols],
            title=f"Tata Guna Lahan — {col}", hole=0.35,
        )
        idx.plotly_chart(fig, use_container_width=True)

    st.markdown(
        """
### Opsi: Unggah Data Tata Guna Lahan Sendiri
Jika Anda memiliki hasil klasifikasi tata guna lahan (misalnya dari GEE, QGIS,
atau ArcGIS) dalam format CSV dengan kolom `Lokasi` dan persentase per kelas,
Anda dapat mengunggahnya untuk menggantikan tabel di atas.
        """
    )
    upload_lu = st.file_uploader("Unggah CSV tata guna lahan", type=["csv"], key="lu_upload")
    if upload_lu is not None:
        try:
            new_lu = pd.read_csv(upload_lu)
            st.session_state.land_use_df = new_lu
            st.success("Data tata guna lahan berhasil diperbarui dari file unggahan. Silakan buka ulang halaman ini.")
            st.dataframe(new_lu, use_container_width=True)
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

# ----------------------------------------------------------------------------
# HALAMAN 3: FAKTOR METEOROLOGIS
# ----------------------------------------------------------------------------
elif halaman == "3. Faktor Meteorologis":
    st.header("3. Faktor Meteorologis")

    st.warning(
        "Laporan sumber **tidak memuat data meteorologi udara** (hanya suhu air). "
        "Isi tabel di bawah ini dengan data BMKG stasiun terdekat pada tanggal "
        "sampling (16 Januari 2026) atau data logger lapangan Anda sendiri."
    )

    edited_meteo = st.data_editor(
        st.session_state.meteo_df,
        num_rows="fixed",
        use_container_width=True,
        key="meteo_editor",
    )
    st.session_state.meteo_df = edited_meteo

    st.markdown("### Suhu Air (tersedia dari laporan) vs Suhu Udara (input manual)")
    suhu_air_lok = df_air.groupby("Lokasi")["Suhu_Air_C"].mean().reset_index()
    suhu_air_lok = suhu_air_lok[suhu_air_lok["Lokasi"].isin(edited_meteo["Lokasi"])]
    gabung_suhu = suhu_air_lok.merge(
        edited_meteo[["Lokasi", "Suhu Udara (C)"]], on="Lokasi", how="left"
    )
    st.dataframe(gabung_suhu, use_container_width=True)

    if gabung_suhu["Suhu Udara (C)"].notna().any():
        fig3 = px.bar(
            gabung_suhu.melt(id_vars="Lokasi", value_vars=["Suhu_Air_C", "Suhu Udara (C)"]),
            x="Lokasi", y="value", color="variable", barmode="group",
            title="Perbandingan Suhu Air vs Suhu Udara",
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Isi kolom 'Suhu Udara (C)' pada tabel di atas untuk menampilkan grafik perbandingan.")

    st.markdown(
        """
### Opsi: Unggah Data Meteorologi Time Series
Untuk analisis yang lebih kuat (misalnya tren curah hujan beberapa hari sebelum
sampling terhadap kelimpahan mikroalga), unggah data harian dalam format CSV
dengan kolom `Tanggal`, `Suhu_Udara_C`, `Kelembaban_persen`, `Curah_Hujan_mm`.
        """
    )
    upload_met = st.file_uploader("Unggah CSV data meteorologi harian", type=["csv"], key="met_upload")
    if upload_met is not None:
        try:
            df_met_ts = pd.read_csv(upload_met)
            st.dataframe(df_met_ts, use_container_width=True)
            if "Tanggal" in df_met_ts.columns:
                fig_ts = px.line(df_met_ts, x="Tanggal", y=df_met_ts.columns[1:], title="Time Series Meteorologi")
                st.plotly_chart(fig_ts, use_container_width=True)
        except Exception as e:
            st.error(f"Gagal membaca file: {e}")

# ----------------------------------------------------------------------------
# HALAMAN 4: ANALISIS KETERKAITAN
# ----------------------------------------------------------------------------
elif halaman == "4. Analisis Keterkaitan":
    st.header("4. Analisis Keterkaitan: Tata Guna Lahan, Meteorologi & Mikroalga")

    st.subheader("4.1 Korelasi antar Parameter Fisika-Kimia Air")
    st.caption("Catatan: n = 5 sampel, korelasi bersifat indikatif, bukan hasil uji statistik inferensial.")
    corr_df = df_air[["Suhu_Air_C", "pH", "DO_mgL", "TDS_mgL"]].corr()
    fig_corr = px.imshow(
        corr_df, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        title="Matriks Korelasi Parameter Fisika-Kimia Air",
    )
    st.plotly_chart(fig_corr, use_container_width=True)

    st.subheader("4.2 Ringkasan Kondisi per Lokasi")
    ringkasan = df_air.groupby("Lokasi").agg(
        Suhu_rata=("Suhu_Air_C", "mean"),
        pH_rata=("pH", "mean"),
        DO_rata=("DO_mgL", "mean"),
        TDS_rata=("TDS_mgL", "mean"),
    ).reset_index()
    lu = st.session_state.land_use_df
    ringkasan = ringkasan.merge(lu, on="Lokasi", how="left")
    st.dataframe(ringkasan, use_container_width=True)

    st.subheader("4.3 Matriks Keterkaitan Spesies Dominan — Kondisi Lingkungan — Hipotesis Tata Guna Lahan")

    keterkaitan = pd.DataFrame([
        {
            "Lokasi": "Embung Wisdom Park",
            "Spesies Dominan": "Chlorococcum sp. (permukaan & kedalaman)",
            "Kondisi Air Pendukung": "Suhu 25.2–25.5°C, pH mendekati netral (6.83–6.96), DO tinggi (~7.1 mg/L), TDS rendah-sedang (127–143 mg/L)",
            "Hipotesis Keterkaitan Lahan": (
                "Proporsi vegetasi/RTH yang relatif tinggi di sekitar embung diduga "
                "menekan input nutrien limpasan (runoff) dan menjaga suhu air stabil, "
                "kondisi yang cenderung mendukung alga hijau toleran seperti Chlorococcum "
                "sp. dibanding taksa yang membutuhkan nutrien/silika tinggi."
            ),
        },
        {
            "Lokasi": "Embung Langensari",
            "Spesies Dominan": "Pinnularia sp. (permukaan); Chlorella sp. & Chlorococcum sp. (kedalaman)",
            "Kondisi Air Pendukung": "pH netral-sedikit basa (7.07–7.22), TDS lebih tinggi (145–205 mg/L), DO bervariasi (4.11–7.3 mg/L)",
            "Hipotesis Keterkaitan Lahan": (
                "Proporsi lahan terbangun/perkerasan yang relatif lebih tinggi (mis. "
                "jalur lari, area publik) berpotensi meningkatkan limpasan nutrien dan "
                "partikel terlarut (tercermin pada TDS lebih tinggi), mendukung "
                "dominansi diatom bentik (Pinnularia sp.) di permukaan dan alga hijau "
                "toleran cahaya rendah (Chlorella sp.) di kedalaman."
            ),
        },
        {
            "Lokasi": "Air Tampungan Rumah Tangga",
            "Spesies Dominan": "Nostoc sp.",
            "Kondisi Air Pendukung": "Suhu tertinggi (26°C), pH mendekati basa (6.84), TDS tinggi (191 mg/L)",
            "Hipotesis Keterkaitan Lahan": (
                "Sistem tampungan domestik dengan sirkulasi terbatas dan kemungkinan "
                "input nutrien dari aktivitas rumah tangga sekitarnya mendukung "
                "dominansi sianobakteri pembentuk koloni seperti Nostoc sp."
            ),
        },
    ])
    st.dataframe(keterkaitan, use_container_width=True, hide_index=True)

    st.info(
        "Kolom **Hipotesis Keterkaitan Lahan** bersifat argumentatif berdasarkan pola "
        "umum ekologi mikroalga dan estimasi tata guna lahan pada halaman 2. Untuk "
        "manuskrip ilmiah, hipotesis ini perlu diuji lebih lanjut (mis. korelasi "
        "kuantitatif antara persentase tutupan lahan hasil klasifikasi citra dengan "
        "kelimpahan/biomassa mikroalga aktual, idealnya dengan jumlah titik & waktu "
        "sampling yang lebih banyak)."
    )

    st.subheader("4.4 Radar Perbandingan Kondisi Dua Embung Utama")
    radar_df = ringkasan[ringkasan["Lokasi"].isin(["Embung Wisdom Park", "Embung Langensari"])]
    categories = ["Suhu_rata", "pH_rata", "DO_rata", "TDS_rata"]
    fig_radar = go.Figure()
    for _, r in radar_df.iterrows():
        vals = [r[c] for c in categories]
        fig_radar.add_trace(go.Scatterpolar(r=vals + [vals[0]], theta=categories + [categories[0]],
                                             fill='toself', name=r["Lokasi"]))
    fig_radar.update_layout(title="Perbandingan Parameter Kualitas Air (Rata-rata)")
    st.plotly_chart(fig_radar, use_container_width=True)

# ----------------------------------------------------------------------------
# HALAMAN 5: PETA LOKASI SAMPLING
# ----------------------------------------------------------------------------
elif halaman == "5. Peta Lokasi Sampling":
    st.header("5. Peta Lokasi Sampling")

    dom_per_titik = df_alga[df_alga["Dominan"]].groupby(["Lokasi"]).agg(
        Spesies_Dominan=("Spesies", lambda x: ", ".join(sorted(set(x))))
    ).reset_index()

    df_map = df_titik.merge(dom_per_titik, on="Lokasi", how="left")

    fig_map = px.scatter_mapbox(
        df_map, lat="lat", lon="lon", color="Lokasi", hover_name="Titik",
        hover_data={"Spesies_Dominan": True, "lat": False, "lon": False},
        zoom=15, height=550,
    )
    fig_map.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_map, use_container_width=True)

    st.dataframe(df_map, use_container_width=True)

    st.caption(
        "Koordinat dikonversi dari format DMS pada Gambar 3 & 4 laporan lapangan. "
        "Gunakan peta ini sebagai acuan awal untuk overlay dengan peta tutupan lahan "
        "(mis. citra Sentinel-2) pada QGIS/GEE."
    )

# ----------------------------------------------------------------------------
# HALAMAN 6: RINGKASAN & UNDUH DATA
# ----------------------------------------------------------------------------
elif halaman == "6. Ringkasan & Unduh Data":
    st.header("6. Ringkasan & Unduh Data")

    st.subheader("Narasi Ringkasan (Draf Otomatis)")
    lu = st.session_state.land_use_df
    met = st.session_state.meteo_df

    def get_lu_text(lokasi):
        row = lu[lu["Lokasi"] == lokasi]
        if row.empty:
            return "data tata guna lahan belum diisi"
        row = row.iloc[0]
        return (f"vegetasi/RTH {row['Vegetasi/RTH (%)']}%, badan air {row['Badan Air (%)']}%, "
                f"lahan terbangun/perkerasan {row['Lahan Terbangun/Perkerasan (%)']}%")

    narasi = f"""
Pada Embung Wisdom Park, komunitas mikroalga didominasi oleh *Chlorococcum sp.*
baik di lapisan permukaan maupun kedalaman 0.8–1 m, pada kondisi perairan
bersuhu 25.2–25.5°C, pH 6.83–6.96, dan DO sekitar 7.1 mg/L. Estimasi tata guna
lahan di sekitar lokasi ini menunjukkan {get_lu_text('Embung Wisdom Park')}.

Pada Embung Langensari, dominansi mikroalga berbeda antar kedalaman: lapisan
permukaan didominasi diatom *Pinnularia sp.*, sedangkan lapisan kedalaman
didominasi *Chlorella sp.* dan *Chlorococcum sp.*, pada kondisi TDS yang lebih
tinggi (145–205 mg/L) dibanding Wisdom Park. Estimasi tata guna lahan di sekitar
lokasi ini menunjukkan {get_lu_text('Embung Langensari')}.

Sampel air tampungan rumah tangga menunjukkan dominansi sianobakteri
*Nostoc sp.*, mengindikasikan kondisi perairan dengan sirkulasi terbatas dan
potensi input nutrien dari aktivitas domestik di sekitarnya.

Catatan: narasi ini adalah draf otomatis berbasis data yang tersedia pada
aplikasi ini per {date.today().strftime('%d %B %Y')}; mohon disunting kembali
sesuai kaidah penulisan ilmiah dan hasil analisis lanjutan sebelum digunakan
dalam manuskrip.
"""
    st.markdown(narasi)

    st.subheader("Unduh Dataset Gabungan")
    ringkasan_full = df_air.groupby("Lokasi").agg(
        Suhu_rata=("Suhu_Air_C", "mean"), pH_rata=("pH", "mean"),
        DO_rata=("DO_mgL", "mean"), TDS_rata=("TDS_mgL", "mean"),
    ).reset_index().merge(lu, on="Lokasi", how="left").merge(met, on="Lokasi", how="left")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        df_air.to_excel(writer, sheet_name="Kualitas_Air", index=False)
        df_alga.to_excel(writer, sheet_name="Mikroalga", index=False)
        lu.to_excel(writer, sheet_name="Tata_Guna_Lahan", index=False)
        met.to_excel(writer, sheet_name="Meteorologi", index=False)
        ringkasan_full.to_excel(writer, sheet_name="Ringkasan", index=False)

    st.download_button(
        "⬇️ Unduh Dataset Gabungan (Excel)",
        data=buf.getvalue(),
        file_name="analisis_embung_wisdompark_langensari.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.download_button(
        "⬇️ Unduh Narasi Ringkasan (TXT)",
        data=narasi,
        file_name="narasi_ringkasan.txt",
        mime="text/plain",
    )
