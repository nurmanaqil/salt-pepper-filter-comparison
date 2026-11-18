"""Standard Median Filter: satu putaran median seluruh piksel, tanpa detektor."""

import argparse
import csv
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]  # src/smf/smf.py -> root proyek


def smf_filter(image, window=3):
    """Median sinkron, padding reflect. Mask keluaran = hasil != input."""
    if image.ndim != 2 or image.dtype != np.uint8:
        raise ValueError('Input harus grayscale uint8 dua dimensi.')
    if window < 1 or window % 2 == 0:
        raise ValueError('Ukuran jendela harus positif dan ganjil.')
    padded = np.pad(image, window // 2, mode='reflect')
    windows = sliding_window_view(padded, (window, window))
    result = np.median(windows, axis=(-2, -1)).astype(np.uint8)
    return result, result != image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT / 'dataset' / 'citra_berderau')
    parser.add_argument('--output', type=Path, default=ROOT / 'hasil' / 'smf')
    parser.add_argument('--mask_output', type=Path, default=ROOT / 'mask_deteksi' / 'smf')
    parser.add_argument('--window', type=int, default=3)
    args = parser.parse_args()
    if args.window < 1 or args.window % 2 == 0:
        parser.error('--window wajib positif dan ganjil.')
    if not args.input.is_dir():
        parser.error('Folder input tidak ditemukan.')
    # Hanya citra derau generator; mask dan gambar bukti tidak ikut difilter.
    files = sorted(args.input.rglob('*_derau.png'))
    if not files:
        parser.error('Tidak ada file *_derau.png pada input.')
    paths = [p.resolve() for p in (args.input, args.output, args.mask_output)]
    if any(a.is_relative_to(b) or b.is_relative_to(a)
           for i, a in enumerate(paths) for b in paths[i + 1:]):
        parser.error('Folder input, hasil, dan mask harus terpisah tanpa saling bersarang.')
    if args.output.exists() or args.mask_output.exists():
        parser.error('Folder hasil/mask sudah ada; gunakan folder baru agar tidak menimpa.')
    for path in files:
        with Image.open(path) as image:
            if image.mode != 'L':
                parser.error(f'{path.name}: input wajib grayscale 8-bit L.')
    args.output.mkdir(parents=True)
    args.mask_output.mkdir(parents=True)
    rows = []
    for path in files:
        with Image.open(path) as image:
            source = np.array(image)
        result, changed = smf_filter(source, args.window)
        relative = path.relative_to(args.input)
        out = args.output / relative
        mask_out = args.mask_output / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        mask_out.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(result).save(out)
        Image.fromarray(changed.astype(np.uint8) * 255).save(mask_out)
        rows.append(dict(file=relative.as_posix(), window=args.window,
                         padding='reflect', iterations=1, mask_type='output_ne_input',
                         changed_pixels=int(changed.sum()), total_pixels=source.size))
        print(f'{relative}: {int(changed.sum())} piksel berubah')
    with (args.output / 'metadata_smf.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    explanation = (
        '# Hasil SMF\n\nSMF standar mengganti setiap piksel dengan median lokal '
        f'{args.window} x {args.window}, satu putaran dengan padding reflect.\n\n'
        'SMF tidak memiliki tahap deteksi derau. Folder mask_deteksi/smf '
        'menyimpan MASK PERUBAHAN AKIBAT FILTER: putih (255) jika hasil berbeda '
        'dari input berderau, hitam (0) jika sama. Ini bukan prediksi piksel '
        'rusak, bukan mask injeksi, dan bukan mask perubahan aktual generator. '
        'Jangan memakai mask ini sebagai detektor SMF untuk menghitung '
        'akurasi deteksi atau membandingkan detektor PSMF/IPSMF.\n\n'
        'PNG di folder hasil/smf adalah hasil pemulihan SMF, bukan hasil '
        'deteksi. '
        'Subfolder mempertahankan rasio salt:pepper input.\n'
    )
    for folder in (args.output, args.mask_output):
        (folder / 'README.md').write_text(explanation, encoding='utf-8')
    print(f'Selesai: {len(rows)} hasil SMF dan {len(rows)} mask perubahan.')


if __name__ == '__main__':
    main()