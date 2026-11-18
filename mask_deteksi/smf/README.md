# Hasil SMF

SMF standar mengganti setiap piksel dengan median lokal 3 x 3, satu putaran dengan padding reflect.

SMF tidak memiliki tahap deteksi derau. Folder mask_deteksi_smf menyimpan MASK PERUBAHAN AKIBAT FILTER: putih (255) jika hasil berbeda dari input berderau, hitam (0) jika sama. Ini bukan prediksi piksel rusak, bukan mask injeksi, dan bukan mask perubahan aktual generator. Jangan memakai mask ini sebagai detektor SMF untuk menghitung akurasi deteksi atau membandingkan detektor PSMF/IPSMF.

Nama hasil_deteksi_smf mengikuti permintaan struktur folder; PNG di dalamnya adalah hasil pemulihan SMF, bukan hasil deteksi. Subfolder mempertahankan rasio salt:pepper input.
