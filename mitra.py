import logging
from datetime import datetime
import mysql.connector
from .conn import get_db_connection

# Konfigurasi Logging agar error terpantau
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

# --- 1. PENGELOLAAN PENDAFTARAN MITRA ---

def save_registration_attempt(telegram_id, nama, no_wa, nik=None, rekening='-', foto_ktp=None):
    """
    Menyimpan atau memperbarui pendaftaran mitra. 
    Menyesuaikan dengan skema tabel mitra terbaru.
    """
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor(dictionary=True)
        
        # MySQL Syntax: Menggunakan ON DUPLICATE KEY UPDATE untuk pembaruan data jika ID sudah ada
        sql = """
            INSERT INTO mitra (telegram_id_mitra, nama_lengkap, no_whatsapp, nik, no_rekening, foto_ktp, status_verifikasi, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'MENUNGGU', %s)
            ON DUPLICATE KEY UPDATE 
                nama_lengkap = VALUES(nama_lengkap),
                no_whatsapp = VALUES(no_whatsapp),
                nik = VALUES(nik),
                no_rekening = VALUES(no_rekening),
                foto_ktp = VALUES(foto_ktp),
                status_verifikasi = 'MENUNGGU'
        """
        cursor.execute(sql, (telegram_id, nama, no_wa, nik, rekening, foto_ktp, datetime.now()))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error save_registration_attempt: {e}")
        return False
    finally:
        if conn: conn.close()

def get_pending_mitra():
    """Mengambil daftar mitra yang status verifikasinya MENUNGGU."""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mitra WHERE status_verifikasi = 'MENUNGGU'")
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error get_pending_mitra: {e}")
        return []
    finally:
        if conn: conn.close()

def approve_mitra(mitra_id):
    """
    Menyetujui pendaftaran mitra. 
    Mengubah status verifikasi menjadi DISETUJUI dan status kerja menjadi AKTIF.
    """
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = "UPDATE mitra SET status_verifikasi = 'DISETUJUI', status_kerja = 'AKTIF' WHERE id = %s"
        cursor.execute(sql, (mitra_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Error approve_mitra: {e}")
        return False
    finally:
        if conn: conn.close()

def reject_mitra(mitra_id, alasan=None):
    """Menolak pendaftaran mitra."""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = "UPDATE mitra SET status_verifikasi = 'DITOLAK' WHERE id = %s"
        cursor.execute(sql, (mitra_id,))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error reject_mitra: {e}")
        return False
    finally:
        if conn: conn.close()

# --- 2. PENGELOLAAN OPERASIONAL & STATUS ---

def update_mitra_status(telegram_id, status_kerja):
    """
    Memperbarui status kerja mitra (AKTIF, SIBUK, NONAKTIF).
    Fungsi ini WAJIB ada untuk menghilangkan ImportError di __init__.py.
    """
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        sql = "UPDATE mitra SET status_kerja = %s WHERE telegram_id_mitra = %s"
        cursor.execute(sql, (status_kerja, telegram_id))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Error update_mitra_status: {e}")
        return False
    finally:
        if conn: conn.close()

def get_eligible_workers(nama_layanan):
    """Mengambil daftar mitra yang AKTIF dan sudah DISETUJUI berdasarkan jenis layanan."""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT m.telegram_id_mitra, m.nama_lengkap 
            FROM mitra m
            JOIN mitra_layanan ml ON m.id = ml.mitra_id
            JOIN layanan l ON ml.layanan_id = l.id
            WHERE l.nama_layanan = %s 
            AND m.status_kerja = 'AKTIF' 
            AND m.status_verifikasi = 'DISETUJUI'
        """
        cursor.execute(sql, (nama_layanan,))
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error get_eligible_workers: {e}")
        return []
    finally:
        if conn: conn.close()

def assign_worker(order_id, mitra_telegram_id):
    """
    Menugaskan mitra ke order tertentu menggunakan ID dari Telegram.
    Mendukung penanganan double-click agar tidak memicu error 'Kurang Cepat'.
    """
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Ambil data order saat ini berdasarkan skema asli tabel orders
        cursor.execute("SELECT status_order, mitra_id FROM orders WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return False
            
        # 2. Cari Primary Key (id) murni mitra dari tabel mitra menggunakan telegram_id_mitra
        cursor.execute("SELECT id FROM mitra WHERE telegram_id_mitra = %s", (mitra_telegram_id,))
        mitra_data = cursor.fetchone()
        if not mitra_data:
            return False
            
        db_mitra_id = mitra_data['id']
        
        # 3. ANTISIPASI KLIK GANDA: Jika order ini ternyata sudah sukses diisi oleh ID Anda sendiri
        if order['mitra_id'] == db_mitra_id:
            return True
            
        # 4. JIKA DIAMBIL MITRA LAIN (mitra_id sudah terisi angka lain)
        if order['mitra_id'] is not None:
            return False
            
        # 5. JIKA MASIH KOSONG, PROSES PENGAMBILAN NORMAL
        sql = """
            UPDATE orders 
            SET mitra_id = %s, 
                status_order = 'KERJA' 
            WHERE id = %s AND (mitra_id IS NULL)
        """
        cursor.execute(sql, (db_mitra_id, order_id))
        conn.commit()
        
        return cursor.rowcount > 0
        
    except Exception as e:
        logging.error(f"Error assign_worker: {e}")
        return False
    finally:
        if conn: conn.close()

# --- 3. PENGAMBILAN DATA MITRA ---

def get_mitra_by_telegram_id(telegram_id):
    """Mengambil data mitra berdasarkan Telegram ID."""
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mitra WHERE telegram_id_mitra = %s", (telegram_id,))
        return cursor.fetchone()
    except Exception as e:
        logging.error(f"Error get_mitra_by_telegram_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_mitra_by_id(mitra_id):
    """Mengambil data mitra berdasarkan Primary Key (ID)."""
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mitra WHERE id = %s", (mitra_id,))
        return cursor.fetchone()
    except Exception as e:
        logging.error(f"Error get_mitra_by_id: {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_active_mitra():
    """
    Mengambil seluruh daftar mitra yang status verifikasinya 'DISETUJUI' 
    dan status kerjanya 'AKTIF' untuk broadcast pesanan baru.
    """
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        # Menyelaraskan dengan kondisi ideal penawaran kerja (Sudah lolos verifikasi & sedang aktif)
        sql = """
            SELECT telegram_id_mitra, nama_lengkap 
            FROM mitra 
            WHERE status_verifikasi = 'DISETUJUI' 
              AND status_kerja = 'AKTIF'
              AND telegram_id_mitra IS NOT NULL
        """
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error get_all_active_mitra: {e}")
        return []
    finally:
        if conn: conn.close()        