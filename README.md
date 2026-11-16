# Crop tulisan tangan IAM

Program mengambil potongan asli **512 x 512 piksel**, grayscale 8-bit (mode `L`).
Tidak ada resize, binarisasi, penambahan derau, atau perubahan file dataset.
Potongan berisi sebagian kata/baris, bukan seluruh paragraf yang diperkecil.

## Jalankan

```powershell
python -m pip install -r requirements.txt
python crop_tulisan.py
```

Input default: `dataset`; konfigurasi: `crop_config.csv`; output: `hasil_crop`.
Path default mengikuti lokasi skrip sehingga bisa dijalankan dari folder lain.
Jika folder output sudah ada, program berhenti agar hasil lama tidak tertimpa.
Untuk percobaan lain:

```powershell
python crop_tulisan.py --output hasil_crop_baru
```

## Pemilihan area

Koordinat awal dipilih secara manual melalui pemeriksaan visual tiga halaman
yang tersedia, pada area tulisan tangan di bawah teks cetak. Program tidak
melakukan OCR atau deteksi tulisan otomatis. Ubah `x` dan `y` di
`crop_config.csv` untuk memilih area lain; ukuran wajib 512 x 512.
Semua koordinat memakai piksel gambar asli: titik (0, 0) di kiri atas,
x bertambah ke kanan, y bertambah ke bawah. Sisi kanan dan bawah eksklusif:
crop mencakup x sampai x+511, dan y sampai y+511.

## Keluaran dan bukti

- PNG pada `hasil_crop`: citra bersih untuk eksperimen.
- `hasil_crop/metadata_crop.csv`: ID halaman, nama sumber, koordinat, ukuran,
  mode, hash SHA-256 sumber/hasil, dan path bukti. Hash membantu memeriksa
  apakah file yang digunakan masih identik.
- `hasil_crop/bukti`: salinan halaman dengan kotak merah di posisi potongan.
  Gambar bukti diperkecil untuk dilihat; PNG crop tetap berukuran asli.

Ketiga halaman diproses agar semua input yang diberikan memiliki hasil.
Rencana CP1 hanya membutuhkan dua crop pilot; pilih dua dari hasil ini bersama
tim. Crop pilot harus dipisahkan dari crop pengujian utama. `writer_id` sengaja
kosong karena metadata identitas penulis tidak tersedia di folder input;
jangan menganggap halaman berbeda selalu berasal dari penulis berbeda.

## Generator derau CP2

```powershell
python generator_derau.py --seed 42
```

Satu file `generator_derau.py` membaca PNG langsung di `hasil_crop` (subfolder
bukti dan JPG preview tidak ikut). Setiap input wajib grayscale 8-bit 512 x 512.
Hasil berada di folder `citra_berderau/25_75`, `citra_berderau/50_50`, dan
`citra_berderau/75_25`; nama folder menyatakan rasio **salt:pepper**.
Masing-masing menyimpan citra berderau, mask injeksi, dan mask perubahan aktual.
Pada mask, putih 255 berarti ditandai dan hitam 0 berarti tidak ditandai.

Sebanyak 30% posisi dipilih tanpa pengulangan. Untuk satu crop dan seed,
ketiga rasio memakai posisi dan urutan acak identik. Salt mengisi awalan urutan,
pepper mengisi sisanya, sehingga himpunan salt 25% berada di dalam himpunan
salt 50% dan 75%. Seed per crop diturunkan dari seed pengguna dan nama file;
hasil tidak bergantung pada urutan atau jumlah file lain di folder input.
Gunakan input, nama file, seed, dan versi NumPy yang sama untuk mengulang hasil.

Jumlah posisi dan salt dibulatkan ke integer terdekat (setengah naik).
Pada 512 x 512, target 30% menjadi 78.643 posisi, sekitar 29,9999%.
Proporsi salt dan pepper juga mendekati target karena pembulatan piksel.
`metadata_derau.csv` mencatat seed, versi NumPy, hash sumber, jumlah injeksi,
jumlah salt/pepper yang ditugaskan, serta jumlah piksel yang benar-benar berubah.
Piksel asli 255 yang diberi salt atau asli 0 yang diberi pepper tetap masuk
mask injeksi, tetapi tidak masuk mask perubahan aktual.

Folder output yang sudah ada tidak ditimpa. Untuk seed/percobaan lain:

```powershell
python generator_derau.py --seed 43 --output citra_berderau_seed43
```
