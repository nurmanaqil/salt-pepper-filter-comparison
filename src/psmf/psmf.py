"""
psmf.py - Progressive Switching Median Filter (PSMF)

Referensi: Z. Wang & D. Zhang, "Progressive Switching Median Filter for the
Removal of Impulse Noise from Highly Corrupted Images", IEEE Trans. Circuits
and Systems II, 1999.
"""

import argparse
import os
import warnings

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
SKIP_NAME_KEYWORDS = ("mask", "ground", "truth")
MAX_RECOVERY_ITER = 100 


def _windows(img, w):
    r = w // 2
    padded = np.pad(img, r, mode="reflect")
    return sliding_window_view(padded, (w, w))


def _local_median(img, w):
    win = _windows(img, w)
    flat = win.reshape(img.shape[0], img.shape[1], -1)
    return np.median(flat, axis=-1)


def _masked_median(img, clean, w):
    val = _windows(img, w)
    cln = _windows(clean.astype(np.uint8), w).astype(bool)

    h, wd = img.shape
    val = val.reshape(h, wd, -1).astype(np.float32)
    cln = cln.reshape(h, wd, -1)

    cnt = cln.sum(axis=-1)
    val = np.where(cln, val, np.inf)
    val.sort(axis=-1)

    lo = np.clip((cnt - 1) // 2, 0, None)
    hi = np.clip(cnt // 2, 0, None)
    v_lo = np.take_along_axis(val, lo[..., None], axis=-1)[..., 0]
    v_hi = np.take_along_axis(val, hi[..., None], axis=-1)[..., 0]
    med = (v_lo + v_hi) / 2.0
    med[cnt == 0] = 0.0
    return med, cnt


def detect_impulses(image, WD=3, ND=3, TD=50):
    work = image.astype(np.int16)  
    mask = np.zeros(image.shape, dtype=bool)

    for _ in range(ND):
        med = np.rint(_local_median(work, WD)).astype(np.int16)
        diff = np.abs(work - med)               
        new_flag = diff >= TD
        if not new_flag.any():
            break
        mask |= new_flag                         
        work = np.where(new_flag, med, work)    
    return mask


def restore_image(image, mask, WF=3, max_iter=MAX_RECOVERY_ITER):
    out = image.astype(np.float32)              
    remaining = mask.copy()                   

    for _ in range(max_iter):
        if not remaining.any():
            break
        clean = ~remaining                   
        med, cnt = _masked_median(out, clean, WF)
        fixable = remaining & (cnt > 0)
        if not fixable.any():
            break                               
        out = np.where(fixable, med, out)
        remaining &= ~fixable                   

    if remaining.any():
        out = _fallback_restore(out, remaining, WF)

    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def _fallback_restore(out, remaining, WF):
    h, w = out.shape
    max_w = 2 * max(h, w) + 1
    win = WF + 2
    while remaining.any() and win <= max_w:
        clean = ~remaining
        if not clean.any():
            break
        med, cnt = _masked_median(out, clean, win)
        fixable = remaining & (cnt > 0)
        out = np.where(fixable, med, out)
        remaining &= ~fixable
        win += 2
    return out


def psmf_filter(image, WD=3, WF=3, ND=3, TD=50):
    if image.ndim != 2:
        raise ValueError("psmf_filter hanya menerima array 2D (grayscale).")
    if WD % 2 == 0 or WF % 2 == 0:
        raise ValueError("WD dan WF harus ganjil.")
    image = np.asarray(image, dtype=np.uint8)

    mask = detect_impulses(image, WD=WD, ND=ND, TD=TD)
    restored = restore_image(image, mask, WF=WF)
    return restored, mask


def _is_target_image(filename):
    stem, ext = os.path.splitext(filename)
    if ext.lower() not in IMAGE_EXTENSIONS:
        return False
    low = stem.lower()
    return not any(k in low for k in SKIP_NAME_KEYWORDS)


def process_folder(input_dir, output_dir, mask_dir, **params):
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(
            f"Folder input tidak ditemukan: '{os.path.abspath(input_dir)}'. "
            "Periksa --input atau jalankan dari folder root proyek."
        )
    count = 0
    for root, _, files in os.walk(input_dir):
        rel = os.path.relpath(root, input_dir)
        for name in sorted(files):
            if not _is_target_image(name):
                continue
            src = os.path.join(root, name)
            img = np.array(Image.open(src).convert("L"), dtype=np.uint8)

            restored, mask = psmf_filter(img, **params)

            out_sub = os.path.normpath(os.path.join(output_dir, rel))
            mask_sub = os.path.normpath(os.path.join(mask_dir, rel))
            os.makedirs(out_sub, exist_ok=True)
            os.makedirs(mask_sub, exist_ok=True)

            Image.fromarray(restored).save(os.path.join(out_sub, name))
            stem = os.path.splitext(name)[0]
            Image.fromarray((mask * 255).astype(np.uint8)).save(
                os.path.join(mask_sub, stem + ".png")
            )
            count += 1
    return count


def main():
    ap = argparse.ArgumentParser(description="PSMF batch processing")
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    ap.add_argument("--input", default=os.path.join(root, "dataset", "citra_berderau"))
    ap.add_argument("--output", default=os.path.join(root, "hasil", "psmf"))
    ap.add_argument("--mask_output",
                    default=os.path.join(root, "mask_deteksi", "psmf"))
    ap.add_argument("--WD", type=int, default=3)
    ap.add_argument("--WF", type=int, default=3)
    ap.add_argument("--ND", type=int, default=3)
    ap.add_argument("--TD", type=int, default=50)
    a = ap.parse_args()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        n = process_folder(a.input, a.output, a.mask_output,
                           WD=a.WD, WF=a.WF, ND=a.ND, TD=a.TD)
    if n == 0:
        print("PERINGATAN: 0 citra diproses. Cek folder input dan "
              "SKIP_NAME_KEYWORDS / IMAGE_EXTENSIONS.")
    print(f"Selesai: {n} citra diproses -> '{a.output}' dan '{a.mask_output}'")


if __name__ == "__main__":
    main()