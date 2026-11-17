"""Evaluasi satu pasangan clean, noisy, dan restored untuk checkpoint 2."""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image


def load_gray(path):
    """Baca grayscale 8-bit tanpa konversi atau perubahan gambar."""
    with Image.open(path) as image:
        if image.mode != 'L':
            raise ValueError(f'{path}: wajib grayscale 8-bit (mode L), ditemukan {image.mode}.')
        return np.array(image)


def evaluate_pair(clean, noisy, restored):
    """Hitung metrik input dan hasil pada mask tetap noisy != clean.

    MSE area berubah bernilai None jika mask kosong; PSNR bernilai inf jika
    MSE global nol. Fungsi hanya menghitung, tanpa menjalankan filter.
    """
    for image in (clean, noisy, restored):
        if (not isinstance(image, np.ndarray) or image.ndim != 2
                or image.dtype != np.uint8 or not image.size):
            raise ValueError('Ketiga citra wajib array grayscale uint8 dua dimensi, tidak kosong.')
    if clean.shape != noisy.shape or clean.shape != restored.shape:
        raise ValueError('Ukuran clean, noisy, dan restored harus sama.')

    changed = noisy != clean
    count = int(changed.sum())
    result = {'jumlah_piksel_berubah': count}
    for label, candidate in [('input', noisy), ('hasil', restored)]:
        squared = (candidate.astype(np.float64) - clean.astype(np.float64)) ** 2
        mse_global = float(squared.mean())
        result[f'mse_berubah_{label}'] = float(squared[changed].mean()) if count else None
        result[f'mse_global_{label}'] = mse_global
        result[f'psnr_global_{label}_db'] = (
            10 * math.log10(255 ** 2 / mse_global) if mse_global else math.inf)
    result['metric_note'] = '' if count else 'empty_changed_mask'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clean', type=Path, required=True, help='Citra asli/crop bersih')
    parser.add_argument('--noisy', type=Path, required=True, help='Citra berderau dari crop yang sama')
    parser.add_argument('--restored', type=Path, required=True, help='Hasil satu filter untuk input noisy tersebut')
    args = parser.parse_args(argv)
    try:
        result = evaluate_pair(load_gray(args.clean), load_gray(args.noisy), load_gray(args.restored))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    for key, value in result.items():
        if value is None:
            value = 'NA'
        elif isinstance(value, float) and math.isfinite(value):
            value = f'{value:.10f}'.rstrip('0').rstrip('.')
        print(f'{key}: {value}')


if __name__ == '__main__':
    main()
