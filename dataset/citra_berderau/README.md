# Penjelasan hasil generator derau

Folder ini berisi hasil penambahan derau salt-and-pepper pada crop tulisan
tangan IAM berukuran 512 × 512 piksel, grayscale 8-bit.

## Derau itu apa?

Derau adalah gangguan pada gambar. Program memilih sekitar **30% posisi
piksel** untuk diberi salah satu nilai berikut:

- **Salt = 255**, yaitu putih.
- **Pepper = 0**, yaitu hitam.

Pada gambar 512 × 512 terdapat 262.144 piksel. Sebanyak 30% dari jumlah itu
dibulatkan menjadi **78.643 posisi injeksi**. Jadi angka 30% menyatakan posisi
yang dipilih, bukan jaminan bahwa semuanya berubah nilai.

## Arti folder komposisi

Urutan rasio selalu **salt:pepper**, dihitung dari posisi injeksi.

| Folder | Komposisi | Jumlah salt | Jumlah pepper |
|---|---|---:|---:|
| `25_75` | 25% putih, 75% hitam | 19.661 | 58.982 |
| `50_50` | 50% putih, 50% hitam | 39.322 | 39.321 |
| `75_25` | 75% putih, 25% hitam | 58.982 | 19.661 |

Jumlah dibulatkan karena sebagian piksel tidak bisa dipilih. Selisih satu
piksel pada rasio 50:50 adalah akibat pembulatan.

## Seed itu apa?

**Seed** adalah angka pengendali pengacakan, misalnya `42`. Angka ini bukan
persentase derau dan bukan jumlah piksel rusak.

Dengan gambar, nama file, seed, algoritme, dan versi NumPy yang sama, hasil
bisa dibuat ulang. Seed berbeda menghasilkan pengacakan berbeda.
Program menurunkan seed khusus setiap crop dari seed pengguna dan nama file,
sehingga penambahan file lain tidak mengubah hasil crop yang sudah ada.

Untuk satu crop dan seed, ketiga rasio menggunakan **posisi injeksi dan urutan
acak yang sama**. Perbedaannya hanya pembagian salt dan pepper. Posisi salt
pada rasio 25:75 menjadi bagian dari posisi salt pada 50:50 dan 75:25.
Ini membantu membandingkan pengaruh rasio secara adil.

## Mask injeksi dan mask berubah

**Mask** adalah gambar penanda lokasi piksel, bukan gambar hasil pemulihan.
Pada kedua jenis mask:

- Putih (255) berarti posisi ditandai.
- Hitam (0) berarti posisi tidak ditandai.

**Mask injeksi** menandai semua posisi yang dipilih untuk diberi derau.
**Mask berubah** hanya menandai piksel yang nilainya benar-benar berbeda
antara crop bersih dan gambar berderau.

| Nilai asli | Perlakuan | Nilai akhir | Mask injeksi | Mask berubah |
|---|---|---|---|---|
| 180 | Diberi salt | 255 | Putih | Putih |
| 255 | Diberi salt | 255 | Putih | Hitam |
| 0 | Diberi pepper | 0 | Putih | Hitam |
| 100 | Tidak dipilih | 100 | Hitam | Hitam |

Jadi posisi bisa dipilih untuk injeksi tanpa berubah nilai. Jumlah piksel pada
mask berubah tidak pernah melebihi jumlah pada mask injeksi. Pada tiga crop
dengan seed 42 yang dibuat dalam proses awal, semua posisi injeksi berubah,
sehingga kedua mask identik. Keadaan ini tidak harus terjadi pada gambar atau
seed lain.

## Cara membaca nama file

Contoh satu kelompok file:

```text
e01-014_x700_y1050_512x512_seed42_derau.png
e01-014_x700_y1050_512x512_seed42_mask_injeksi.png
e01-014_x700_y1050_512x512_seed42_mask_berubah.png
```

- `e01-014`: ID halaman IAM asal.
- `x700_y1050`: koordinat kiri atas crop pada halaman asli.
- `512x512`: ukuran crop dalam piksel.
- `seed42`: seed pengguna yang dipakai.
- `_derau.png`: gambar yang menerima gangguan, sebagai input filter.
- `_mask_injeksi.png`: peta posisi terpilih untuk injeksi.
- `_mask_berubah.png`: peta perubahan aktual terhadap crop bersih.

Rasio ditentukan oleh folder tempat file disimpan. Crop bersih pembanding
berada di folder `../hasil_crop`.

## Metadata dan pemakaian eksperimen

`metadata_derau.csv` mencatat sumber crop, hash SHA-256 sumber, seed, versi
NumPy, rasio, jumlah injeksi, jumlah salt/pepper, jumlah perubahan aktual,
serta lokasi gambar dan mask. Hash adalah sidik jari file untuk memeriksa
apakah file sumber masih identik.

Setiap filter harus menerima gambar berderau yang sama untuk kondisi yang
sama. Mask ini merupakan bukti dari generator dan bahan evaluasi; jangan
memberikannya kepada filter untuk menggantikan proses deteksi asli filter.
Mask berubah dapat dipakai untuk evaluasi pada piksel yang benar-benar rusak.

## Menjalankan ulang

Dari folder proyek:

```powershell
python generator_derau.py --seed 42
```

Program berhenti jika folder output sudah ada agar hasil lama tidak tertimpa.
Untuk percobaan baru, tentukan folder output baru:

```powershell
python generator_derau.py --seed 43 --output citra_berderau_seed43
```

README ini menjelaskan keluaran saat ini; generator menyimpan PNG dan CSV,
tetapi tidak otomatis menyalin README ke folder percobaan baru.
