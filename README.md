# Analisis Tata Guna Lahan, Meteorologi & Mikroalga — Embung Wisdom Park & Langensari

Aplikasi Streamlit untuk menghubungkan data kualitas air & mikroalga (dari
laporan sampling lapangan) dengan tata guna lahan dan faktor meteorologis di
sekitar Embung Wisdom Park (UGM) dan Embung Langensari, Yogyakarta.

## Isi Repo
- `app.py` — aplikasi utama (single-file, siap deploy)
- `requirements.txt` — dependensi Python

## Menjalankan Secara Lokal
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy ke Streamlit Community Cloud
1. Buat repository baru di GitHub, unggah `app.py` dan `requirements.txt`.
2. Buka https://share.streamlit.io/ (Streamlit Community Cloud), login dengan akun GitHub.
3. Klik **New app** → pilih repository, branch, dan file utama `app.py`.
4. Klik **Deploy**. Aplikasi akan otomatis membangun environment dari `requirements.txt`.

## Catatan Data Penting
- Data **kualitas air** (suhu air, pH, DO, TDS) dan **hasil identifikasi mikroalga**
  bersumber langsung dari laporan lapangan (sampling 16 Januari 2026) dan sudah
  di-hardcode di dalam `app.py`.
- Data **tata guna lahan** dan **meteorologi udara** (suhu udara, kelembaban,
  curah hujan, angin) **tidak tersedia** pada laporan sumber. Aplikasi
  menyediakan tabel interaktif (`st.data_editor`) dengan nilai default
  indikatif yang WAJIB divalidasi/diganti dengan data primer, misalnya:
  - Tata guna lahan: hasil klasifikasi citra Sentinel-2 via Google Earth Engine,
    atau digitasi manual dari peta RBI/citra resolusi tinggi.
  - Meteorologi: data harian dari stasiun BMKG terdekat (Yogyakarta) pada
    tanggal sampling.
- Kedua modul tersebut juga mendukung unggah file CSV agar Anda dapat
  memasukkan data hasil olahan sendiri tanpa mengubah kode.

## Struktur Halaman
1. **Beranda** — ringkasan aplikasi
2. **Data Kualitas Air & Mikroalga** — tabel & grafik dari laporan sumber
3. **Tata Guna Lahan** — input/edit komposisi lahan per lokasi
4. **Faktor Meteorologis** — input/edit data iklim mikro per lokasi
5. **Analisis Keterkaitan** — korelasi parameter air, matriks hipotesis
   keterkaitan lahan-mikroalga, radar perbandingan lokasi
6. **Peta Lokasi Sampling** — visualisasi titik sampling (dikonversi dari DMS)
7. **Ringkasan & Unduh Data** — narasi draf otomatis + unduhan Excel/TXT
