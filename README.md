# Dashboard RKP — Target vs Realisasi Biaya

Dashboard interaktif untuk memantau anggaran (Target Biaya) vs realisasi, lengkap
dengan analisa otomatis (misalnya biaya yang melebihi target) berdasarkan sheet
**"Rekap RKP"** di file Master RKP.

## Fitur
- Upload file Excel langsung dari browser (tidak perlu edit kode tiap update data)
- Filter interaktif: Proyek, Tahun, Kegiatan, Bulan/Cawu
- Kartu ringkasan: Total Target, Total Realisasi, Sisa Anggaran, % Realisasi
- Analisa otomatis (teks): kegiatan yang melebihi target, alokasi anggaran terbesar, dll
- Grafik: Target vs Realisasi per Kegiatan, komposisi per Proyek, top Sub Kegiatan
- Tabel detail dengan highlight otomatis (merah) untuk item yang melebihi target

## Cara pakai online (gratis, bisa dibagikan ke tim)

**1. Push folder ini ke GitHub**
```bash
cd rkp-dashboard
git init
git add .
git commit -m "Dashboard RKP"
git branch -M main
git remote add origin https://github.com/USERNAME/rkp-dashboard.git
git push -u origin main
```
(Buat dulu repo kosong di GitHub, lalu ganti USERNAME/rkp-dashboard sesuai punya Anda)

**2. Deploy ke Streamlit Community Cloud (gratis)**
1. Buka https://share.streamlit.io
2. Login dengan akun GitHub
3. Klik "New app" → pilih repo `rkp-dashboard` → branch `main` → file `app.py`
4. Klik "Deploy"
5. Dalam 1-2 menit, dashboard akan online dengan URL publik (mis. `https://rkp-dashboard.streamlit.app`) yang bisa dibagikan ke tim

**3. Update data**
Setiap kali ada data baru, tinggal buka dashboard online lalu upload ulang file Excel
terbaru lewat tombol di sidebar — tidak perlu deploy ulang.

## Cara pakai lokal (untuk uji coba)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Lalu buka http://localhost:8501 di browser.

## Catatan penting
Kolom **"Realisasi Biaya"** di file yang Anda kirim saat ini masih 0 (belum diisi).
Dashboard sudah siap menampilkan analisa "biaya melebihi target" secara otomatis —
begitu kolom Realisasi Biaya diisi di Excel dan file di-upload ulang ke dashboard,
insight dan highlight otomatis akan langsung muncul, tanpa perlu ubah kode.
