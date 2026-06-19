"""
File ini berisi daftar statis kategori dan layanan Sejaiin Hub.
Data di sini digunakan untuk membangun Keyboard Button secara dinamis.
Last Update: 2026-05-16 (Sistem Perantara & Escrow)
"""

LAYANAN = {
    "🛵 HUB 1: Jastip & Kebutuhan Kampus": [
        "Jastip Print & Jilid Tugas",
        "Jastip Makanan & Minuman",
        "Jastip Belanja Minimarket/Kos"
    ],
    "💻 HUB 2: Digital & Layanan IT": [
        "Jasa Instalasi Software Kuliah",
        "Cleaning & Ganti Thermal Paste",
        "Desain PPT / Poster Kuliah"
    ],
    "🧹 HUB 3: Domestik & Layanan Tenaga": [
        "Jasa Cuci Sepatu atau Helm",
        "Deep Cleaning Kamar Kos",
        "Jasa Setrika Kiloan"
    ]
}

# Daftar bank untuk metode pembayaran (Opsional, mempermudah maintenance)
METODE_PEMBAYARAN = [
    "🏧 Bank Mandiri",
    "🏧 Bank BCA",
    "📱 E-Wallet (Dana/OVO/GoPay)"
]

def get_kategori_list():
    """Mengambil semua nama kategori (Key) dari dictionary LAYANAN."""
    return list(LAYANAN.keys())

def get_jasa_by_kategori(kategori):
    """Mengambil daftar jasa berdasarkan kategori yang dipilih."""
    return LAYANAN.get(kategori, [])