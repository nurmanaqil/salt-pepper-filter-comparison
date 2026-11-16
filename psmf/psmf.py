"""
psmf.py - Progressive Switching Median Filter (PSMF)

Referensi: Z. Wang & D. Zhang, "Progressive Switching Median Filter for the
Removal of Impulse Noise from Highly Corrupted Images", IEEE Trans. Circuits
and Systems II, 1999.

Hanya memakai numpy + Pillow (tanpa filter instan seperti cv2.medianBlur
atau scipy.ndimage.median_filter). Pemrosesan bersifat BLIND: tidak ada
ground truth / mask injeksi derau yang dipakai.

Pemakaian:
    python psmf.py                                   # default folder
    python psmf.py --input citra_berderau --output hasil_psmf \
                   --mask_output mask_deteksi_psmf --WD 3 --WF 3 --ND 3 --TD 50
"""

import argparse
import os
import warnings

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image

# ----------------------------------------------------------------------------
# Pengaturan yang mudah disesuaikan
# ----------------------------------------------------------------------------
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
# File yang namanya mengandung salah satu kata ini dianggap file mask/ground
# truth dan DILEWATI. Ubah sesuai konvensi penamaan di dataset tim.
SKIP_NAME_KEYWORDS = ("mask", "ground", "truth")
MAX_RECOVERY_ITER = 100  # batas iterasi pemulihan (Tahap 2)


# ----------------------------------------------------------------------------
# Utilitas jendela
# ----------------------------------------------------------------------------
def _windows(img, w):
    """Kembalikan view (H, W, w, w) dari semua jendela w x w (padding reflect)."""
    r = w // 2
    padded = np.pad(img, r, mode="reflect")
    return sliding_window_view(padded, (w, w))


def _local_median(img, w):
    """Median lokal w x w untuk seluruh piksel (float32, tanpa overflow)."""
    win = _windows(img, w)
    flat = win.reshape(img.shape[0], img.shape[1], -1)
    return np.median(flat, axis=-1)


def _masked_median(img, clean, w):
    """
    Median dari piksel BERSIH saja di dalam jendela w x w.
    Return: (median, jumlah_tetangga_bersih) -> keduanya (H, W).
    Piksel tanpa tetangga bersih mendapat jumlah 0 (nilai median-nya diabaikan).
    """
    val = _windows(img, w)
    cln = _windows(clean.astype(np.uint8), w).astype(bool)

    h, wd = img.shape
    val = val.reshape(h, wd, -1).astype(np.float32)
    cln = cln.reshape(h, wd, -1)

    cnt = cln.sum(axis=-1)
    # nilai tak bersih -> +inf supaya terurut ke belakang, lalu ambil indeks tengah
    val = np.where(cln, val, np.inf)
    val.sort(axis=-1)

    lo = np.clip((cnt - 1) // 2, 0, None)
    hi = np.clip(cnt // 2, 0, None)
    v_lo = np.take_along_axis(val, lo[..., None], axis=-1)[..., 0]
    v_hi = np.take_along_axis(val, hi[..., None], axis=-1)[..., 0]
    med = (v_lo + v_hi) / 2.0
    med[cnt == 0] = 0.0
    return med, cnt


# ----------------------------------------------------------------------------
# Tahap 1: deteksi derau iteratif
# ----------------------------------------------------------------------------
def detect_impulses(image, WD=3, ND=3, TD=50):
    """
    Deteksi iteratif. Pada setiap iterasi:
      1. median lokal WD x WD dihitung dari citra kerja,
      2. piksel dengan |x - median| >= TD ditandai rusak (mask di-OR-kan
         dengan mask iterasi sebelumnya, sehingga tanda tidak pernah hilang),
      3. piksel yang ditandai pada iterasi ini diganti median lokalnya di
         citra kerja agar iterasi berikutnya mendeteksi dari citra yang
         lebih bersih.
    """
    work = image.astype(np.int16)  # int16 -> selisih negatif aman
    mask = np.zeros(image.shape, dtype=bool)

    for _ in range(ND):
        med = np.rint(_local_median(work, WD)).astype(np.int16)
        diff = np.abs(work - med)               # |x - median|, tanpa overflow
        new_flag = diff >= TD
        if not new_flag.any():
            break
        mask |= new_flag                         # akumulasi mask antar-iterasi
        work = np.where(new_flag, med, work)     # ganti dengan median lokal
    return mask


# ----------------------------------------------------------------------------
# Tahap 2: pemulihan iteratif (mulai dari citra berderau ASLI)
# ----------------------------------------------------------------------------
def restore_image(image, mask, WF=3, max_iter=MAX_RECOVERY_ITER):
    """
    Pemulihan progresif. Hanya piksel rusak yang diubah, dan hanya memakai
    median dari tetangga BERSIH dalam jendela WF x WF.
    Piksel tanpa tetangga bersih dilewati dan dicoba lagi pada iterasi
    berikutnya, setelah tetangganya pulih (piksel yang baru pulih dianggap
    bersih pada iterasi selanjutnya).
    """
    out = image.astype(np.float32)               # mulai dari citra berderau asli
    remaining = mask.copy()                      # piksel yang belum pulih

    for _ in range(max_iter):
        if not remaining.any():
            break
        clean = ~remaining                       # mask diperbarui tiap iterasi
        med, cnt = _masked_median(out, clean, WF)
        fixable = remaining & (cnt > 0)
        if not fixable.any():
            break                                # macet -> tangani di fallback
        out = np.where(fixable, med, out)
        remaining &= ~fixable                    # yang sudah pulih jadi "bersih"

    # ---- Kasus ekstrem: piksel rusak yang masih tersisa -------------------
    # (mis. blok rusak lebih besar dari jendela, atau batas iterasi tercapai)
    if remaining.any():
        out = _fallback_restore(out, remaining, WF)

    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def _fallback_restore(out, remaining, WF):
    """
    Fallback untuk piksel yang tetap terisolasi: perbesar jendela (WF+2, WF+4,
    ...) sampai ada tetangga bersih. Jika seluruh citra rusak (tidak ada piksel
    bersih sama sekali), nilai piksel dibiarkan apa adanya.
    """
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


# ----------------------------------------------------------------------------
# Fungsi inti
# ----------------------------------------------------------------------------
def psmf_filter(image, WD=3, WF=3, ND=3, TD=50):
    """
    PSMF.

    Parameter
    ---------
    image : ndarray 2D uint8, citra grayscale berderau
    WD    : ukuran jendela deteksi (ganjil)
    WF    : ukuran jendela pemulihan (ganjil)
    ND    : jumlah iterasi deteksi
    TD    : ambang deteksi

    Return
    ------
    (citra_hasil uint8, mask_deteksi bool) ; mask True = terdeteksi rusak.
    """
    if image.ndim != 2:
        raise ValueError("psmf_filter hanya menerima array 2D (grayscale).")
    if WD % 2 == 0 or WF % 2 == 0:
        raise ValueError("WD dan WF harus ganjil.")
    image = np.asarray(image, dtype=np.uint8)

    mask = detect_impulses(image, WD=WD, ND=ND, TD=TD)
    restored = restore_image(image, mask, WF=WF)
    return restored, mask


# ----------------------------------------------------------------------------
# Pemrosesan batch
# ----------------------------------------------------------------------------
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
    # Default path relatif terhadap root proyek (folder induk dari folder script
    # ini), sehingga bisa dijalankan dari mana saja.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--input", default=os.path.join(root, "citra_berderau"))
    ap.add_argument("--output", default=os.path.join(root, "hasil_psmf"))
    ap.add_argument("--mask_output",
                    default=os.path.join(root, "mask_deteksi_psmf"))
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