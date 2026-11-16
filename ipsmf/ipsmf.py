"""IPSMF menurut Boo, Ibrahim & Toh (2009), DOI 10.1109/ICFCC.2009.87.

Jalankan dari root proyek: python -m ipsmf.ipsmf
Input hanya citra berderau; mask injeksi dan citra acuan tidak dipakai.
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image

from psmf.psmf import _windows, _local_median, _masked_median

BASE = Path(__file__).resolve().parents[1]
MAX_RECOVERY_ITER = 100


def _validate_image(image):
    if not isinstance(image, np.ndarray) or image.ndim != 2 or image.dtype != np.uint8 or not image.size:
        raise ValueError('Input harus array grayscale uint8 dua dimensi yang tidak kosong.')


def detect_impulses(image):
    """Estimasi RE (TI=40), lalu deteksi progresif ND=3; return mask, parameter."""
    _validate_image(image)
    work = image.astype(np.float32)
    RE = float(np.mean(np.abs(work - _local_median(work, 3)) >= 40))
    WD = 3 if RE <= 0.25 else 5
    TD = 65 - 50 * RE
    ND = 3
    mask = np.zeros(image.shape, dtype=bool)
    for _ in range(ND):
        med = _local_median(work, WD)
        # Persamaan deteksi mengganti hanya piksel yang BARU ditandai.
        new_flag = (~mask) & (np.abs(work - med) >= TD)
        work = np.where(new_flag, med, work)
        mask |= new_flag
    return mask, {'RE': RE, 'WD': WD, 'TD': TD, 'ND': ND}


def restore_image(image, mask, WF=3, GP=5, max_iter=MAX_RECOVERY_ITER):
    """Median-mean tetangga bersih, minimum GP; pembaruan serentak per iterasi.

    Return citra dan laporan. Tidak memperbesar jendela jika macet: piksel
    yang belum pulih dipertahankan dan jumlahnya dilaporkan secara eksplisit.
    """
    _validate_image(image)
    if mask.shape != image.shape or mask.dtype != bool:
        raise ValueError('Mask wajib bool dengan ukuran sama seperti citra.')
    if WF != 3 or not isinstance(GP, int) or not 1 <= GP <= 8 or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError('IPSMF memakai WF=3, GP integer 1..8, max_iter integer positif.')
    out = image.astype(np.float32)
    remaining = mask.copy()
    iterations = 0
    stop_reason = 'complete'
    while remaining.any():
        if iterations >= max_iter:
            stop_reason = 'max_iter'
            break
        clean = ~remaining
        med, cnt = _masked_median(out, clean, WF)
        val = _windows(out, WF)
        cln = _windows(clean, WF)
        mean = np.divide(np.where(cln, val, 0).sum(axis=(-2, -1)), cnt,
                         out=np.zeros_like(out), where=cnt > 0)
        fixable = remaining & (cnt >= GP)
        if not fixable.any():
            stop_reason = 'no_progress'
            break
        out = np.where(fixable, (med + mean) / 2, out)
        remaining &= ~fixable
        iterations += 1
    return np.clip(np.rint(out), 0, 255).astype(np.uint8), {
        'recovery_iterations': iterations,
        'unresolved_pixels': int(remaining.sum()), 'stop_reason': stop_reason,
    }


def ipsmf_filter(image, GP=5, max_iter=MAX_RECOVERY_ITER, return_info=False):
    """Return (hasil uint8, mask bool), opsional ditambah laporan parameter."""
    mask, info = detect_impulses(image)
    restored, recovery = restore_image(image, mask, GP=GP, max_iter=max_iter)
    if return_info:
        return restored, mask, {**info, 'WF': 3, 'GP': GP,
                                'detected_pixels': int(mask.sum()), **recovery}
    return restored, mask


def process_folder(input_dir, output_dir, mask_dir, **params):
    input_dir, output_dir, mask_dir = map(Path, (input_dir, output_dir, mask_dir))
    # Cocok dengan generator: hanya *_derau.png, bukan mask atau gambar bukti.
    files = sorted(input_dir.rglob('*_derau.png'))
    if not files:
        raise ValueError(f'Tidak ada *_derau.png pada {input_dir}')
    if output_dir.exists() or mask_dir.exists():
        raise ValueError('Folder output/mask sudah ada; pilih folder baru agar hasil tidak tertimpa.')
    a, b = output_dir.resolve(), mask_dir.resolve()
    source = input_dir.resolve()
    if a == b or a in b.parents or b in a.parents or source == a or source == b or source in a.parents or source in b.parents:
        raise ValueError('Folder output dan mask harus terpisah dan di luar folder input.')
    # Validasi semua input sebelum membuat hasil.
    for path in files:
        with Image.open(path) as img:
            if img.mode != 'L':
                raise ValueError(f'{path}: wajib grayscale 8-bit mode L.')
    records = []
    for path in files:
        with Image.open(path) as img:
            image = np.array(img)
        restored, mask, info = ipsmf_filter(image, return_info=True, **params)
        relative = path.relative_to(input_dir)
        target = output_dir / relative
        mask_target = mask_dir / relative.parent / (path.stem + '_mask_deteksi.png')
        target.parent.mkdir(parents=True, exist_ok=True)
        mask_target.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(restored).save(target)
        Image.fromarray(mask.astype(np.uint8) * 255).save(mask_target)
        records.append({'citra_berderau': relative.as_posix(), **info})
        print(f'{relative}: deteksi={info["detected_pixels"]}, '
              f'sisa={info["unresolved_pixels"]}, status={info["stop_reason"]}')
    with (output_dir / 'metadata_ipsmf.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE / 'citra_berderau')
    parser.add_argument('--output', type=Path, default=BASE / 'hasil_ipsmf')
    parser.add_argument('--mask_output', type=Path, default=BASE / 'mask_deteksi_ipsmf')
    parser.add_argument('--GP', type=int, choices=range(1, 9), default=5)
    parser.add_argument('--max_iter', type=int, default=MAX_RECOVERY_ITER)
    args = parser.parse_args()
    if args.max_iter < 1:
        parser.error('--max_iter harus positif.')
    try:
        count = process_folder(args.input, args.output, args.mask_output,
                               GP=args.GP, max_iter=args.max_iter)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f'Selesai: {count} citra. Hasil: {args.output}; mask: {args.mask_output}')


if __name__ == '__main__':
    main()
