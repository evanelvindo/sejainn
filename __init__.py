"""
File inisialisasi untuk paket handlers.worker.
Mengelola alur kerja Mitra mulai dari registrasi, penerimaan order, 
hingga pengiriman bukti penyelesaian kerja.
"""

from .broadcast import broadcast_to_workers
from .order_ops import worker_take_handler
from .submission import worker_send_bukti
from .registration import worker_registration_handler

# Mendefinisikan public API dari package worker
# Pastikan semua fungsi yang terdaftar di sini sudah diimplementasikan di sub-modulnya
__all__ = [
    'broadcast_to_workers',         # Mengirim notifikasi order baru ke semua mitra aktif
    'worker_take_handler',          # Menangani aksi mitra saat mengambil order (Tombol Ambil)
    'worker_send_bukti',            # Menangani proses pengiriman foto bukti kerja oleh mitra
    'worker_registration_handler'   # Menangani pendaftaran mitra baru ke sistem
]