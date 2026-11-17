"""Bukti hitung manual dan kasus batas evaluator C2."""
import contextlib
import io
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from evaluasi.evaluasi import evaluate_pair, load_gray, main


class EvaluasiTests(unittest.TestCase):
    def setUp(self):
        self.clean = np.array([[10, 20], [30, 40]], dtype=np.uint8)
        self.noisy = np.array([[255, 20], [30, 0]], dtype=np.uint8)
        self.restored = np.array([[12, 20], [30, 36]], dtype=np.uint8)

    def test_manual_example(self):
        result = evaluate_pair(self.clean, self.noisy, self.restored)
        self.assertEqual(result['jumlah_piksel_berubah'], 2)
        self.assertEqual(result['mse_berubah_hasil'], 10)
        self.assertEqual(result['mse_global_hasil'], 5)
        self.assertAlmostEqual(result['psnr_global_hasil_db'], 41.1411035653)
        self.assertEqual(result['mse_berubah_input'], (245**2 + 40**2) / 2)

    def test_uint8_does_not_overflow(self):
        clean = np.array([[0]], dtype=np.uint8)
        noisy = np.array([[255]], dtype=np.uint8)
        self.assertEqual(evaluate_pair(clean, noisy, noisy)['mse_global_hasil'], 65025)

    def test_perfect_recovery(self):
        result = evaluate_pair(self.clean, self.noisy, self.clean)
        self.assertEqual(result['mse_berubah_hasil'], 0)
        self.assertTrue(math.isinf(result['psnr_global_hasil_db']))

    def test_empty_changed_mask(self):
        result = evaluate_pair(self.clean, self.clean, self.clean)
        self.assertIsNone(result['mse_berubah_hasil'])
        self.assertEqual(result['metric_note'], 'empty_changed_mask')
        self.assertEqual(result['mse_global_hasil'], 0)

    def test_global_error_still_counts_when_changed_mask_empty(self):
        result = evaluate_pair(self.clean, self.clean, self.restored)
        self.assertIsNone(result['mse_berubah_hasil'])
        self.assertEqual(result['mse_global_hasil'], 5)

    def test_mask_is_fixed_from_noisy_not_restored(self):
        clean = np.array([[10, 20]], dtype=np.uint8)
        noisy = np.array([[255, 20]], dtype=np.uint8)
        restored = np.array([[10, 24]], dtype=np.uint8)
        result = evaluate_pair(clean, noisy, restored)
        self.assertEqual(result['mse_berubah_hasil'], 0)
        self.assertEqual(result['mse_global_hasil'], 8)

    def test_mismatched_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pair(self.clean, self.noisy[:1], self.restored)

    def test_non_grayscale_and_wrong_dtype_rejected(self):
        for invalid in [np.zeros((2, 2, 3), np.uint8), self.clean.astype(float), np.array([], np.uint8)]:
            with self.subTest(shape=invalid.shape, dtype=invalid.dtype), self.assertRaises(ValueError):
                evaluate_pair(invalid, self.noisy, self.restored)

    def test_rgb_file_is_not_silently_converted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'rgb.png'
            Image.new('RGB', (2, 2)).save(path)
            with self.assertRaises(ValueError):
                load_gray(path)

    def test_cli_reads_three_files_without_creating_output_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name, array in [('clean', self.clean), ('noisy', self.noisy), ('restored', self.restored)]:
                Image.fromarray(array).save(folder / f'{name}.png')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main(['--clean', str(folder / 'clean.png'), '--noisy', str(folder / 'noisy.png'),
                      '--restored', str(folder / 'restored.png')])
            self.assertIn('mse_berubah_hasil: 10', output.getvalue())
            self.assertIn('psnr_global_hasil_db: 41.1411035653', output.getvalue())
            self.assertEqual(len(list(folder.iterdir())), 3)


if __name__ == '__main__':
    unittest.main()
