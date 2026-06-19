import logging
from datetime import datetime
from .conn import get_db_connection, get_cursor  # Mengambil fungsi koneksi pusat

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

# --- 1. PENGELOLAAN PESANAN (ORDERS) ---

def get_order_details(order_id):
    """
    Mengambil detail order lengkap menggunakan ID (MySQL).
    Menggunakan get_cursor agar otomatis bertipe dictionary=True & buffered=True.
    """
    conn = get_db_connection()
    if not conn: 
        return None
    
    cursor = get_cursor(conn)
    if not cursor: 
        conn.close()
        return None
        
    try:
        cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        return cursor.fetchone()
    except Exception as e:
        logging.error(f"Error get_order_details: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
    
def create_order(telegram_id, nama_layanan, lokasi, no_wa_user, uang_titipan=0.0):
    """
    Membuat order baru dengan mengambil harga otomatis dari tabel layanan
    dan menyimpan deposit uang titipan jika ada (Sistem Escrow).
    """
    conn = get_db_connection()
    if not conn: 
        return None, 0.0
        
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True, buffered=True)
        
        # 1. Ambil harga layanan murni dari database
        cursor.execute("SELECT harga FROM layanan WHERE nama_layanan = %s", (nama_layanan,))
        result = cursor.fetchone()
        
        if result:
            raw_harga = result.get('harga') if isinstance(result, dict) else result[0]
            harga = float(raw_harga) if raw_harga is not None else 0.0
        else:
            harga = 0.0
            logging.warning(f"⚠️ Layanan '{nama_layanan}' tidak ditemukan harganya di tabel layanan.")

        # 2. Insert order baru dengan kolom uang_titipan dan status 'PROSES'
        sql = """
            INSERT INTO orders 
            (telegram_id_pengguna, jenis_jasa, lokasi_pengguna, no_whatsapp_user, harga_final, uang_titipan, status_order, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, 'PROSES', NOW(), NOW())
        """
        
        cursor.execute(sql, (telegram_id, nama_layanan, lokasi, no_wa_user, harga, float(uang_titipan)))
        conn.commit()
        
        order_id = cursor.lastrowid
        logging.info(f"✅ Berhasil buat order #{order_id} | Harga Jasa: Rp{harga:,.0f} | Uang Titipan: Rp{float(uang_titipan):,.0f}")
        return order_id, harga

    except Exception as e:
        if conn: conn.rollback()
        logging.error(f"❌ Error create_order: {e}")
        return None, 0.0
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_order_status(order_id, status):
    """
    Mengupdate status pesanan di database MySQL.
    Mengembalikan True jika berhasil, False jika gagal.
    """
    conn = get_db_connection()
    if not conn:
        logging.error("Gagal update status: Koneksi database tidak tersedia.")
        return False
        
    cursor = None
    try:
        cursor = conn.cursor()
        sql = "UPDATE orders SET status_order = %s WHERE id = %s"
        cursor.execute(sql, (status, order_id))
        conn.commit()
        
        if cursor.rowcount >= 0:
            logging.info(f"Status Order #{order_id} berhasil diupdate menjadi {status} (Affected rows: {cursor.rowcount})")
            return True
        else:
            logging.warning(f"Order #{order_id} tidak ditemukan di database.")
            return False
    except Exception as e:
        if conn: conn.rollback()
        logging.error(f"DB Error saat update_order_status: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def save_bukti_kerja(order_id, file_id):
    """Menyimpan file_id foto bukti kerja dan ubah status ke MENUNGGU_VERIFIKASI."""
    conn = get_db_connection()
    if not conn: return False
    cursor = None
    try:
        cursor = conn.cursor()
        sql = "UPDATE orders SET bukti_kerja = %s, status_order = 'MENUNGGU_VERIFIKASI' WHERE id = %s"
        cursor.execute(sql, (file_id, order_id))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error save_bukti_kerja: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- 2. PENGELOLAAN KEUANGAN (PAYOUTS) & SALES ---

def get_sales_data():
    """Mengambil seluruh detail baris data keuangan dari tabel payouts."""
    conn = get_db_connection()
    if not conn: 
        return []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT 
                id,
                order_id, 
                total_bayar as harga_final, 
                keuntungan_admin,
                gaji_mitra,
                status_bayar,
                created_at
            FROM payouts 
            ORDER BY order_id DESC
        """
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error get_sales_data: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def update_payout_status(order_id, status='PAID'):
    """
    Memperbarui status pembayaran pada tabel payouts dan orders secara sinkron.
    """
    conn = get_db_connection()
    if not conn: return False
    cursor = None
    try:
        cursor = conn.cursor()
        sql_payout = "UPDATE payouts SET status_bayar = %s WHERE order_id = %s"
        cursor.execute(sql_payout, (status, order_id))
        
        if status == 'PAID':
            sql_order = "UPDATE orders SET status_order = 'SELESAI' WHERE id = %s"
            cursor.execute(sql_order, (order_id,))
        elif status in ['REJECTED', 'BATAL']:
            sql_order = "UPDATE orders SET status_order = 'BATAL' WHERE id = %s"
            cursor.execute(sql_order, (order_id,))
            
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error update_payout_status: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def save_finance_report(order_id, total_bayar, keuntungan_admin, gaji_mitra):
    """
    Menyimpan data ke tabel payouts secara aman berdasarkan kolom murni database (mitra_id).
    """
    conn = get_db_connection()
    if not conn: 
        print("❌ [DATABASE] Gagal membuat koneksi ke database MySQL.")
        return False
        
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. Ambil data order untuk mendapatkan mitra_id murni
        cursor.execute("SELECT mitra_id FROM orders WHERE id = %s", (order_id,))
        order_data = cursor.fetchone()
        
        if not order_data:
            print(f"❌ [DB WARNING] Order #{order_id} tidak ditemukan di database.")
            return False
            
        m_id = order_data.get('mitra_id')

        if not m_id:
            print(f"❌ [DB WARNING] Gagal simpan payout: Order #{order_id} tidak memiliki mitra_id!")
            return False

        print(f"🚀 [DB DEBUG] Menemukan ID Mitra: {m_id} untuk Order #{order_id}. Mencoba melakukan INSERT...")

        # 2. INSERT ke tabel payouts sesuai skema asli
        sql = """
            INSERT INTO payouts (order_id, mitra_id, total_bayar, gaji_mitra, keuntungan_admin, status_bayar)
            VALUES (%s, %s, %s, %s, %s, 'PENDING')
        """
        
        params = (int(order_id), int(m_id), float(total_bayar), float(gaji_mitra), float(keuntungan_admin))
        cursor.execute(sql, params)
        conn.commit()
        
        print(f"✅ [DB SUCCESS] Data berhasil disimpan ke tabel payouts untuk Order #{order_id}!")
        return True
        
    except Exception as e:
        print(f"❌ [DB CRASH] Terjadi error pada fungsi save_finance_report: {e}")
        if conn: conn.rollback()
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- 3. FUNGSI KHUSUS DASHBOARD ADMIN ---

def get_active_orders():
    """Mengambil semua order yang sedang berjalan untuk Dashboard Admin."""
    conn = get_db_connection()
    if not conn: return []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM orders WHERE status_order NOT IN ('SELESAI', 'BATAL') ORDER BY created_at DESC"
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error get_active_orders: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_pending_payouts():
    """Mengambil daftar pembayaran yang masih tertunda (PENDING)."""
    conn = get_db_connection()
    if not conn: return []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT p.*, m.nama_lengkap, o.jenis_jasa 
            FROM payouts p
            JOIN mitra m ON p.mitra_id = m.id
            JOIN orders o ON p.order_id = o.id
            WHERE p.status_bayar = 'PENDING'
        """
        cursor.execute(sql)
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error get_pending_payouts: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def get_all_services():
    """Mengambil semua daftar layanan dari tabel layanan."""
    conn = get_db_connection()
    if not conn: return []
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM layanan ORDER BY kategori ASC")
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error get_all_services: {e}")
        return []
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- 4. PEMELIHARAAN SISTEM, REVIEW & REPORT ---

def save_report(order_id, telegram_id, alasan):
    """
    Menyimpan laporan kendala/komplain dari user ke tabel reports.
    Disesuaikan dengan kolom skema: pelapor_id & pesan.
    """
    conn = get_db_connection()
    if not conn: return False
    cursor = None
    try:
        cursor = conn.cursor()
        # Perbaikan kolom agar pas dengan skema: pelapor_id, pesan
        sql = "INSERT INTO reports (order_id, pelapor_id, pesan) VALUES (%s, %s, %s)"
        cursor.execute(sql, (order_id, telegram_id, alasan))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error save_report: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def save_review(order_id, mitra_id, rating, ulasan):
    """Menyimpan rating ke tabel reviews."""
    if not mitra_id:
        logging.error(f"Gagal simpan review: mitra_id untuk Order #{order_id} null.")
        return False

    conn = get_db_connection()
    if not conn: 
        return False
    cursor = None
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO reviews (order_id, mitra_id, rating, ulasan) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (order_id, mitra_id, rating, ulasan))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error SQL save_review: {e}")
        return False
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def auto_complete_orders():
    """
    Proses otomatis menutup order pesanan dengan status 'MENUNGGU_VERIFIKASI' 
    yang lebih dari 24 jam menjadi 'SELESAI'.
    """
    conn = get_db_connection()
    if not conn: return
        
    cursor = None
    try:
        cursor = conn.cursor()
        sql = """
            UPDATE orders 
            SET status_order = 'SELESAI' 
            WHERE status_order = 'MENUNGGU_VERIFIKASI' 
            AND updated_at < NOW() - INTERVAL 24 HOUR
        """
        cursor.execute(sql)
        conn.commit()
        
        if cursor.rowcount > 0:
            logging.info(f"Auto-Complete: Berhasil menutup {cursor.rowcount} pesanan kadaluarsa.")
            
    except Exception as e:
        if conn: conn.rollback()
        logging.error(f"Error pada auto_complete_orders: {e}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()