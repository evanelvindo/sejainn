import logging
from .conn import get_db_connection

# Setup logging agar jika ada error SQL, Anda bisa melihatnya di terminal
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_services():
    """Mengambil semua daftar jasa yang tersedia."""
    conn = get_db_connection()
    if not conn:
        return []
    try:
        # Menggunakan dictionary=True agar hasil bisa diakses seperti: service['nama_layanan']
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM layanan ORDER BY nama_layanan ASC")
        return cursor.fetchall()
    except Exception as e:
        logging.error(f"Gagal mengambil daftar layanan: {e}")
        return []
    finally:
        conn.close()

def update_service_price(service_id, new_price):
    """Memperbarui harga layanan berdasarkan ID."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        # Memastikan new_price adalah float/int dan service_id adalah int
        sql = "UPDATE layanan SET harga = %s WHERE id = %s"
        cursor.execute(sql, (float(new_price), int(service_id)))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Gagal update harga layanan ID {service_id}: {e}")
        return False
    finally:
        conn.close()

def add_new_service(nama, harga, deskripsi=""):
    """Menambah layanan baru ke sistem."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        sql = "INSERT INTO layanan (nama_layanan, harga, deskripsi) VALUES (%s, %s, %s)"
        cursor.execute(sql, (str(nama), float(harga), str(deskripsi)))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Gagal menambah layanan baru: {e}")
        return False
    finally:
        conn.close()

def delete_service(service_id):
    """Menghapus layanan (Opsional: berguna untuk menu admin)."""
    conn = get_db_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM layanan WHERE id = %s", (int(service_id),))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logging.error(f"Gagal menghapus layanan: {e}")
        return False
    finally:
        conn.close()