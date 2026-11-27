"""
PREPROCESSING DATA TRANSAKSI - Apotek Bintan Medika
Proyek Penambangan Data: Prediksi Permintaan Obat (Moving Average & SES)

Tahapan yang dikerjakan script ini (sesuai tahapan KDD):
  1. Data Cleaning        -> tanggal, nama produk, satuan, validasi
  2. Data Integration     -> gabung semua file Excel per periode + cek dobel & hari bolong
  3. Data Selection       -> pakai sheet "Stok Terjual", buang kolom tak relevan,
                             filter non-obat, tandai pembelian grosir, pilih obat
  4. Data Transformation  -> agregasi harian jadi mingguan (isi minggu kosong dengan 0)

Cara pakai:
  1. Taruh semua file Excel (Transaksi_YYYYMMDD_YYYYMMDD.xlsx) dalam satu folder.
  2. Install library:   pip install pandas openpyxl
  3. Jalankan:          python preprocessing_penambangan_data.py  <folder_input>
     (kalau folder_input dikosongin, script baca folder tempat script ini berada)
  4. Hasil ada di folder  hasil_preprocessing/
"""

import re
import sys
import glob
import os
from datetime import datetime

import pandas as pd

# =============================================================================
# PENGATURAN (ubah di sini kalau perlu)
# =============================================================================
POLA_FILE = "Data Penjualan/Transaksi_*.xlsx"      # pola nama file input
NAMA_SHEET = "Stok Terjual"         # sheet yang dipakai (format datar, 1 baris = 1 item)
BARIS_HEADER = 9                    # header ada di baris ke-10 Excel (index 9)
FOLDER_OUTPUT = "hasil_preprocessing"

# Kolom yang dipertahankan (sisanya dibuang: Barcode, Kategori 1, ED, Kode Batch,
# Harga Pokok, Pelanggan, Kanal Penjualan -> kosong / tidak bisa dipercaya)
KOLOM_DIPAKAI = ["Tanggal Transaksi", "Kode Struk", "Kode Produk",
                 "Nama Produk", "Jumlah", "Satuan", "Harga Jual"]

# Koreksi typo nama produk (tulis dalam HURUF BESAR): {salah: benar}
KOREKSI_NAMA = {
    "IBU PROFEN 400 BALATIF": "IBUPROFEN 400 BALATIF",
}

# Kata kunci produk NON-OBAT yang difilter. Cek file
# "produk_non_obat_terfilter.csv" untuk memastikan nggak ada obat yang ikut kebuang.
KATA_KUNCI_NON_OBAT = [
    "AICE", "TISU", "BOTOL", "PARFUM", "KASSA", "HANDSCOON", "EASY TOUCH",
    "NESCO", "POPOK", "SUSU", "MASKER", "HANSAPLAST", "FRESHCARE",
]

# Pembelian grosir: baris ditandai kalau Jumlah >= GROSIR_MIN_ABS
# DAN >= GROSIR_KALI_MEDIAN x median jumlah per transaksi produk itu.
GROSIR_MIN_ABS = 100
GROSIR_KALI_MEDIAN = 10

# Pemilihan obat:
# - Isi PRODUK_TERPILIH manual (huruf besar) kalau tim sudah memutuskan,
# - atau kosongkan [] supaya script memilih otomatis TOP_N obat dengan
#   jumlah hari terjual terbanyak (bukan sekadar total jumlah).
PRODUK_TERPILIH = []
TOP_N = 5

# Minggu di awal / akhir periode yang tidak penuh 7 hari dibuang dari tabel
# mingguan "siap pakai" (tetap ada di file long dengan penanda).
BUANG_MINGGU_TIDAK_PENUH = True

# =============================================================================
BULAN_ID = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
            "jul": 7, "agu": 8, "agt": 8, "sep": 9, "okt": 10, "nov": 11,
            "des": 12}

log_lines = []


def log(teks=""):
    print(teks)
    log_lines.append(str(teks))


def parse_tanggal(teks):
    """'1 Okt 2025 pukul 07.13' -> Timestamp. Gagal baca -> NaT."""
    m = re.match(r"\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})(?:\s+pukul\s+(\d{1,2})[.:](\d{2}))?",
                 str(teks))
    if not m:
        return pd.NaT
    hari, bln, thn, jam, menit = m.groups()
    bulan = BULAN_ID.get(bln.lower()[:3])
    if bulan is None:
        return pd.NaT
    return pd.Timestamp(int(thn), bulan, int(hari), int(jam or 0), int(menit or 0))


# -----------------------------------------------------------------------------
# 1 & 2. LOAD + INTEGRATION
# -----------------------------------------------------------------------------
def muat_semua_file(folder):
    pola = os.path.join(folder, POLA_FILE)
    daftar = sorted(glob.glob(pola))
    daftar = [f for f in daftar if not os.path.basename(f).startswith("~$")]
    if not daftar:
        sys.exit(f"Tidak ada file yang cocok dengan pola {pola}")

    log("=== TAHAP 2: DATA INTEGRATION ===")
    frames = []
    for f in daftar:
        df = pd.read_excel(f, sheet_name=NAMA_SHEET, header=BARIS_HEADER)
        df["file_sumber"] = os.path.basename(f)
        log(f"  {os.path.basename(f)}: {len(df):,} baris")
        frames.append(df)

    gabung = pd.concat(frames, ignore_index=True)
    log(f"  Total setelah digabung: {len(gabung):,} baris dari {len(daftar)} file")

    kurang = [k for k in KOLOM_DIPAKAI if k not in gabung.columns]
    if kurang:
        sys.exit(f"Kolom ini tidak ditemukan di file: {kurang}")
    return gabung


# -----------------------------------------------------------------------------
# 1. CLEANING
# -----------------------------------------------------------------------------
def bersihkan(df):
    log("\n=== TAHAP 1: DATA CLEANING ===")
    awal = len(df)

    # buang baris kosong / baris footer (tanpa nama produk atau kode struk)
    df = df.dropna(subset=["Nama Produk", "Kode Struk"]).copy()
    log(f"  Baris kosong dibuang: {awal - len(df)}")

    # tanggal: teks Indonesia -> datetime
    df["tanggal_waktu"] = df["Tanggal Transaksi"].map(parse_tanggal)
    gagal = df["tanggal_waktu"].isna().sum()
    if gagal:
        log(f"  PERINGATAN: {gagal} tanggal gagal dibaca, contoh: "
            f"{df.loc[df['tanggal_waktu'].isna(), 'Tanggal Transaksi'].head(3).tolist()}")
        df = df.dropna(subset=["tanggal_waktu"])
    df["tanggal"] = df["tanggal_waktu"].dt.normalize()
    log("  Tanggal teks -> datetime: OK")

    # nama produk: strip spasi, rapikan spasi ganda, huruf besar semua
    asli = df["Nama Produk"].astype(str)
    df["Nama Produk"] = (asli.str.strip().str.replace(r"\s+", " ", regex=True).str.upper())
    log(f"  Nama produk dengan spasi nyangkut diperbaiki: {(asli != asli.str.strip()).sum()} baris")

    # koreksi typo
    n_typo = df["Nama Produk"].isin(KOREKSI_NAMA).sum()
    df["Nama Produk"] = df["Nama Produk"].replace(KOREKSI_NAMA)
    log(f"  Koreksi typo nama: {n_typo} baris")

    # satuan: samakan huruf (KOTAK/Kotak -> Kotak)
    df["Satuan"] = df["Satuan"].astype(str).str.strip().str.title()

    # satu nama dengan >1 kode produk -> beda barang, bedakan lewat satuan
    kode_per_nama = df.groupby("Nama Produk")["Kode Produk"].nunique()
    ganda = kode_per_nama[kode_per_nama > 1].index.tolist()
    if ganda:
        m = df["Nama Produk"].isin(ganda)
        df.loc[m, "Nama Produk"] = df.loc[m, "Nama Produk"] + " (" + df.loc[m, "Satuan"] + ")"
        log(f"  Nama sama tapi kode beda, dibedakan dengan satuan: {ganda}")

    # validasi jumlah
    df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce")
    tidak_valid = (df["Jumlah"].isna() | (df["Jumlah"] <= 0)).sum()
    if tidak_valid:
        log(f"  Jumlah kosong/<=0 dibuang: {tidak_valid} baris")
        df = df[df["Jumlah"] > 0]
    else:
        log("  Validasi Jumlah (semua > 0): OK")
    return df


def integrasi_cek(df):
    """Cek dobel antar file & hari yang bolong."""
    kunci = ["Kode Struk", "Kode Produk", "Jumlah", "Harga Jual", "tanggal_waktu"]
    n_dobel = df.duplicated(subset=kunci).sum()
    df = df.drop_duplicates(subset=kunci).copy()
    log(f"  Baris dobel (struk+produk+jumlah+harga+waktu sama) dibuang: {n_dobel}")

    mulai, akhir = df["tanggal"].min(), df["tanggal"].max()
    semua_hari = pd.date_range(mulai, akhir, freq="D")
    hari_ada = set(df["tanggal"].unique())
    bolong = [d.date() for d in semua_hari if d not in hari_ada]
    log(f"  Rentang data: {mulai.date()} s/d {akhir.date()} ({len(semua_hari)} hari)")
    if bolong:
        log(f"  PERINGATAN: {len(bolong)} hari tidak ada transaksi sama sekali "
            f"(file ada yang kelewat?): {bolong[:10]}{' ...' if len(bolong) > 10 else ''}")
    else:
        log("  Tidak ada hari bolong: OK")
    return df, mulai, akhir


# -----------------------------------------------------------------------------
# 3. SELECTION
# -----------------------------------------------------------------------------
def seleksi(df, folder_out):
    log("\n=== TAHAP 3: DATA SELECTION ===")
    df = df[KOLOM_DIPAKAI[1:] + ["tanggal_waktu", "tanggal"]].copy()
    log(f"  Kolom dipakai: {KOLOM_DIPAKAI}")

    # filter non-obat
    pola = "|".join(re.escape(k) for k in KATA_KUNCI_NON_OBAT)
    non_obat = df["Nama Produk"].str.contains(pola, regex=True)
    ringkas_non = (df[non_obat].groupby("Nama Produk")["Jumlah"]
                   .agg(["count", "sum"]).rename(columns={"count": "baris", "sum": "total_jumlah"})
                   .sort_values("baris", ascending=False))
    ringkas_non.to_csv(os.path.join(folder_out, "produk_non_obat_terfilter.csv"))
    log(f"  Non-obat difilter: {non_obat.sum():,} baris dari {ringkas_non.shape[0]} produk "
        f"(daftar lengkap: produk_non_obat_terfilter.csv, cek manual ya)")
    df = df[~non_obat].copy()

    # tandai pembelian grosir
    med = df.groupby("Nama Produk")["Jumlah"].transform("median")
    df["grosir"] = (df["Jumlah"] >= GROSIR_MIN_ABS) & (df["Jumlah"] >= GROSIR_KALI_MEDIAN * med)
    log(f"  Baris ditandai pembelian grosir: {df['grosir'].sum()} "
        f"(Jumlah >= {GROSIR_MIN_ABS} dan >= {GROSIR_KALI_MEDIAN}x median produk)")
    if df["grosir"].any():
        top = (df[df["grosir"]].groupby("tanggal")["Jumlah"].sum()
               .sort_values(ascending=False).head(3))
        log("  Hari dengan grosir terbesar: " +
            ", ".join(f"{t.date()} ({int(v):,} unit)" for t, v in top.items()))

    # ringkasan per produk -> bahan memilih obat
    total_hari = df["tanggal"].nunique()
    ring = df.groupby("Nama Produk").agg(
        satuan=("Satuan", "first"),
        total_jumlah=("Jumlah", "sum"),
        jumlah_transaksi=("Kode Struk", "count"),
        hari_terjual=("tanggal", "nunique"),
        median_per_transaksi=("Jumlah", "median"),
        baris_grosir=("grosir", "sum"),
    )
    ring["persen_hari_terjual"] = (ring["hari_terjual"] / total_hari * 100).round(1)
    ring = ring.sort_values(["hari_terjual", "total_jumlah"], ascending=False)
    ring.to_csv(os.path.join(folder_out, "ringkasan_produk.csv"))
    log(f"  Total produk obat: {len(ring):,}; muncul >= 80% hari: "
        f"{(ring['persen_hari_terjual'] >= 80).sum()}; muncul < 10% hari: "
        f"{(ring['persen_hari_terjual'] < 10).sum()}  (mayoritas = permintaan putus-putus)")

    # pilih obat
    if PRODUK_TERPILIH:
        terpilih = [p.upper() for p in PRODUK_TERPILIH]
        hilang = [p for p in terpilih if p not in ring.index]
        if hilang:
            sys.exit(f"Produk tidak ditemukan: {hilang}. Cek ejaan di ringkasan_produk.csv")
        cara = "manual"
    else:
        terpilih = ring.head(TOP_N).index.tolist()
        cara = f"otomatis (top {TOP_N} berdasarkan hari terjual)"
    log(f"  Obat terpilih ({cara}):")
    for p in terpilih:
        r = ring.loc[p]
        log(f"    - {p}: {int(r['hari_terjual'])} hari terjual, total {int(r['total_jumlah']):,} {r['satuan']}")
    return df, ring, terpilih


# -----------------------------------------------------------------------------
# 4. TRANSFORMATION (harian -> mingguan)
# -----------------------------------------------------------------------------
def transformasi(df, terpilih, mulai, akhir):
    log("\n=== TAHAP 4: DATA TRANSFORMATION ===")
    d = df[df["Nama Produk"].isin(terpilih)].copy()

    # minggu = Senin s/d Minggu, diberi label tanggal Senin-nya
    d["minggu_mulai"] = d["tanggal"] - pd.to_timedelta(d["tanggal"].dt.weekday, unit="D")
    d["jumlah_non_grosir"] = d["Jumlah"].where(~d["grosir"], 0)

    mingguan = (d.groupby(["Nama Produk", "minggu_mulai"])
                 .agg(jumlah=("Jumlah", "sum"), jumlah_tanpa_grosir=("jumlah_non_grosir", "sum"))
                 .reset_index())

    # isi minggu kosong dengan 0 untuk tiap produk
    semua_minggu = pd.date_range(mingguan["minggu_mulai"].min(), mingguan["minggu_mulai"].max(), freq="7D")
    kerangka = pd.MultiIndex.from_product([terpilih, semua_minggu], names=["Nama Produk", "minggu_mulai"])
    mingguan = (mingguan.set_index(["Nama Produk", "minggu_mulai"]).reindex(kerangka, fill_value=0)
                .reset_index())

    mingguan["minggu_selesai"] = mingguan["minggu_mulai"] + pd.Timedelta(days=6)
    mingguan["minggu_penuh"] = (mingguan["minggu_mulai"] >= mulai) & (mingguan["minggu_selesai"] <= akhir)
    n_tidak_penuh = (~mingguan.drop_duplicates("minggu_mulai")["minggu_penuh"]).sum()
    log(f"  Jumlah minggu: {len(semua_minggu)} (tidak penuh 7 hari: {n_tidak_penuh}, "
        f"{'dibuang dari tabel siap pakai' if BUANG_MINGGU_TIDAK_PENUH else 'tetap dipakai'})")

    siap = mingguan[mingguan["minggu_penuh"]] if BUANG_MINGGU_TIDAK_PENUH else mingguan
    wide = siap.pivot(index="minggu_mulai", columns="Nama Produk", values="jumlah")[terpilih]
    wide_ng = siap.pivot(index="minggu_mulai", columns="Nama Produk", values="jumlah_tanpa_grosir")[terpilih]
    log(f"  Tabel mingguan siap pakai: {wide.shape[0]} minggu x {wide.shape[1]} obat")
    return mingguan, wide, wide_ng


# -----------------------------------------------------------------------------
def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    folder_out = os.path.join(folder, FOLDER_OUTPUT)
    os.makedirs(folder_out, exist_ok=True)
    log(f"Preprocessing dijalankan {datetime.now():%Y-%m-%d %H:%M}\nFolder input: {folder}\n")

    df = muat_semua_file(folder)
    df = bersihkan(df)
    df, mulai, akhir = integrasi_cek(df)
    df, ring, terpilih = seleksi(df, folder_out)
    mingguan, wide, wide_ng = transformasi(df, terpilih, mulai, akhir)

    # simpan hasil
    df.drop(columns=["tanggal_waktu"]).to_csv(
        os.path.join(folder_out, "data_bersih_harian.csv"), index=False)
    mingguan.to_csv(os.path.join(folder_out, "data_mingguan_long.csv"), index=False)

    xlsx = os.path.join(folder_out, "data_mingguan_siap_olah.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl", datetime_format="yyyy-mm-dd") as w:
        wide.to_excel(w, sheet_name="Mingguan")
        wide_ng.to_excel(w, sheet_name="Mingguan_tanpa_grosir")
        ring.to_excel(w, sheet_name="Ringkasan_produk")
        for ws in w.book.worksheets:
            ws.freeze_panes = "B2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = max(
                    12, min(32, max(len(str(c.value)) if c.value is not None else 0 for c in col) + 2))

    log("\n=== SELESAI === File hasil di: " + folder_out)
    for nama in ["data_bersih_harian.csv", "data_mingguan_long.csv", "data_mingguan_siap_olah.xlsx",
                 "ringkasan_produk.csv", "produk_non_obat_terfilter.csv", "laporan_preprocessing.txt"]:
        log(f"  - {nama}")
    with open(os.path.join(folder_out, "laporan_preprocessing.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))


if __name__ == "__main__":
    main()