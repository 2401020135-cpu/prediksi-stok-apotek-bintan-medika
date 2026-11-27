"""
PREPROCESSING KARTU STOK - Apotek Bintan Medika
Proyek Penambangan Data: Prediksi Permintaan Obat -> titik restock (BAB VI)

Input : file Excel "AD - Kartu Stok - <OBAT> - ....xlsx" (satu file per obat)
Output: folder hasil_preprocessing_stok/
          - kartu_stok_bersih.csv       semua baris transaksi stok, sudah bersih (semua obat)
          - stok_harian.csv             stok akhir & stok terendah per hari per obat
          - data_stok_siap_olah.xlsx    Ringkasan, Stok_Mingguan, Pembelian, Opname, Validasi
          - laporan_cleaning_stok.txt   log hasil cleaning & validasi (lampirkan di laporan)

Cara pakai:
  pip install pandas openpyxl
  python preprocessing_kartu_stok.py  <folder_berisi_file_kartu_stok>

Tahapan:
  1. Cleaning     : buang baris judul/ringkasan, '-' jadi 0, tanggal teks jadi datetime,
                    buang kolom tak terpakai, buang baris opname yang tidak mengubah stok
  2. Validasi     : urutan waktu, No unik, kolom Sisa dihitung ulang, total sama dengan baris
                    'stok akhir', stok tidak boleh minus
  3. Klasifikasi  : Penjualan / VOID (pembatalan) / Opname (penyesuaian) / Pembelian (restock)
  4. Transformasi : stok harian dan mingguan (minggu Senin-Minggu, sama dengan data penjualan)
"""
import re
import sys
import glob
import os
from datetime import datetime

import numpy as np
import pandas as pd

POLA_FILE = "AD*Kartu*Stok*.xlsx"
BARIS_HEADER = 11                       # header tabel di baris ke-12 Excel
FOLDER_OUTPUT = "hasil_preprocessing_stok"
PERIODE_MULAI = pd.Timestamp("2025-10-01")
PERIODE_AKHIR = pd.Timestamp("2026-09-30")

BULAN_ID = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6, "jul": 7,
            "agu": 8, "agt": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12}
log_lines = []


def log(t=""):
    print(t)
    log_lines.append(str(t))


def parse_tanggal(teks):
    """'1 Okt 2025 09:39' -> Timestamp."""
    m = re.match(r"\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+(\d{1,2})[.:](\d{2})", str(teks))
    if not m:
        return pd.NaT
    d, b, y, h, mi = m.groups()
    bln = BULAN_ID.get(b.lower()[:3])
    return pd.Timestamp(int(y), bln, int(d), int(h), int(mi)) if bln else pd.NaT


def angka(seri):
    """'-' / spasi / kosong -> 0, sisanya jadi angka."""
    return pd.to_numeric(seri.replace({"-": 0, " ": 0}), errors="coerce").fillna(0)


def klasifikasi(catatan):
    c = str(catatan)
    if c.startswith("(VOID)"):
        return "VOID"
    if c.startswith("Penjualan"):
        return "Penjualan"
    if "opname" in c.lower():
        return "Opname"
    if c.startswith("Faktur Pembelian"):
        return "Pembelian"
    return "Lain"


def muat_satu(path):
    raw = pd.read_excel(path, header=None)
    nama = str(raw.iloc[7, 2]).strip(": ").strip()
    kode = str(raw.iloc[6, 2]).strip(": ").strip()
    satuan = str(raw.iloc[8, 3]).strip(": ").strip()
    d = pd.read_excel(path, header=BARIS_HEADER)

    ket = d["Catatan"].astype(str).str.strip()
    stok_awal = float(pd.to_numeric(d.loc[ket == "stok awal", "Sisa"]).iloc[0])
    baris_akhir = d.loc[ket == "stok akhir"].iloc[0]
    total_akhir = (float(angka(pd.Series([baris_akhir["Stok Masuk"]])).iloc[0]),
                   float(angka(pd.Series([baris_akhir["Stok Keluar"]])).iloc[0]),
                   float(pd.to_numeric(baris_akhir["Sisa"])))

    x = d[~ket.isin(["stok awal", "stok akhir"])].copy()
    x["obat"], x["kode_produk"], x["satuan"] = nama, kode, satuan
    x["masuk"] = angka(x["Stok Masuk"])
    x["keluar"] = angka(x["Stok Keluar"])
    x["sisa"] = pd.to_numeric(x["Sisa"], errors="coerce")
    x["tanggal_waktu"] = x["Tgl Transaksi"].map(parse_tanggal)
    x["tanggal"] = x["tanggal_waktu"].dt.normalize()
    x["jenis"] = x["Catatan"].map(klasifikasi)
    x["faktur"] = x["Catatan"].str.extract(r"((?:SIN|[A-Za-z0-9./-]+)-?\d[\w./-]*)", expand=False)
    pemb = x["Catatan"].str.extract(r"Faktur Pembelian dari (.+?) dengan kode faktur:\s*(\S+)")
    x["supplier"] = pemb[0].str.strip()
    x["kode_faktur"] = pemb[1]
    x.loc[x["jenis"].isin(["Penjualan", "VOID"]), "kode_faktur"] = x["Catatan"].str.extract(
        r"(SIN-\d{6}-\d+)", expand=False)
    return nama, kode, satuan, stok_awal, total_akhir, x


def bersihkan_dan_validasi(nama, satuan, stok_awal, total_akhir, x):
    log(f"\n--- {nama} ({satuan}) ---")
    log(f"  Baris transaksi mentah: {len(x):,}")
    # tanggal
    if x["tanggal_waktu"].isna().any():
        log(f"  PERINGATAN: {x['tanggal_waktu'].isna().sum()} tanggal gagal dibaca")
        x = x.dropna(subset=["tanggal_waktu"])
    # baris opname tanpa perubahan stok (masuk = keluar = 0)
    kosong = (x["jenis"] == "Opname") & (x["masuk"] == 0) & (x["keluar"] == 0)
    log(f"  Baris opname tanpa perubahan stok dibuang: {int(kosong.sum())}")
    x = x[~kosong].copy()
    # validasi
    urut = x["tanggal_waktu"].is_monotonic_increasing
    no_dobel = int(x["No"].duplicated().sum())
    hitung = stok_awal + (x["masuk"] - x["keluar"]).cumsum()
    sisa_salah = int((hitung.values != x["sisa"].values).sum())
    cocok_total = (round(x["masuk"].sum()), round(x["keluar"].sum()), float(x["sisa"].iloc[-1])) == \
                  tuple(round(v) for v in total_akhir)
    log(f"  Urut waktu: {'OK' if urut else 'TIDAK'} | No dobel: {no_dobel} | "
        f"Sisa dihitung ulang tidak cocok: {sisa_salah} | Total = baris 'stok akhir': {'OK' if cocok_total else 'TIDAK'}")
    log(f"  Stok minus: {int((x['sisa'] < 0).sum())} baris | Rentang: {x['tanggal'].min().date()} s/d {x['tanggal'].max().date()}")
    j = x.groupby("jenis").agg(baris=("No", "count"), masuk=("masuk", "sum"), keluar=("keluar", "sum"))
    log("  Ringkasan per jenis:\n" + "\n".join("    " + l for l in j.to_string().splitlines()))
    valid = dict(obat=nama, urut_waktu=urut, no_dobel=no_dobel, sisa_tidak_cocok=sisa_salah,
                 total_cocok=cocok_total, stok_minus=int((x["sisa"] < 0).sum()))
    return x, valid


def stok_harian(x, stok_awal):
    hari = pd.date_range(PERIODE_MULAI, PERIODE_AKHIR)
    akhir = x.groupby("tanggal")["sisa"].last().reindex(hari).ffill().fillna(stok_awal)
    terendah_baris = x.groupby("tanggal")["sisa"].min().reindex(hari)
    pembuka = akhir.shift(1).fillna(stok_awal)
    terendah = pd.concat([terendah_baris, pembuka], axis=1).min(axis=1)
    pemb = x[x["jenis"] == "Pembelian"].groupby("tanggal")["masuk"].sum().reindex(hari, fill_value=0)
    jual = x[x["jenis"] == "Penjualan"].groupby("tanggal")["keluar"].sum().reindex(hari, fill_value=0)
    void = x[x["jenis"] == "VOID"].groupby("tanggal")["masuk"].sum().reindex(hari, fill_value=0)
    opn = (x[x["jenis"] == "Opname"].assign(n=lambda t: t["masuk"] - t["keluar"])
           .groupby("tanggal")["n"].sum().reindex(hari, fill_value=0))
    h = pd.DataFrame({"stok_akhir": akhir, "stok_terendah": terendah,
                      "habis": terendah <= 0, "pembelian": pemb,
                      "penjualan_bersih": jual - void, "opname_net": opn})
    h.index.name = "tanggal"
    return h.reset_index()


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(folder, FOLDER_OUTPUT)
    os.makedirs(out, exist_ok=True)
    files = sorted(f for f in glob.glob(os.path.join(folder, POLA_FILE))
                   if not os.path.basename(f).startswith("~$"))
    if not files:
        sys.exit("Tidak ada file kartu stok di folder: " + folder)
    log(f"Preprocessing kartu stok {datetime.now():%Y-%m-%d %H:%M}\nFolder: {folder}")
    log(f"Jumlah file: {len(files)}")

    semua, harian, valid_list, ring = [], [], [], []
    for f in files:
        nama, kode, satuan, stok_awal, total_akhir, x = muat_satu(f)
        x, valid = bersihkan_dan_validasi(nama, satuan, stok_awal, total_akhir, x)
        h = stok_harian(x, stok_awal)
        h.insert(0, "obat", nama)
        semua.append(x)
        harian.append(h)
        valid_list.append(valid)
        pemb = x[x["jenis"] == "Pembelian"]
        selang = pemb["tanggal"].drop_duplicates().sort_values().diff().dt.days.dropna()
        ring.append({
            "obat": nama, "satuan": satuan, "stok_awal_1okt2025": stok_awal,
            "stok_akhir_30sep2026": float(x["sisa"].iloc[-1]),
            "jumlah_pembelian": len(pemb), "total_pembelian": pemb["masuk"].sum(),
            "rata2_per_pembelian": round(pemb["masuk"].mean(), 1),
            "selang_pembelian_rata2_hari": round(selang.mean(), 1) if len(selang) else np.nan,
            "penjualan_kotor": x.loc[x["jenis"] == "Penjualan", "keluar"].sum(),
            "pembatalan_void": x.loc[x["jenis"] == "VOID", "masuk"].sum(),
            "penjualan_bersih": x.loc[x["jenis"] == "Penjualan", "keluar"].sum() - x.loc[x["jenis"] == "VOID", "masuk"].sum(),
            "opname_masuk": x.loc[x["jenis"] == "Opname", "masuk"].sum(),
            "opname_keluar": x.loc[x["jenis"] == "Opname", "keluar"].sum(),
            "hari_stok_habis": int(h["habis"].sum()),
        })

    bersih = pd.concat(semua, ignore_index=True)
    hari_df = pd.concat(harian, ignore_index=True)

    # ---- mingguan (Senin-Minggu, sama dengan data penjualan) ----
    hari_df["minggu_mulai"] = hari_df["tanggal"] - pd.to_timedelta(hari_df["tanggal"].dt.weekday, unit="D")
    mg = (hari_df.groupby(["obat", "minggu_mulai"])
          .agg(penjualan_bersih=("penjualan_bersih", "sum"), pembelian=("pembelian", "sum"),
               opname_net=("opname_net", "sum"), stok_akhir_minggu=("stok_akhir", "last"),
               stok_terendah=("stok_terendah", "min"), hari_stok_habis=("habis", "sum"))
          .reset_index())
    mg["minggu_selesai"] = mg["minggu_mulai"] + pd.Timedelta(days=6)
    mg["minggu_penuh"] = (mg["minggu_mulai"] >= PERIODE_MULAI) & (mg["minggu_selesai"] <= PERIODE_AKHIR)
    mg["ada_stok_habis"] = mg["hari_stok_habis"] > 0

    # ---- daftar pembelian (restock) ----
    pb = bersih[bersih["jenis"] == "Pembelian"][["obat", "tanggal_waktu", "supplier", "kode_faktur", "masuk", "sisa"]].copy()
    pb = pb.rename(columns={"masuk": "jumlah_masuk", "sisa": "stok_setelah"}).sort_values(["obat", "tanggal_waktu"])
    pb["selang_hari_dari_pembelian_sebelumnya"] = pb.groupby("obat")["tanggal_waktu"].diff().dt.days

    # ---- opname ----
    op = bersih[bersih["jenis"] == "Opname"][["obat", "tanggal_waktu", "masuk", "keluar", "sisa"]].copy()
    op["perubahan_stok"] = op["masuk"] - op["keluar"]

    # ---- simpan ----
    kolom = ["obat", "kode_produk", "satuan", "No", "tanggal_waktu", "tanggal", "jenis", "kode_faktur",
             "supplier", "masuk", "keluar", "sisa"]
    bersih[kolom].to_csv(os.path.join(out, "kartu_stok_bersih.csv"), index=False)
    hari_df.drop(columns=["minggu_mulai"]).to_csv(os.path.join(out, "stok_harian.csv"), index=False)

    xlsx = os.path.join(out, "data_stok_siap_olah.xlsx")
    with pd.ExcelWriter(xlsx, engine="openpyxl", datetime_format="yyyy-mm-dd hh:mm") as w:
        pd.DataFrame(ring).to_excel(w, sheet_name="Ringkasan", index=False)
        mg.to_excel(w, sheet_name="Stok_Mingguan", index=False)
        pb.to_excel(w, sheet_name="Pembelian", index=False)
        op.to_excel(w, sheet_name="Opname", index=False)
        pd.DataFrame(valid_list).to_excel(w, sheet_name="Validasi", index=False)
        for ws in w.book.worksheets:
            ws.freeze_panes = "B2"
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = max(
                    10, min(34, max(len(str(c.value)) if c.value is not None else 0 for c in col) + 2))

    log("\n=== RINGKASAN ===")
    log(pd.DataFrame(ring).set_index("obat").T.to_string())
    log(f"\nHasil di: {out}")
    with open(os.path.join(out, "laporan_cleaning_stok.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))


if __name__ == "__main__":
    main()
