# Evaluasi C2: MSE area berubah dan PSNR global

PIC: Yahya. Target C2-YH adalah implementasi metrik yang lolos contoh hitung manual.
Program menilai **satu pasangan citra asli, noisy, dan hasil satu filter**. Program
membaca gambar dan mencetak angka di terminal, tanpa mengubah atau membuat file.
Tidak menjalankan generator/filter, audit batch, integrasi, atau membuat CSV final tim.

## Persiapan dan tes

Jalankan dari root repositori dengan Python yang memiliki dependensi repo:

```powershell
python -m pip install -r requirements.txt
python -B -m unittest evaluasi.test_evaluasi
```

Ada 10 tes evaluator, mencakup hitung manual, overflow uint8, pemulihan sempurna,
mask kosong, dampak pada piksel yang awalnya benar, ukuran/mode/dtype salah, serta
pembacaan tiga PNG tanpa menulis file keluaran.

## Menilai satu hasil nyata

Contoh berikut memakai crop `e01-014`, seed 42, rasio salt:pepper 50:50, metode PSMF.
Path ini dicocokkan dengan metadata generator yang tersedia di repo.

```powershell
python -B evaluasi/evaluasi.py --clean hasil_crop/e01-014_x700_y1050_512x512.png --noisy citra_berderau/50_50/e01-014_x700_y1050_512x512_seed42_derau.png --restored hasil_psmf/50_50/e01-014_x700_y1050_512x512_seed42_derau.png
```

Hasil pemeriksaan pada snapshot `bbe2a24`:

```text
jumlah_piksel_berubah: 78643
mse_berubah_input: 30173.3072364991
mse_global_input: 9051.9691505432
psnr_global_input_db: 8.5633729567
mse_berubah_hasil: 95.602838142
mse_global_hasil: 36.5406227112
psnr_global_hasil_db: 32.5030441671
metric_note:
```

Untuk SMF, ganti folder `hasil_psmf` dengan `hasil_deteksi_smf`; untuk IPSMF ganti
dengan `hasil_ipsmf`. Gunakan nama file dan subfolder rasio yang sama. Jangan mengisi
`--restored` dengan gambar mask. Pemanggil bertanggung jawab memilih crop, rasio,
seed, dan hasil filter yang berpasangan; ukuran sama saja tidak membuktikan pasangan benar.

## Rumus dan contoh manual

`I` adalah citra bersih, `N` citra noisy, `R` hasil filter. Ketiganya harus grayscale
8-bit (mode L/array uint8), tidak kosong, dan berukuran sama.

```text
M = N != I
MSE area berubah = mean((R[M] - I[M])^2)
MSE global       = mean((R - I)^2)
PSNR global      = 10 log10(255^2 / MSE global)
```

Mask `M` ditetapkan dari noisy dan citra bersih, sama untuk ketiga metode pada input
yang sama. Mask deteksi filter dan mask injeksi tidak dipakai untuk menilai area berubah.
Selisih dihitung dalam float64 sebelum dikuadratkan. Skor input memakai rumus sama
dengan mengganti `R` menjadi `N`, sebagai pembanding kondisi sebelum pemulihan.

```text
clean       noisy       restored
10 20       255 20      12 20
30 40        30  0      30 36
```

Mask memilih kiri atas dan kanan bawah. MSE berubah hasil = (4+16)/2 = **10**.
MSE global hasil = (4+0+0+16)/4 = **5**.
PSNR global hasil = 10 log10(65025/5) = **41.1411035653 dB**.
Angka ini diperiksa otomatis oleh tes, bukan hasil eksperimen dataset.

MSE lebih kecil lebih baik; PSNR lebih besar lebih baik. Mask kosong menghasilkan
MSE berubah `None` pada fungsi/`NA` di terminal dan `metric_note=empty_changed_mask`.
MSE global tetap dihitung. MSE global nol menghasilkan PSNR `inf`.

Fungsi `evaluate_pair(clean, noisy, restored)` dapat dipanggil oleh program integrasi
nanti. Nama kolom metrik mengikuti draft C1; penetapan skema CSV final, run_id,
agregasi dan audit algoritme tetap pekerjaan tim pada checkpoint berikutnya.

Verifikasi sesi pengembangan memakai Python bundled Codex, NumPy 2.3.5 dan Pillow 13.0.0.
Pillow runtime tersebut berada di luar batas `<13` requirements repo; kompatibilitas
persis pada lingkungan dependensi tim belum diuji. Gunakan requirements repo saat
menyiapkan lingkungan tim.
