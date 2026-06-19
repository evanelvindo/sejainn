# bot/config.py

# Token & ID Admin
TOKEN = "8692863295:AAH1fiVc7s2HF_U0LEqrM1A5J2VA3a4MTcA"
ADMIN_ID = 1453357152  # Pastikan ini angka tanpa tanda kutip

# --- Konfigurasi Grup & Topik ---
# Gunakan 1 ID Grup utama untuk semua notifikasi
GROUP_ID = -1003757508319 # Pastikan berupa integer

# --- PEMBAGIAN TOPIK (Routing) ---
# 1. Rekrutmen & Umum
TOPIC_RECRUITMENT = 166 

# 2. Finance (Keuangan)
TOPIC_FINANCE = 168          # Notifikasi bukti bayar dari User
TOPIC_PAYOUT = 170           # Khusus bukti transfer admin ke mitra (payout)

# 3. Services (Layanan)
TOPIC_SERVICES = 172         # Broadcast Order baru (Pending)
TOPIC_ORDER_TAKEN = 174      # Notifikasi saat mitra mengambil order
TOPIC_SUBMISSION = 176       # Verifikasi bukti kerja mitra (foto kerja)

# 4. User Interaction
# Diselaraskan menjadi TOPIC_REPORT agar sesuai dengan import di handlers/user/report.py
TOPIC_REPORT = 178          
TOPIC_REKOMENDASI = 180    

# --- Database Configuration ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',          # Sesuaikan jika Anda menggunakan password database
    'database': 'sejaiin_db',
    'port': 3307             # Port XAMPP MariaDB/MySQL
}

# Profit Margin Admin (10%)
PROFIT_MARGIN = 0.10

# Pesan Pembayaran
PAYMENT_INFO = (
    "💳 **Pembayaran Sejaiin**\n\n"
    "Silakan transfer total biaya ke rekening berikut:\n\n"
    "BANK: BCA\n"
    "NO REK: 1234567890\n"
    "A.N: SEJAIIN OFFICIAL\n\n"
    "Setelah transfer, mohon kirimkan **foto bukti transfer** di chat ini."
)