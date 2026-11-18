# Standard Median Filter (SMF)

Jalankan dari folder proyek:

```powershell
python smf/smf.py
```

Implementasi memakai NumPy dan Pillow yang sudah tercatat di requirements.txt.
Default: median 3 x 3, satu putaran, seluruh piksel diproses serentak dari
input awal, tepi ditangani dengan padding reflect, sama seperti fungsi
jendela pada program PSMF di proyek ini. Tidak memakai crop bersih atau mask
generator untuk menentukan hasil. Ukuran jendela ini konfigurasi awal pilot.

Input: file *_derau.png dalam citra_berderau beserta subfoldernya.
Output: hasil_deteksi_smf dan mask_deteksi_smf, masing-masing mempertahankan
subfolder rasio. Folder hasil menyimpan metadata_smf.csv. Output lama tidak
ditimpa; untuk mencoba ulang gunakan --output dan --mask_output folder baru.
Ukuran jendela bisa ditentukan dengan --window (bilangan positif ganjil).

**SMF tidak memiliki detektor.** Sesuai penamaan folder yang diminta,
mask_deteksi_smf berisi mask PERUBAHAN OUTPUT TERHADAP INPUT BERDERAU,
bukan hasil deteksi piksel rusak. Putih 255 berarti nilai berubah oleh SMF;
hitam 0 berarti tetap. Mask ini jangan dianggap setara dengan mask deteksi
PSMF/IPSMF atau dipakai menghitung akurasi deteksi derau SMF.
Folder hasil_deteksi_smf berisi citra hasil pemulihan.
