"""
Logika data & model untuk Dashboard Restock Apotek Bintan Medika.

Isi:
  - membaca & membersihkan data penjualan (format ekspor sistem apotek atau tabel sederhana)
  - mengubah data harian menjadi deret mingguan (Senin-Minggu)
  - model Moving Average (MA) dan Single Exponential Smoothing (SES) + MAPE
  - pemilihan parameter & metode terbaik, prediksi minggu depan (rolling forecast)
  - titik restock (reorder point), stok pengaman, dan jumlah pesan
Semua rumus sama dengan yang dipakai di laporan (BAB IV-VI).
"""
import math
import re

import numpy as np
import pandas as pd

BULAN_ID = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6, "jul": 7,
            "agu": 8, "agt": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12}

# kata kunci produk non-obat (sama dengan preprocessing di laporan)
KATA_NON_OBAT = ["AICE", "TISU", "PARFUM", "KASSA", "HANDSCOON", "EASY TOUCH", "NESCO",
                 "POPOK", "SUSU", "MASKER", "HANSAPLAST", "FRESHCARE"]

NILAI_K = [2, 3, 4]
NILAI_ALPHA = [round(a / 10, 1) for a in range(1, 10)]
RASIO_LATIH = 0.8
AMBANG_MAPE = 5          # minggu dengan aktual < 5 unit tidak dihitung dalam MAPE
GROSIR_MIN_ABS = 100
GROSIR_KALI_MEDIAN = 10
MIN_MINGGU = 12          # minimal minggu penuh agar model dapat dievaluasi

Z_LAYANAN = {"90%": 1.28, "95%": 1.65, "98%": 2.05, "99%": 2.33}


# ----------------------------------------------------------------------------
# 1. Membaca data
# ----------------------------------------------------------------------------
def parse_tanggal(seri: pd.Series) -> pd.Series:
    """Menerima datetime, teks ISO, atau teks Indonesia ('1 Okt 2025 pukul 07.13')."""
    if pd.api.types.is_datetime64_any_dtype(seri):
        return seri

    def satu(x):
        if isinstance(x, (pd.Timestamp,)):
            return x
        s = str(x)
        m = re.match(r"\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})(?:\s+pukul\s+(\d{1,2})[.:](\d{2}))?", s)
        if m:
            d, b, y, h, mi = m.groups()
            bln = BULAN_ID.get(b.lower()[:3])
            if bln:
                return pd.Timestamp(int(y), bln, int(d), int(h or 0), int(mi or 0))
        return pd.to_datetime(s, errors="coerce")

    return seri.map(satu)


def _cari_kolom(df, kandidat):
    peta = {c.strip().lower(): c for c in df.columns}
    for k in kandidat:
        if k in peta:
            return peta[k]
    return None


def baca_penjualan(file, nama_file="data"):
    """Baca satu berkas penjualan (xlsx/csv). Mengembalikan DataFrame standar:
    tanggal, produk, jumlah, satuan, kode_struk, sumber."""
    nama = getattr(file, "name", nama_file)
    if str(nama).lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        xl = pd.ExcelFile(file)
        if "Stok Terjual" in xl.sheet_names:          # format ekspor sistem apotek
            df = xl.parse("Stok Terjual", header=9)
        else:
            df = xl.parse(xl.sheet_names[0])
    kt = _cari_kolom(df, ["tanggal transaksi", "tanggal", "tgl"])
    kp = _cari_kolom(df, ["nama produk", "produk", "nama obat", "obat"])
    kj = _cari_kolom(df, ["jumlah", "qty", "jumlah terjual"])
    ks = _cari_kolom(df, ["satuan"])
    kst = _cari_kolom(df, ["kode struk", "struk"])
    if not (kt and kp and kj):
        raise ValueError(f"Kolom tanggal, nama produk, dan jumlah tidak ditemukan di '{nama}'. "
                         f"Kolom yang ada: {list(df.columns)[:8]}")
    out = pd.DataFrame({
        "tanggal_waktu": parse_tanggal(df[kt]),
        "produk": df[kp].astype(str),
        "jumlah": pd.to_numeric(df[kj], errors="coerce"),
        "satuan": df[ks].astype(str) if ks else "",
        "kode_struk": df[kst].astype(str) if kst else "",
    })
    out["sumber"] = str(nama)
    return out


def bersihkan(df: pd.DataFrame):
    """Pembersihan: nama produk, jumlah valid, dobel antar berkas. Mengembalikan (df, log)."""
    log = {"baris_awal": len(df)}
    df = df.dropna(subset=["tanggal_waktu", "jumlah"]).copy()
    df = df[~df["produk"].str.lower().isin(["nan", ""])]
    df["produk"] = df["produk"].str.strip().str.replace(r"\s+", " ", regex=True).str.upper()
    df["satuan"] = df["satuan"].astype(str).str.strip().str.title()
    log["baris_jumlah_tidak_valid"] = int((df["jumlah"] <= 0).sum())
    df = df[df["jumlah"] > 0]
    df["tanggal"] = df["tanggal_waktu"].dt.normalize()

    # dobel hanya antar berkas berbeda (tumpang tindih periode); dobel dalam satu berkas dibiarkan
    # karena bisa berupa dua batch obat berbeda pada struk yang sama
    log["baris_dobel_antar_berkas"] = 0
    if df["sumber"].nunique() > 1 and (df["kode_struk"] != "").any():
        kunci = ["kode_struk", "produk", "jumlah", "tanggal_waktu"]
        urut = {s: i for i, s in enumerate(pd.unique(df["sumber"]))}
        df["_u"] = df["sumber"].map(urut)
        df = df.sort_values("_u", kind="stable")
        pertama = df.groupby(kunci)["_u"].transform("min")
        dobel = df["_u"] > pertama
        log["baris_dobel_antar_berkas"] = int(dobel.sum())
        df = df[~dobel].drop(columns="_u")
    log["baris_bersih"] = len(df)
    return df.reset_index(drop=True), log


def tandai_grosir(df: pd.DataFrame) -> pd.DataFrame:
    med = df.groupby("produk")["jumlah"].transform("median")
    df = df.copy()
    df["grosir"] = (df["jumlah"] >= GROSIR_MIN_ABS) & (df["jumlah"] >= GROSIR_KALI_MEDIAN * med)
    return df


def non_obat(nama: str) -> bool:
    return any(k in nama for k in KATA_NON_OBAT)


def ringkasan_produk(df: pd.DataFrame) -> pd.DataFrame:
    r = df.groupby("produk").agg(
        satuan=("satuan", "first"), total_jumlah=("jumlah", "sum"),
        jumlah_transaksi=("jumlah", "count"), hari_terjual=("tanggal", "nunique"))
    r["persen_hari"] = (r["hari_terjual"] / df["tanggal"].nunique() * 100).round(1)
    return r.sort_values(["hari_terjual", "total_jumlah"], ascending=False)


# ----------------------------------------------------------------------------
# 2. Deret mingguan
# ----------------------------------------------------------------------------
def deret_mingguan(df: pd.DataFrame, produk, keluarkan_grosir=True):
    """Jumlah terjual per minggu (Senin-Minggu), hanya minggu penuh, minggu kosong = 0.
    Mengembalikan (DataFrame minggu x produk, info)."""
    d = df[df["produk"].isin(produk)].copy()
    if keluarkan_grosir:
        d = d[~d["grosir"]]
    awal, akhir = df["tanggal"].min(), df["tanggal"].max()
    d["minggu"] = d["tanggal"] - pd.to_timedelta(d["tanggal"].dt.weekday, unit="D")
    mg = d.pivot_table(index="minggu", columns="produk", values="jumlah", aggfunc="sum")
    semua = pd.date_range(awal - pd.Timedelta(days=awal.weekday()), akhir, freq="7D")
    mg = mg.reindex(semua).fillna(0)
    penuh = [(m >= awal) and (m + pd.Timedelta(days=6) <= akhir) for m in mg.index]
    mg_penuh = mg[penuh]
    mg_penuh = mg_penuh.reindex(columns=[p for p in produk if p in mg_penuh.columns])
    info = {"data_awal": awal, "data_akhir": akhir, "minggu_penuh": len(mg_penuh),
            "minggu_dibuang": len(mg) - len(mg_penuh),
            "minggu_terakhir": mg_penuh.index.max() if len(mg_penuh) else None,
            "minggu_prediksi": (mg_penuh.index.max() + pd.Timedelta(days=7)) if len(mg_penuh) else None}
    return mg_penuh, info


# ----------------------------------------------------------------------------
# 3. Model
# ----------------------------------------------------------------------------
def prediksi_ma(y, k):
    f = np.full(len(y), np.nan)
    for t in range(k, len(y)):
        f[t] = y[t - k:t].mean()
    return f


def prediksi_ses(y, alpha):
    f = np.full(len(y), np.nan)
    if len(y) < 2:
        return f
    f[1] = y[0]
    for t in range(1, len(y) - 1):
        f[t + 1] = alpha * y[t] + (1 - alpha) * f[t]
    return f


def depan_ma(y, k):
    return float(y[-k:].mean())


def depan_ses(y, alpha):
    f = prediksi_ses(y, alpha)
    return float(alpha * y[-1] + (1 - alpha) * f[-1])


def metrik(y, f, idx):
    a, p = y[idx], f[idx]
    ok = ~np.isnan(p)
    a, p = a[ok], p[ok]
    if len(a) == 0:
        return np.nan, np.nan, np.nan, 0
    kecil = int((a < AMBANG_MAPE).sum())
    pakai = a >= AMBANG_MAPE
    mape = np.mean(np.abs((a[pakai] - p[pakai]) / a[pakai])) * 100 if pakai.any() else np.nan
    mae = float(np.mean(np.abs(a - p)))
    rmse = float(np.sqrt(np.mean((a - p) ** 2)))
    return mape, mae, rmse, kecil


def cari_model(y):
    """Grid search parameter MA & SES, bandingkan, pilih metode terbaik.
    Prosedur sama dengan laporan: parameter dipilih dari MAPE data latih, metode dari MAPE data uji."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    n_latih = int(round(n * RASIO_LATIH))
    mulai = max(NILAI_K)
    idx_latih = np.arange(mulai, n_latih)
    idx_uji = np.arange(n_latih, n)
    idx_semua = np.arange(mulai, n)

    kombinasi = []
    for k in NILAI_K:
        f = prediksi_ma(y, k)
        kombinasi.append(("Moving Average", f"k={k}", k, f, depan_ma(y, k)))
    for a in NILAI_ALPHA:
        f = prediksi_ses(y, a)
        kombinasi.append(("SES", f"alpha={a}", a, f, depan_ses(y, a)))

    baris = []
    for metode, param, nilai, f, depan in kombinasi:
        ml = metrik(y, f, idx_latih)
        mu = metrik(y, f, idx_uji)
        ms = metrik(y, f, idx_semua)
        baris.append(dict(metode=metode, parameter=param, nilai=nilai, mape_latih=ml[0], mape_uji=mu[0],
                          mae_uji=mu[1], rmse_semua=ms[2], minggu_kecil_uji=mu[3],
                          prediksi_depan=depan, _f=f))
    tab = pd.DataFrame(baris)

    terbaik = {}
    for metode in ["Moving Average", "SES"]:
        sub = tab[tab["metode"] == metode].dropna(subset=["mape_latih"])
        terbaik[metode] = sub.sort_values("mape_latih").iloc[0] if len(sub) else tab[tab["metode"] == metode].iloc[0]
    kandidat = pd.DataFrame([terbaik["Moving Average"], terbaik["SES"]])
    kandidat_ok = kandidat.dropna(subset=["mape_uji"])
    menang = (kandidat_ok if len(kandidat_ok) else kandidat).sort_values("mape_uji").iloc[0]
    return dict(tabel=tab.drop(columns="_f"), terbaik=terbaik, menang=menang, n=n, n_latih=n_latih,
                prediksi_rolling=menang["_f"], mulai_eval=mulai)


# ----------------------------------------------------------------------------
# 4. Titik restock
# ----------------------------------------------------------------------------
def hitung_restock(prediksi_minggu, rmse_minggu, stok, lead_time=7, z=1.65, periode_pesan=14):
    per_hari = prediksi_minggu / 7
    ss = z * rmse_minggu * math.sqrt(lead_time / 7)
    rop = per_hari * lead_time + ss
    target = per_hari * (lead_time + periode_pesan) + ss
    cukup_hari = (stok / per_hari) if per_hari > 0 else float("inf")
    hari_ke_rop = max(0.0, (stok - rop) / per_hari) if per_hari > 0 else float("inf")
    if stok <= rop:
        status = "MERAH"
    elif hari_ke_rop <= 7:
        status = "KUNING"
    else:
        status = "HIJAU"
    pesan = max(0, math.ceil(target - min(stok, rop)))
    return dict(per_hari=per_hari, stok_pengaman=ss, rop=rop, target=target, cukup_hari=cukup_hari,
                hari_ke_rop=hari_ke_rop, status=status, jumlah_pesan=pesan)


# ----------------------------------------------------------------------------
# 5. Kartu stok (opsional)
# ----------------------------------------------------------------------------
def baca_kartu_stok(file):
    """Ambil nama obat, satuan, dan stok akhir dari ekspor 'Kartu Stok' sistem apotek."""
    raw = pd.read_excel(file, header=None)
    nama = str(raw.iloc[7, 2]).strip(": ").strip().upper()
    satuan = str(raw.iloc[8, 3]).strip(": ").strip()
    d = pd.read_excel(file, header=11)
    ket = d["Catatan"].astype(str).str.strip()
    akhir = d[ket == "stok akhir"]
    if len(akhir):
        sisa = float(pd.to_numeric(akhir["Sisa"], errors="coerce").iloc[0])
    else:
        sisa = float(pd.to_numeric(d["Sisa"], errors="coerce").dropna().iloc[-1])
    return nama, satuan, sisa
