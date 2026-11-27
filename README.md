# Prediksi Jumlah Permintaan Obat Menggunakan Metode Moving Average dan Single Exponential Smoothing untuk Optimasi Persediaan Apotek Bintan Medika

Proyek Akhir Mata Kuliah **Penambangan Data (INF11121)** — Program Studi Teknik Informatika, Fakultas Teknik dan Teknologi Kemaritiman, Universitas Maritim Raja Ali Haji (2026).

## Anggota Tim
- **Fitri Arfiana** (`2401020135`) – Ketua, Analisis Titik Restock, Antarmuka Dashboard, Penyusunan Laporan Akhir
- **Siti Melka Rehngenana** (`2401020132`) – Pengumpulan Data, Exploratory Data Analysis (EDA), Pemodelan Orange & Evaluasi MA/SES
- **Atsilah Halimatus Sa'diyah** (`2401020142`) – Pre-processing Data Penjualan (Integration, Cleaning, Selection, Transformation)
- **Munfarida** (`2401020166`) – Pre-processing Data Kartu Stok & Validasi Silang

## Ringkasan Proyek
- **Periode Pengamatan:** 1 Oktober 2025 – 30 September 2026 (365 hari / 110.573 baris transaksi mentah -> 51 minggu penuh)
- **Objek Penelitian:** 5 obat dengan frekuensi hari terjual tertinggi (`ANDALAN`, `VICEE`, `KADITIC`, `MEFINAL`, `DEXAHARSEN 0,75MG`)
- **Metode Peramalan:** *Moving Average* ($k = 2, 3, 4$) dan *Single Exponential Smoothing* ($\alpha = 0,1 \dots 0,9$) yang dievaluasi menggunakan MAPE, MAE, dan RMSE
- **Implementasi:** Aplikasi web interaktif **Dashboard Restock Apotek Bintan Medika** berbasis Streamlit dengan konsep *rolling forecast*

## Struktur Repositori
```text
├── data_contoh/         # Dataset sampel 5 obat untuk uji coba aplikasi
├── preprocessing/       # Skrip Python, log cleaning, dan data bersih mingguan/stok
├── modeling_orange/     # Alur kerja Orange Data Mining (.ows) dan perhitungan Excel MA & SES
├── restock_excel/       # Perhitungan titik restock (ROP) dan grafik perpotongan stok
├── dashboard/           # Kode sumber aplikasi web Streamlit (app.py & logika.py)
└── laporan/             # Dokumen laporan akhir lengkap (PDF)
```

## Cara Menjalankan Aplikasi Dashboard
1. Instal seluruh pustaka yang diperlukan:
   ```bash
   pip install -r requirements.txt
   ```
2. Jalankan aplikasi Streamlit dari folder utama repositori:
   ```bash
   streamlit run dashboard/app.py
   ```
3. Pada halaman **Input Data**, klik tombol **Pakai data contoh** lalu klik **Proses data dan hitung prediksi** untuk melihat hasil peramalan dan status *restock*.