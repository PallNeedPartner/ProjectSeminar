# Puskesmas Digital — UI Terpadu

Project Flask dengan tampilan seluruh halaman mengikuti dashboard referensi: header horizontal, palet biru kesehatan, panel putih, aksen hijau, dan font Plus Jakarta Sans.

## Menjalankan di Windows 11
1. Ekstrak ZIP.
2. Buka folder `puskesmas_digital` di VS Code.
3. Buat virtual environment: `py -m venv venv`
4. Aktifkan: `venv\Scripts\activate`
5. Instal: `pip install -r requirements.txt`
6. Salin `.env.example` menjadi `.env`.
7. Isi `SECRET_KEY` dan `GEMINI_API_KEY`. API key dapat dibuat di https://aistudio.google.com/apikey.
8. Jalankan: `py app.py`
9. Buka http://127.0.0.1:5000

## Akun demo
- Admin: admin@puskesmas.test / admin123
- Dokter: dokter@puskesmas.test / dokter123
- Tenaga medis: medis@puskesmas.test / medis123
- Pasien: pasien@puskesmas.test / pasien123

Database SQLite dibuat otomatis saat aplikasi pertama kali dijalankan.

## Catatan
Tanpa `GEMINI_API_KEY`, halaman AI berjalan dalam mode demo. Dengan API key, backend mencoba menggunakan Gemini API. Gunakan hanya untuk edukasi umum; jangan kirim identitas atau rekam medis pribadi ke layanan AI. Data imunisasi bawaan adalah data contoh dan harus diverifikasi oleh petugas kesehatan.

Ini prototipe pengembangan, bukan sistem produksi. Sebelum dipakai di fasilitas kesehatan nyata, perlu penguatan autentikasi, otorisasi per-record, CSRF, audit log, backup, HTTPS, dan kepatuhan perlindungan data kesehatan.
