"""
File ini mendefinisikan konstanta State untuk ConversationHandler Sejaiin Hub.
Menggunakan range() untuk memberikan nilai integer unik pada setiap tahapan percakapan.
Last Update: 2026-05-16 (Sistem Perantara & Escrow HUB 1)
"""

(
    CATEGORY,           # 0: Tahap memilih HUB (Kategori)
    SERVICE,            # 1: Tahap memilih Jasa spesifik
    ASK_LOCATION,       # 2: Tahap transisi / deteksi kategori jastip
    WAITING_TITIPIAN,   # 3: Tahap menunggu input nominal uang titipan belanja (HUB 1)
    WAITING_LOCATION,   # 4: Tahap menunggu input lokasi (GPS/Teks)
    WAITING_CONTACT,    # 5: Tahap menunggu kiriman kontak WhatsApp
    WAITING_PHOTO       # 6: Tahap menunggu upload bukti transfer
) = range(7)