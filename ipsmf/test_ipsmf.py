"""Jalankan: python -m unittest ipsmf.test_ipsmf"""
import unittest

import numpy as np

from ipsmf.ipsmf import detect_impulses, ipsmf_filter, restore_image


class IPSMFTests(unittest.TestCase):
    def test_constant_image(self):
        image = np.full((9, 9), 120, dtype=np.uint8)
        result, mask, info = ipsmf_filter(image, return_info=True)
        np.testing.assert_array_equal(result, image)
        self.assertFalse(mask.any())
        self.assertEqual((info['RE'], info['WD'], info['TD']), (0, 3, 65))

    def test_isolated_salt_and_pepper(self):
        for value in (0, 255):
            image = np.full((9, 9), 120, dtype=np.uint8)
            image[4, 4] = value
            result, mask = ipsmf_filter(image)
            self.assertEqual(int(mask.sum()), 1)
            self.assertEqual(int(result[4, 4]), 120)
            np.testing.assert_array_equal(result[~mask], image[~mask])

    def test_median_mean_manual(self):
        image = np.array([[10, 20, 30], [40, 255, 50], [60, 70, 200]], dtype=np.uint8)
        mask = np.zeros((3, 3), dtype=bool)
        mask[1, 1] = True
        result, info = restore_image(image, mask)
        # Median=45; mean=60; hasil=52.5, np.rint -> 52.
        self.assertEqual(int(result[1, 1]), 52)
        self.assertEqual(info['unresolved_pixels'], 0)

    def test_minimum_good_pixels_and_stall(self):
        image = np.full((5, 5), 100, dtype=np.uint8)
        mask = np.ones(image.shape, dtype=bool)
        mask[1:3, 1:3] = False  # pusat hanya memiliki empat piksel bersih
        result, info = restore_image(image, mask)
        self.assertEqual(info['stop_reason'], 'no_progress')
        self.assertEqual(info['unresolved_pixels'], 21)
        np.testing.assert_array_equal(result, image)

    def test_adaptive_detection_and_synchronous_update(self):
        rng = np.random.default_rng(12)
        image = rng.choice(np.array([0, 120, 255], dtype=np.uint8), (13, 13))
        work = image.astype(float)
        def median_at(array, w):
            padded = np.pad(array, w // 2, mode='reflect')
            return np.array([[np.median(padded[y:y+w, x:x+w])
                              for x in range(13)] for y in range(13)])
        RE = float(np.mean(np.abs(work - median_at(work, 3)) >= 40))
        WD = 3 if RE <= .25 else 5
        mask = np.zeros(image.shape, dtype=bool)
        for _ in range(3):
            med = median_at(work, WD)
            new = (~mask) & (np.abs(work - med) >= 65 - 50 * RE)
            work[new] = med[new]
            mask |= new
        actual, info = detect_impulses(image)
        self.assertEqual(info['WD'], 5)
        np.testing.assert_array_equal(actual, mask)


if __name__ == '__main__':
    unittest.main()
