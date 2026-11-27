"""
Dashboard Prediksi Permintaan & Titik Restock Obat — Apotek Bintan Medika
Proyek Penambangan Data (INF11121), Universitas Maritim Raja Ali Haji

Jalankan:  streamlit run app.py
"""
import io
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import logika as L

st.set_page_config(page_title="Dashboard Restock Apotek Bintan Medika", layout="wide")

st.markdown("""
<style>
    /* 1. Latar belakang utama gradasi hijau */
    [data-testid="stAppViewContainer"], .stApp {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 50%, #f1f8e9 100%) !important;
        color: #1b4332 !important;
    }
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* 2. Semua teks judul, label, dan keterangan (PEKAT & TEBAL) */
    [data-testid="stWidgetLabel"] p {
        color: #1b4332 !important;
        font-size: 16.5px !important;
        font-weight: 700 !important;
    }
    div[data-testid="stCaptionContainer"],
    div[data-testid="stCaptionContainer"] p,
    div[data-testid="stCaptionContainer"] div,
    .stCaption,
    small {
        color: #1b4332 !important;
        font-size: 15.5px !important;
        font-weight: 600 !important;
        opacity: 1 !important;
    }
    [data-testid="stMarkdownContainer"] p {
        color: #1b4332 !important;
        font-size: 16px !important;
        font-weight: 500 !important;
    }
    /* Angka di atas & bawah slider (misal 1, 7, 14) */
    [data-testid="stSliderTickBarMin"],
    [data-testid="stSliderTickBarMax"],
    [data-testid="stThumbValue"] {
        font-size: 14.5px !important;
        color: #1b4332 !important;
        font-weight: 700 !important;
    }

    /* 3. Kotak pengaturan restock */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: rgba(255, 255, 255, 0.78) !important;
        border: 1px solid #81c784 !important;
        border-radius: 10px !important;
    }

    /* 4. KOTAK DROPDOWN & MULTISELECT - PUTIH & TEKS TEBAL */
    [data-baseweb="select"],
    [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #1b4332 !important;
        font-size: 15.5px !important;
        font-weight: 600 !important;
    }
    [data-baseweb="select"] > div {
        border: 1.5px solid #66bb6a !important;
        border-radius: 8px !important;
    }
    [data-baseweb="select"] svg {
        fill: #1b4332 !important;
    }
    /* Tag hijau di dalam multiselect obat */
    [data-baseweb="tag"] {
        background-color: #2e7d32 !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tag"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 14px !important;
    }
    [data-baseweb="tag"] svg {
        fill: #ffffff !important;
    }
    [data-baseweb="popover"] ul,
    [data-baseweb="popover"] li,
    li[role="option"] {
        background-color: #ffffff !important;
        color: #1b4332 !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #e8f5e9 !important;
        color: #1b5e20 !important;
    }

    /* 5. IKON TANDA TANYA (?) & KOTAK DESKRIPSI SAAT DI-HOVER (TOOLTIP) */
    [data-testid="stTooltipIcon"] svg {
        fill: none !important;
        stroke: #1b4332 !important;
    }
    div[role="tooltip"],
    div[role="tooltip"] > div,
    [data-baseweb="tooltip"] > div,
    [data-testid="stTooltipContent"] {
        background-color: #ffffff !important;
        color: #1b4332 !important;
        border: 1.5px solid #66bb6a !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12) !important;
    }
    div[role="tooltip"] p,
    [data-baseweb="tooltip"] p,
    [data-testid="stTooltipContent"] p {
        color: #1b4332 !important;
        font-size: 14.5px !important;
        font-weight: 600 !important;
    }

    /* 6. Tombol navigasi & tombol sekunder */
    button[kind="secondary"],
    button[data-testid="stBaseButton-secondary"] {
        background-color: #ffffff !important;
        border: 1.5px solid #4caf50 !important;
    }
    button[kind="secondary"] p,
    button[data-testid="stBaseButton-secondary"] p {
        color: #1b4332 !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }
    button[kind="secondary"]:hover,
    button[data-testid="stBaseButton-secondary"]:hover {
        background-color: #e8f5e9 !important;
        border-color: #1b5e20 !important;
    }
    button[kind="primary"],
    button[data-testid="stBaseButton-primary"] {
        background-color: #2e7d32 !important;
        border-color: #2e7d32 !important;
    }
    button[kind="primary"] p,
    button[data-testid="stBaseButton-primary"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }
    button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        background-color: #1b5e20 !important;
        border-color: #1b5e20 !important;
    }

    /* 7. Kotak upload file & alert biru */
    [data-testid="stFileUploaderDropzone"] {
        background-color: #ffffff !important;
        border: 1.5px dashed #2e7d32 !important;
    }
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small {
        color: #1b4332 !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }
    [data-testid="stAlert"] {
        background-color: #e3f2fd !important;
        border: 1px solid #64b5f6 !important;
        border-radius: 8px !important;
    }
    [data-testid="stAlert"] p {
        color: #0d47a1 !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    [data-testid="stAlert"] svg {
        fill: #0d47a1 !important;
    }

    /* 8. Tabel HTML Kustom yang Super Tajam & Tebal */
    .tabel-tebal-wrap {
        max-height: 290px;
        overflow-y: auto;
        border: 1.5px solid #81c784;
        border-radius: 8px;
        background-color: #ffffff;
        margin-bottom: 12px;
    }
    .tabel-tebal {
        width: 100%;
        border-collapse: collapse;
        font-family: sans-serif;
    }
    .tabel-tebal th {
        position: sticky;
        top: 0;
        background-color: #e8f5e9;
        color: #1b4332 !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        padding: 10px 14px;
        border-bottom: 1.5px solid #81c784;
        text-align: left;
    }
    .tabel-tebal td {
        color: #1b4332 !important;
        font-weight: 700 !important;
        font-size: 14.5px !important;
        padding: 9px 14px;
        border-bottom: 1px solid #e0e0e0;
    }
    .tabel-tebal tr:hover td {
        background-color: #f1f8e9;
    }
    .tabel-tebal th.kanan, .tabel-tebal td.kanan {
        text-align: right;
    }

    /* Bingkai tabel data editor */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border: 1.5px solid #81c784 !important;
        border-radius: 8px !important;
        background-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

BLN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
OBAT_CONTOH = ["ANDALAN", "VICEE", "KADITIC", "MEFINAL", "DEXAHARSEN 0,75MG"]
STOK_CONTOH = {"ANDALAN": 55, "VICEE": 415, "KADITIC": 160, "MEFINAL": 0, "DEXAHARSEN 0,75MG": 360}
FILE_CONTOH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_contoh", "contoh_penjualan_5_obat.xlsx")
LAMPU = {"MERAH": "🔴", "KUNING": "🟡", "HIJAU": "🟢"}
KET_STATUS = {"MERAH": "Pesan sekarang", "KUNING": "Segera siapkan pesanan", "HIJAU": "Stok aman"}


def tgl(ts):
    return f"{ts.day} {BLN[ts.month - 1]} {ts.year}"


def rentang(ts):
    akhir = ts + pd.Timedelta(days=6)
    return f"{ts.day} {BLN[ts.month - 1]} – {akhir.day} {BLN[akhir.month - 1]} {akhir.year}"


def kategori_mape(m):
    if m != m:
        return "tidak dapat dihitung"
    return "sangat baik" if m < 10 else "baik" if m < 20 else "cukup" if m < 50 else "kurang akurat"


def render_tabel_tebal(df_in, kolom_kanan=None, format_angka=None):
    kolom_kanan = set(kolom_kanan or [])
    format_angka = format_angka or {}
    ths = "".join(
        f'<th class="{"kanan" if c in kolom_kanan else ""}">{c}</th>'
        for c in df_in.columns
    )
    rows_html = []
    for _, row in df_in.iterrows():
        tds = []
        for c in df_in.columns:
            val = row[c]
            if c in format_angka and pd.notna(val):
                val_str = format_angka[c].format(val)
            else:
                val_str = str(val)
            tds.append(f'<td class="{"kanan" if c in kolom_kanan else ""}">{val_str}</td>')
        rows_html.append(f"<tr>{''.join(tds)}</tr>")
    html = f'<div class="tabel-tebal-wrap"><table class="tabel-tebal"><thead><tr>{ths}</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)


# ------------------------------------------------------------------ state
for k, v in {"df": None, "log": None, "produk_tabel": None, "hasil": None, "mingguan": None,
             "info": None, "stok": {}, "satuan": {}, "obat_pilih": [], "sumber_data": "",
             "halaman": "Input Data"}.items():
    st.session_state.setdefault(k, v)

daftar_hal = ["Input Data", "Hasil Mining (Prediksi)", "Dashboard Restock"]
if st.session_state["halaman"] not in daftar_hal:
    st.session_state["halaman"] = "Input Data"

# ------------------------------------------------------------------ topbar
col_judul, col_nav = st.columns([1.2, 1.8])
with col_judul:
    st.markdown("## Apotek Bintan Medika")

with col_nav:
    st.write("")
    nav_cols = st.columns(3)
    for idx, nama_hal in enumerate(daftar_hal):
        aktif = st.session_state["halaman"] == nama_hal
        if nav_cols[idx].button(
            nama_hal,
            key=f"nav_btn_{idx}",
            use_container_width=True,
            type="primary" if aktif else "secondary"
        ):
            st.session_state["halaman"] = nama_hal
            st.rerun()

halaman = st.session_state["halaman"]
st.divider()


# ------------------------------------------------------------------ helper functions
def hitung_semua(obat, keluarkan_grosir):
    mg, info = L.deret_mingguan(st.session_state["df"], obat, keluarkan_grosir)
    hasil = {}
    peringatan = []
    for o in obat:
        if o not in mg.columns or len(mg) < L.MIN_MINGGU:
            peringatan.append(o)
            continue
        hasil[o] = L.cari_model(mg[o].values)
    st.session_state.update(mingguan=mg, info=info, hasil=hasil)
    return peringatan


def muat_data(daftar_file, label):
    mentah = []
    for f in daftar_file:
        mentah.append(L.baca_penjualan(f, getattr(f, "name", "data")))
    df, log = L.bersihkan(pd.concat(mentah, ignore_index=True))
    df = L.tandai_grosir(df)
    prod = L.ringkasan_produk(df)
    prod["non_obat"] = [L.non_obat(p) for p in prod.index]
    st.session_state.update(df=df, log=log, produk_tabel=prod, sumber_data=label, hasil=None, mingguan=None)
    kandidat = [p for p in prod.index if not L.non_obat(p)]
    st.session_state["obat_pilih"] = kandidat[:5]
    st.session_state["satuan"] = prod["satuan"].to_dict()


# ================================================================== HALAMAN 1
if halaman == "Input Data":
    st.title("Input Data")
    st.write("Unggah laporan penjualan dari sistem apotek (berkas Excel hasil ekspor, boleh lebih dari satu periode). "
             "Pembersihan data dilakukan otomatis.")
    c1, c2 = st.columns([3, 1])
    with c1:
        files = st.file_uploader("Berkas penjualan (.xlsx / .csv)", type=["xlsx", "csv"], accept_multiple_files=True,
                                 help="Format ekspor sistem apotek (lembar 'Stok Terjual') atau tabel dengan kolom tanggal, nama produk, jumlah.")
    with c2:
        st.write("")
        st.write("")
        pakai_contoh = st.button("Pakai data contoh", width="stretch",
                                 help="Data penjualan 5 obat, 1 Okt 2025 – 30 Sep 2026")
    try:
        if pakai_contoh:
            with open(FILE_CONTOH, "rb") as fh:
                bio = io.BytesIO(fh.read())
            bio.name = "contoh_penjualan_5_obat.xlsx"
            muat_data([bio], "Data contoh (5 obat, Okt 2025 – Sep 2026)")
            st.session_state["stok"] = dict(STOK_CONTOH)
            st.session_state["obat_pilih"] = list(OBAT_CONTOH)
        elif files and (st.session_state["sumber_data"] != ",".join(sorted(f.name for f in files))):
            muat_data(files, ",".join(sorted(f.name for f in files)))
    except Exception as e:  # noqa: BLE001
        st.error(f"Gagal membaca berkas: {e}")

    df = st.session_state["df"]
    if df is None:
        st.info("Belum ada data. Unggah berkas penjualan atau klik **Pakai data contoh**.")
        st.stop()

    st.success(f"Data dimuat: {st.session_state['sumber_data']}")
    log = st.session_state["log"]
    m = st.columns(5)
    m[0].metric("Baris transaksi", f"{log['baris_bersih']:,}".replace(",", "."))
    m[1].metric("Mulai", tgl(df["tanggal"].min()))
    m[2].metric("Sampai", tgl(df["tanggal"].max()))
    m[3].metric("Jumlah hari", df["tanggal"].nunique())
    m[4].metric("Jumlah produk", df["produk"].nunique())
    with st.expander("Ringkasan pembersihan data"):
        st.write(f"- Baris awal: {log['baris_awal']:,}  → baris bersih: {log['baris_bersih']:,}".replace(",", "."))
        st.write(f"- Baris dengan jumlah tidak valid (nol/negatif) dibuang: {log['baris_jumlah_tidak_valid']}")
        st.write(f"- Baris dobel antar berkas (periode tumpang tindih) dibuang: {log['baris_dobel_antar_berkas']}")
        st.write(f"- Pembelian grosir terdeteksi (jumlah ≥ {L.GROSIR_MIN_ABS} dan ≥ {L.GROSIR_KALI_MEDIAN}× median produk): "
                 f"{int(df['grosir'].sum())} baris")
        st.write("- Nama produk diseragamkan (spasi dan huruf besar), tanggal dikonversi, produk non-obat dapat difilter.")

    st.subheader("Pilih obat yang diprediksi")
    prod = st.session_state["produk_tabel"]
    pilihan = [p for p in prod.index if not prod.loc[p, "non_obat"]]
    default = [o for o in st.session_state["obat_pilih"] if o in pilihan]
    obat = st.multiselect("Obat (urut berdasarkan jumlah hari terjual terbanyak)", pilihan, default=default,
                          help="Model paling cocok untuk obat yang terjual hampir setiap hari. Obat yang jarang terjual kurang cocok untuk MA dan SES.")
    sedikit = [o for o in obat if prod.loc[o, "persen_hari"] < 50]
    if sedikit:
        st.warning("Obat berikut terjual di kurang dari 50% hari sehingga permintaannya putus-putus dan prediksinya kurang andal: "
                   + ", ".join(sedikit))
    df_prod_tampil = (prod.loc[pilihan[:15], ["satuan", "total_jumlah", "hari_terjual", "persen_hari"]]
                      .reset_index()
                      .rename(columns={"index": "Produk", "produk": "Produk", "satuan": "Satuan",
                                       "total_jumlah": "Total jumlah", "hari_terjual": "Hari terjual", "persen_hari": "% hari"}))
    render_tabel_tebal(
        df_prod_tampil,
        kolom_kanan=["Total jumlah", "Hari terjual", "% hari"],
        format_angka={"Total jumlah": "{:.0f}", "Hari terjual": "{:.0f}", "% hari": "{:.1f}"}
    )
    grosir = st.checkbox("Keluarkan pembelian grosir dari deret prediksi (disarankan)", value=True,
                         help="Pembelian borongan bersifat sesekali sehingga tidak mencerminkan permintaan rutin.")
    if st.button("Proses data dan hitung prediksi", type="primary", disabled=not obat):
        with st.spinner("Menghitung deret mingguan dan mencari parameter terbaik..."):
            lewat = hitung_semua(obat, grosir)
        st.session_state["obat_pilih"] = obat
        if lewat:
            st.warning(f"Dilewati karena data kurang dari {L.MIN_MINGGU} minggu penuh: {', '.join(lewat)}")
        if st.session_state["hasil"]:
            st.toast("Perhitungan prediksi selesai!")
            st.session_state["halaman"] = "Hasil Mining (Prediksi)"
            st.rerun()

# ================================================================== HALAMAN 2
elif halaman == "Hasil Mining (Prediksi)":
    st.title("Hasil Mining: Prediksi Permintaan")
    hasil = st.session_state["hasil"]
    if not hasil:
        st.info("Belum ada hasil. Unggah data dan klik **Proses data** di halaman **Input Data**.")
        st.stop()
    info, mg = st.session_state["info"], st.session_state["mingguan"]
    st.caption(f"Data mingguan: {tgl(mg.index.min())} s/d {tgl(mg.index.max() + pd.Timedelta(days=6))} "
               f"({info['minggu_penuh']} minggu penuh). Prediksi untuk minggu **{rentang(info['minggu_prediksi'])}**.")

    ringkas = []
    for o, r in hasil.items():
        mn = r["menang"]
        ringkas.append({"Obat": o, "Metode terbaik": mn["metode"], "Parameter": mn["parameter"],
                        "MAPE uji (%)": round(mn["mape_uji"], 1), "Penilaian": kategori_mape(mn["mape_uji"]),
                        f"Prediksi minggu depan ({st.session_state['satuan'].get(o, '')})": round(mn["prediksi_depan"], 1)})
    tabel_ringkas = pd.DataFrame(ringkas)
    st.subheader("Ringkasan semua obat")
    kol_pred = [c for c in tabel_ringkas.columns if c.startswith("Prediksi")][0]
    render_tabel_tebal(tabel_ringkas, kolom_kanan=["MAPE uji (%)", kol_pred], format_angka={"MAPE uji (%)": "{:.1f}", kol_pred: "{:.1f}"})

    st.subheader("Detail per obat")
    o = st.selectbox("Pilih obat", list(hasil.keys()))
    r = hasil[o]
    mn = r["menang"]
    y = mg[o].values
    sat = st.session_state["satuan"].get(o, "")
    c = st.columns(4)
    c[0].metric("Metode terbaik", mn["metode"], mn["parameter"])
    c[1].metric("MAPE data uji", f"{mn['mape_uji']:.1f}%", kategori_mape(mn["mape_uji"]), delta_color="off")
    c[2].metric(f"Prediksi minggu depan ({sat})", f"{mn['prediksi_depan']:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."))
    c[3].metric("Galat rata-rata (MAE uji)", f"{mn['mae_uji']:.1f} {sat}")

    fr = r["prediksi_rolling"]
    fig = go.Figure()
    fig.add_vrect(x0=mg.index[r["n_latih"]] - pd.Timedelta(days=3.5), x1=mg.index[-1] + pd.Timedelta(days=3.5),
                  fillcolor="#DDEBF7", opacity=0.6, line_width=0, annotation_text="Data uji", annotation_position="top left")
    fig.add_trace(go.Scatter(x=mg.index, y=y, mode="lines+markers", name="Aktual", line=dict(color="#1F4E78", width=2)))
    fig.add_trace(go.Scatter(x=mg.index[r["mulai_eval"]:], y=fr[r["mulai_eval"]:], mode="lines+markers",
                             name=f"Prediksi {mn['metode']} ({mn['parameter']})", line=dict(color="#C00000", width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=[info["minggu_prediksi"]], y=[mn["prediksi_depan"]], mode="markers+text",
                             name="Prediksi minggu depan", marker=dict(color="#ED7D31", size=14, symbol="star"),
                             text=[f"{mn['prediksi_depan']:.0f}"], textposition="top center"))
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=30, b=10), yaxis_title=f"Jumlah terjual per minggu ({sat})",
                      legend=dict(orientation="h", y=-0.2), hovermode="x unified")
    st.plotly_chart(fig, width="stretch")
    if mn["minggu_kecil_uji"]:
        st.caption(f"Catatan: {int(mn['minggu_kecil_uji'])} minggu uji bernilai < {L.AMBANG_MAPE} unit tidak dihitung dalam MAPE.")

    st.markdown("**Perbandingan Moving Average vs SES** (parameter terbaik dipilih dari MAPE data latih, metode dibandingkan pada data uji)")
    bandingan = pd.DataFrame([r["terbaik"]["Moving Average"], r["terbaik"]["SES"]])
    bandingan["Terbaik"] = np.where(bandingan["metode"] == mn["metode"], "✔", "")
    df_banding = (bandingan[["metode", "parameter", "mape_latih", "mape_uji", "mae_uji", "prediksi_depan", "Terbaik"]]
                  .rename(columns={"metode": "Metode", "parameter": "Parameter", "mape_latih": "MAPE latih (%)", "mape_uji": "MAPE uji (%)",
                                   "mae_uji": "MAE uji", "prediksi_depan": "Prediksi minggu depan"}).round(2))
    render_tabel_tebal(
        df_banding,
        kolom_kanan=["MAPE latih (%)", "MAPE uji (%)", "MAE uji", "Prediksi minggu depan"],
        format_angka={"MAPE latih (%)": "{:.2f}", "MAPE uji (%)": "{:.2f}", "MAE uji": "{:.2f}", "Prediksi minggu depan": "{:.2f}"}
    )
    with st.expander("Semua kombinasi parameter (12 kombinasi)"):
        df_kombi = r["tabel"][["metode", "parameter", "mape_latih", "mape_uji", "mae_uji", "prediksi_depan"]].round(2)
        render_tabel_tebal(
            df_kombi,
            kolom_kanan=["mape_latih", "mape_uji", "mae_uji", "prediksi_depan"],
            format_angka={"mape_latih": "{:.2f}", "mape_uji": "{:.2f}", "mae_uji": "{:.2f}", "prediksi_depan": "{:.2f}"}
        )

    with st.expander("Simulasi rolling forecast: bagaimana prediksi diperbarui tiap minggu"):
        st.write("Geser untuk berpura-pura berada di minggu tertentu. Model hanya memakai data sampai minggu itu, "
                 "mencari parameter terbaik, lalu memprediksi minggu berikutnya. Setelah minggu berikutnya berjalan, "
                 "datanya ditambahkan dan prediksi dihitung ulang.")
        n_min = max(L.MIN_MINGGU, 10)
        if len(y) > n_min + 1:
            n_pakai = st.slider("Data yang tersedia sampai minggu ke-", n_min, len(y) - 1, len(y) - 1)
            sim = L.cari_model(y[:n_pakai])["menang"]
            aktual = y[n_pakai]
            cc = st.columns(4)
            cc[0].metric("Minggu yang diprediksi", rentang(mg.index[n_pakai]))
            cc[1].metric("Prediksi", f"{sim['prediksi_depan']:.1f}", f"{sim['metode']} {sim['parameter']}", delta_color="off")
            cc[2].metric("Aktual (kenyataan)", f"{aktual:.0f}")
            cc[3].metric("Galat", f"{abs(aktual - sim['prediksi_depan']):.1f}")
        else:
            st.write("Data terlalu pendek untuk simulasi.")

    unduh = io.BytesIO()
    with pd.ExcelWriter(unduh, engine="openpyxl") as xw:
        tabel_ringkas.to_excel(xw, sheet_name="Ringkasan", index=False)
        mg.reset_index().rename(columns={"index": "minggu_mulai"}).to_excel(xw, sheet_name="Data_Mingguan", index=False)
        for ob, rr in hasil.items():
            rr["tabel"].round(3).to_excel(xw, sheet_name=("Param_" + ob)[:31].replace(",", ""), index=False)
    st.download_button("Unduh hasil prediksi (Excel)", unduh.getvalue(), "hasil_prediksi.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ================================================================== HALAMAN 3
else:
    st.title("Dashboard Restock")
    hasil = st.session_state["hasil"]
    if not hasil:
        st.info("Belum ada hasil. Unggah data dan klik **Proses data** di halaman **Input Data**.")
        st.stop()

    with st.container(border=True):
        st.markdown("**Pengaturan Restock**")
        c_set1, c_set2, c_set3 = st.columns(3)
        with c_set1:
            lead_time = st.slider("Lead time pengadaan (hari)", 1, 14, 7,
                                  help="Waktu dari pesan sampai barang datang. Info apotek: 3–7 hari. Pakai 7 untuk kondisi terburuk.")
        with c_set2:
            layanan = st.selectbox("Tingkat layanan (stok pengaman)", list(L.Z_LAYANAN.keys()), index=1,
                                   help="Semakin tinggi, semakin kecil risiko stok habis, tetapi stok pengaman makin besar.")
        with c_set3:
            periode_pesan = st.slider("Periode antar pemesanan (hari)", 7, 60, 14,
                                      help="Seberapa sering apotek memesan. Dipakai untuk menghitung jumlah pesan.")
        st.caption("Rolling forecast: tiap minggu data baru diunggah, model dihitung ulang dan memprediksi minggu berikutnya.")

    z = L.Z_LAYANAN[layanan]
    info = st.session_state["info"]
    st.caption(f"Prediksi permintaan minggu {rentang(info['minggu_prediksi'])} · lead time {lead_time} hari · "
               f"tingkat layanan {layanan} · periode pemesanan {periode_pesan} hari.")

    st.subheader("Stok terkini")
    with st.expander("Isi stok dari ekspor Kartu Stok (opsional)"):
        ks = st.file_uploader("Berkas Kartu Stok per obat (.xlsx)", type=["xlsx"], accept_multiple_files=True, key="kartu")
        if ks:
            for f in ks:
                try:
                    nama, satuan, sisa = L.baca_kartu_stok(f)
                    if nama in hasil:
                        st.session_state["stok"][nama] = sisa
                except Exception as e:  # noqa: BLE001
                    st.error(f"{f.name}: {e}")
            st.success("Stok dari kartu stok dimuat.")
    stok_df = pd.DataFrame({"Obat": list(hasil.keys()),
                            "Stok terkini": [float(st.session_state["stok"].get(o, 0)) for o in hasil]})
    stok_edit = st.data_editor(stok_df, hide_index=True, disabled=["Obat"], width="stretch", key="editor_stok",
                               column_config={"Stok terkini": st.column_config.NumberColumn(min_value=0, step=1, help="Jumlah stok saat ini")})
    for _, row in stok_edit.iterrows():
        st.session_state["stok"][row["Obat"]] = float(row["Stok terkini"])
    if not st.session_state["stok"] or all(v == 0 for v in st.session_state["stok"].values()):
        st.warning("Stok belum diisi (bernilai 0), sehingga semua obat tampak merah. Isi stok terkini terlebih dahulu.")

    rek = []
    for o, r in hasil.items():
        mn = r["menang"]
        stk = st.session_state["stok"].get(o, 0)
        rs = L.hitung_restock(mn["prediksi_depan"], mn["rmse_semua"], stk, lead_time, z, periode_pesan)
        rek.append(dict(obat=o, satuan=st.session_state["satuan"].get(o, ""), stok=stk, prediksi=mn["prediksi_depan"],
                        metode=f"{mn['metode']} ({mn['parameter']})", **rs))
    rek = pd.DataFrame(rek)
    n = rek["status"].value_counts()
    c = st.columns(3)
    c[0].metric("🔴 Pesan sekarang", int(n.get("MERAH", 0)))
    c[1].metric("🟡 Segera siapkan", int(n.get("KUNING", 0)))
    c[2].metric("🟢 Stok aman", int(n.get("HIJAU", 0)))

    tampil = pd.DataFrame({
        "Lampu": rek["status"].map(LAMPU), "Obat": rek["obat"], "Status": rek["status"].map(KET_STATUS),
        "Stok": rek["stok"].round(0), "Titik restock": rek["rop"].round(0),
        "Prediksi / minggu": rek["prediksi"].round(1),
        "Stok cukup (hari)": rek["cukup_hari"].round(1),
        "Jumlah pesan": rek["jumlah_pesan"], "Satuan": rek["satuan"]})
    render_tabel_tebal(
        tampil,
        kolom_kanan=["Stok", "Titik restock", "Prediksi / minggu", "Stok cukup (hari)", "Jumlah pesan"],
        format_angka={"Stok": "{:.0f}", "Titik restock": "{:.0f}", "Prediksi / minggu": "{:.1f}", "Stok cukup (hari)": "{:.1f}", "Jumlah pesan": "{:.0f}"}
    )

    st.subheader("Grafik perpotongan stok dan titik restock")
    pilih = st.selectbox("Pilih obat", list(rek["obat"]))
    r = rek[rek["obat"] == pilih].iloc[0]
    hari = np.arange(0, 43)
    stok_proy = np.maximum(0, r["stok"] - r["per_hari"] * hari)
    tg0 = info["minggu_prediksi"]
    x = [tg0 + pd.Timedelta(days=int(h)) for h in hari]
    atas = max(r["stok"], r["rop"]) * 1.35 if max(r["stok"], r["rop"]) > 0 else 10
    fig = go.Figure()
    fig.add_hrect(y0=0, y1=r["rop"], fillcolor="#F8CBAD", opacity=0.35, line_width=0,
                  annotation_text="Zona di bawah titik restock", annotation_position="bottom right")
    fig.add_trace(go.Scatter(x=x, y=stok_proy, mode="lines", name="Stok (proyeksi turun sesuai prediksi)", line=dict(color="#1F4E78", width=3)))
    fig.add_trace(go.Scatter(x=[x[0], x[-1]], y=[r["rop"], r["rop"]], mode="lines", name="Titik restock",
                             line=dict(color="#C00000", width=2, dash="dash")))
    if r["status"] == "MERAH":
        cx, teks = x[0], f"Stok sudah di bawah titik restock → pesan sekarang ±{r['jumlah_pesan']:,} {r['satuan']}".replace(",", ".")
    else:
        cx = tg0 + pd.Timedelta(days=float(r["hari_ke_rop"]))
        teks = f"Mulai pesan {tgl(cx)} (±{r['jumlah_pesan']:,} {r['satuan']})".replace(",", ".")
    fig.add_trace(go.Scatter(x=[cx], y=[min(r["stok"], r["rop"]) if r["status"] == "MERAH" else r["rop"]], mode="markers+text",
                             name="Saat memesan", marker=dict(color="#C00000", size=13), text=[teks], textposition="top right"))
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=30, b=10), yaxis_title=f"Stok ({r['satuan']})", yaxis_range=[0, atas],
                      legend=dict(orientation="h", y=-0.2), hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

    d = st.columns(4)
    d[0].metric("Kebutuhan per hari", f"{r['per_hari']:.1f} {r['satuan']}")
    d[1].metric("Stok pengaman", f"{r['stok_pengaman']:.0f} {r['satuan']}")
    d[2].metric("Titik restock", f"{r['rop']:.0f} {r['satuan']}")
    d[3].metric("Target stok setelah pesan", f"{r['target']:.0f} {r['satuan']}")

    unduh = tampil.drop(columns=["Lampu"]).to_csv(index=False).encode("utf-8")
    st.download_button("Unduh rekomendasi pemesanan (CSV)", unduh, "rekomendasi_pemesanan.csv", "text/csv")
    with st.expander("Cara hitung dan asumsi"):
        st.markdown(
            "- **Kebutuhan per hari** = prediksi minggu depan ÷ 7.\n"
            "- **Stok pengaman** = z × RMSE galat prediksi × √(lead time ÷ 7).\n"
            "- **Titik restock** = kebutuhan per hari × lead time + stok pengaman.\n"
            "- **Jumlah pesan** = target stok − (stok atau titik restock, mana yang lebih kecil), "
            "dengan target stok = kebutuhan per hari × (lead time + periode pemesanan) + stok pengaman.\n"
            "- Permintaan diasumsikan konstan sesuai prediksi. Pembelian grosir dan pola musiman tidak dimodelkan.\n"
            "- Hasil ini adalah alat bantu keputusan. Keputusan pemesanan akhir tetap pada pihak apotek.")