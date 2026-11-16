"""Generator salt-and-pepper berpasangan: injeksi 30%, tiga rasio salt:pepper.

Jalankan: python generator_derau.py --seed 42
Dependensi: numpy dan Pillow. Input default: PNG pada hasil_crop (tanpa rekursi).
"""

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image


BASE = Path(__file__).resolve().parent
RASIO_SALT = (25, 50, 75)


def buat_derau(citra, seed_crop):
    """Kembalikan tiga kondisi dengan satu urutan posisi injeksi bersama.

    Jumlah dibulatkan ke bilangan bulat terdekat (setengah dibulatkan naik).
    Mask bool True menandai posisi terpilih atau piksel berubah.
    Citra acuan tidak diubah. Salt memakai awalan urutan posisi yang sama.
    """
    if citra.dtype != np.uint8 or citra.ndim != 2:
        raise ValueError('Input harus berupa array grayscale uint8 dua dimensi.')
    jumlah_injeksi = (citra.size * 30 + 50) // 100
    rng = np.random.default_rng(seed_crop)
    posisi = rng.choice(citra.size, size=jumlah_injeksi, replace=False)
    mask_injeksi = np.zeros(citra.shape, dtype=bool)
    mask_injeksi.flat[posisi] = True
    hasil = {}
    for salt in RASIO_SALT:
        jumlah_salt = (jumlah_injeksi * salt + 50) // 100
        berderau = citra.copy()
        berderau.flat[posisi[:jumlah_salt]] = 255
        berderau.flat[posisi[jumlah_salt:]] = 0
        hasil[salt] = (berderau, mask_injeksi.copy(), berderau != citra, jumlah_salt)
    return hasil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE / 'hasil_crop')
    parser.add_argument('--output', type=Path, default=BASE / 'citra_berderau')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    if args.seed < 0:
        parser.error('Seed harus bilangan bulat nonnegatif.')
    if args.output.exists():
        parser.error('Folder output sudah ada; gunakan --output dengan folder baru.')
    files = sorted(args.input.glob('*.png'))
    if not files:
        parser.error(f'Tidak ada PNG pada folder input: {args.input}')

    # Periksa semua input sebelum menulis keluaran apa pun.
    inputs = []
    for path in files:
        with Image.open(path) as image:
            if image.mode != 'L' or image.size != (512, 512):
                parser.error(f'{path.name}: wajib grayscale 8-bit L, ukuran 512 x 512.')
            inputs.append((path, np.array(image)))

    args.output.mkdir(parents=True, exist_ok=False)
    for salt in RASIO_SALT:
        (args.output / f'{salt}_{100 - salt}').mkdir()
    records = []
    for path, citra in inputs:
        # Seed per crop stabil terhadap urutan/jumlah file input.
        # Nama berbeda menghasilkan urutan acak berbeda, tetap dapat diulang.
        seed_crop = int.from_bytes(
            hashlib.sha256(f'{args.seed}\0{path.name}'.encode('utf-8')).digest()[:8],
            'big',
        )
        conditions = buat_derau(citra, seed_crop)
        for salt, (berderau, injeksi, berubah, jumlah_salt) in conditions.items():
            folder = args.output / f'{salt}_{100 - salt}'
            prefix = f'{path.stem}_seed{args.seed}'
            nama = {
                'citra_berderau': f'{prefix}_derau.png',
                'mask_injeksi': f'{prefix}_mask_injeksi.png',
                'mask_berubah': f'{prefix}_mask_berubah.png',
            }
            Image.fromarray(berderau).save(folder / nama['citra_berderau'])
            # PNG mask: putih (255) = ditandai, hitam (0) = tidak ditandai.
            Image.fromarray(injeksi.astype(np.uint8) * 255).save(folder / nama['mask_injeksi'])
            Image.fromarray(berubah.astype(np.uint8) * 255).save(folder / nama['mask_berubah'])
            n_injeksi = int(injeksi.sum())
            n_berubah = int(berubah.sum())
            records.append({
                'crop_id': path.stem,
                'source_file': path.name,
                'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'seed': args.seed,
                'seed_crop': seed_crop,
                'rng': 'numpy.default_rng/PCG64',
                'numpy_version': np.__version__,
                'rasio_salt_pepper': f'{salt}:{100 - salt}',
                'width': citra.shape[1], 'height': citra.shape[0],
                'total_piksel': citra.size,
                'target_injeksi_persen': 30,
                'jumlah_injeksi': n_injeksi,
                'injeksi_aktual_persen': 100 * n_injeksi / citra.size,
                'jumlah_salt_ditugaskan': jumlah_salt,
                'jumlah_pepper_ditugaskan': n_injeksi - jumlah_salt,
                'salt_aktual_persen_dari_injeksi': 100 * jumlah_salt / n_injeksi,
                'jumlah_piksel_berubah': n_berubah,
                'berubah_aktual_persen': 100 * n_berubah / citra.size,
                **{key: (folder / name).relative_to(args.output).as_posix()
                   for key, name in nama.items()},
            })
            print(f'{path.name} | {salt}:{100-salt} | injeksi={n_injeksi}, '
                  f'salt={jumlah_salt}, pepper={n_injeksi-jumlah_salt}, berubah={n_berubah}')

    with (args.output / 'metadata_derau.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f'Selesai: {len(records)} citra berderau dan {len(records) * 2} mask.')
    print(f'Output: {args.output.resolve()}')


if __name__ == '__main__':
    main()
