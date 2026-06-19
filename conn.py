import mysql.connector
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Setup path agar folder root terbaca (Absolute Path)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    # Mengambil config dari root folder
    from config import DB_CONFIG
except ImportError:
    logging.error("❌ Gagal mengimpor config.py. Pastikan file config.py ada di folder root!")
    DB_CONFIG = {}

def get_db_connection():
    """
    Membuka koneksi ke database MariaDB/MySQL.
    Menambahkan parameter autocommit agar perubahan data langsung tersimpan.
    """
    if not DB_CONFIG:
        logging.error("❌ DB_CONFIG kosong. Koneksi dibatalkan.")
        return None
        
    try:
        # Menghubungkan ke database
        conn = mysql.connector.connect(**DB_CONFIG)
        
        if conn.is_connected():
            # Opsional: Memastikan koneksi menggunakan autocommit jika diperlukan
            # conn.autocommit = True 
            return conn
            
    except mysql.connector.Error as err:
        logging.error(f"❌ Error koneksi database: {err}")
        return None
    
    return None

def get_cursor(conn, dictionary=True, buffered=True):
    """
    Helper untuk membuat cursor secara dinamis.
    - dictionary=True: Hasil query berupa dict {'kolom': 'nilai'} -> WAJIB agar nominal tidak Rp0.
    - buffered=True: Mengambil semua hasil query sekaligus agar koneksi bisa dipakai query lain.
    """
    if conn is None:
        return None
    try:
        # Default menggunakan dictionary=True agar mempermudah pengambilan harga
        return conn.cursor(dictionary=dictionary, buffered=buffered)
    except Exception as e:
        logging.error(f"❌ Gagal membuat cursor: {e}")
        return None

def check_db_health():
    """Fungsi tambahan untuk mengecek apakah DB masih hidup."""
    conn = get_db_connection()
    if conn and conn.is_connected():
        conn.close()
        return True
    return False