"""
File Backend Web Portal & Landing Page Rekrutmen SEJAIIN HUB.
Mengelola pendaftaran mitra baru via web dan sinkronisasi notifikasi ke Telegram Bot.
Last Update: 2026-06-16 (Fixing Input Handling Validation - Multi-field Strict Bounds)
"""

import os
import sys
import logging
from datetime import datetime
import httpx
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Path Handling ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    # Memastikan modul bot & konfigurasi global terdeteksi
    from bot.database.conn import get_db_connection
    from config import TOKEN, GROUP_ID, TOPIC_RECRUITMENT 
except ImportError as e:
    logger.error(f"Gagal mengimpor modul internal bot/config: {e}")
    sys.exit(1)

# --- Inisialisasi Flask ---
app = Flask(__name__, template_folder='templates')

# --- Konfigurasi Upload Berkas KTP ---
UPLOAD_FOLDER = os.path.join(current_dir, 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Variabel Statis Konten Landing Page (Diselaraskan ke Sejaiin Hub) ---
LANGKAH = [
    {"nomor": "01", "judul": "Pilih Kategori Jasa", "deskripsi": "Cari sub-layanan Jastip, Digital IT, atau Domestik Kos yang Anda butuhkan di katalog.", "ikon": "🔍"},
    {"nomor": "02", "judul": "Isi Form / Order Bot", "deskripsi": "Lakukan pemesanan cepat lewat formulir web atau langsung berinteraksi dengan Telegram Bot.", "ikon": "🤖"},
    {"nomor": "03", "judul": "Proses & Escrow System", "deskripsi": "Dana aman di sistem penampungan sementara selagi mitra mahasiswa memproses pesanan Anda.", "ikon": "🛡️"},
    {"nomor": "04", "judul": "Selesai Transaksi", "deskripsi": "Konfirmasi penyelesaian tugas, dana diteruskan ke mitra, dan berikan penilaian bintang Anda.", "ikon": "⭐"}
]

KEUNGGULAN = [
    {"judul": "Tarif Jasa Flat", "deskripsi": "Skema biaya transparan dan terjangkau, disesuaikan dengan kantong mahasiswa.", "ikon": "💰"},
    {"judul": "Mitra Internal Kampus", "deskripsi": "Semua kurir dan teknisi adalah mahasiswa aktif yang divalidasi berkas identitasnya.", "ikon": "🎓"},
    {"judul": "Sistem Escrow Aman", "deskripsi": "Uang titipan belanja aman. Pencairan komisi transparan menggunakan bagi hasil 90:10.", "ikon": "🔒"},
    {"judul": "Otomatisasi Bot", "deskripsi": "Notifikasi pengerjaan, assignment mitra, dan status order dikirim real-time via Telegram.", "ikon": "⚡"}
]

MITRA_BENEFITS = [
    {"judul": "Bagi Hasil 90%", "deskripsi": "Raih pendapatan lebih tinggi dengan hak retensi upah murni 90% utuh milik Anda.", "ikon": "💵"},
    {"judul": "Waktu Sangat Fleksibel", "deskripsi": "Bebas ambil orderan tugas atau jastip di sela-sela jam kosong kuliah Anda.", "ikon": "📅"},
    {"judul": "Modal Titipan Aman", "deskripsi": "Uang belanja jastip dicairkan di awal oleh sistem setelah divalidasi admin.", "ikon": "💼"},
    {"judul": "Portofolio Pengalaman", "deskripsi": "Asah skill teknis IT atau operasional logistik langsung di lapangan nyata.", "ikon": "🚀"}
]

# --- Helper Functions ---
def allowed_file(filename):
    """Validasi ekstensi file gambar KTP."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_whatsapp_number(phone_number):
    """Normalisasi format nomor HP/WA ke kode internasional 62."""
    if not phone_number: 
        return ""
    num = "".join(filter(str.isdigit, str(phone_number)))
    if num.startswith('08'): 
        return '62' + num[1:]
    elif num.startswith('8'): 
        return '62' + num
    return num 

# --- Routes Area ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Menyajikan file KTP yang diunggah secara aman."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    """Render Landing Page utama dengan daftar layanan dinamis dari Database."""
    tahun = datetime.now().year
    conn = get_db_connection()
    daftar_layanan = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, kategori, nama_layanan, harga, deskripsi FROM layanan")
            daftar_layanan = cursor.fetchall()
        except Exception as e:
            logger.error(f"Gagal mengambil katalog layanan: {e}")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        'index.html',
        layanan=daftar_layanan,
        langkah=LANGKAH,
        keunggulan=KEUNGGULAN,
        mitra_benefits=MITRA_BENEFITS,
        tahun=tahun
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Endpoint pendaftaran mitra baru via Form HTML (Multipart-form)."""
    conn = get_db_connection()
    daftar_layanan = []

    # Ambil data layanan terlebih dahulu agar drop-down form tidak pernah kosong
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id, kategori, nama_layanan FROM layanan")
            daftar_layanan = cursor.fetchall()
        except Exception as e:
            logger.error(f"Gagal memuat drop-down layanan: {e}")
        finally:
            if not request.method == 'POST':
                cursor.close()
                conn.close()

    # Jika user hanya mengakses halaman pendaftaran (bukan submit form)
    if request.method == 'GET':
        return render_template('register.html', layanan=daftar_layanan)

    # Pemrosesan Form Data (POST)
    cursor = None
    nama_layanan_terpilih = "Tidak Diketahui"
    
    try:
        # 1. Ambil Data Form Pendaftaran & Lakukan Kebersihan Spasi Mentah (.strip())
        nama = request.form.get('nama_lengkap', '').strip()
        nik = request.form.get('nik', '').strip()
        no_wa_raw = request.form.get('no_whatsapp', '').strip()
        no_rek = request.form.get('no_rekening', '').strip()
        t_id = request.form.get('telegram_id_mitra', '').strip()
        layanan_id = request.form.get('layanan_id')

        # 🌟 2. VALIDASI BERLAPIS BACKEND (Penyaringan Karakter Senormalnya)
        if not nama or len(nama) > 50:
            return render_template('register.html', layanan=daftar_layanan, error_pesan="❌ Nama tidak valid! Maksimal panjang adalah 50 karakter.")
            
        if len(nik) != 16 or not nik.isdigit():
            return render_template('register.html', layanan=daftar_layanan, error_pesan="❌ NIK tidak valid! Harus tepat berjumlah 16 digit angka numerik.")
            
        if not (10 <= len(no_rek) <= 20) or not no_rek.isdigit():
            return render_template('register.html', layanan=daftar_layanan, error_pesan="❌ Nomor Rekening tidak valid! Harus berupa 10 hingga 20 digit angka.")
            
        if not (10 <= len(no_wa_raw) <= 15) or not no_wa_raw.startswith('08') or not no_wa_raw.isdigit():
            return render_template('register.html', layanan=daftar_layanan, error_pesan="❌ Nomor WhatsApp tidak valid! Gunakan format angka diawali '08' (10-15 digit).")
            
        if not (7 <= len(t_id) <= 12) or not t_id.isdigit():
            return render_template('register.html', layanan=daftar_layanan, error_pesan="❌ Telegram ID tidak valid! Harus berupa susunan 7 hingga 12 digit angka numerik.")

        # Normalisasi nomor setelah dipastikan lolos saringan regex string dasar
        wa = format_whatsapp_number(no_wa_raw)

        # 3. Validasi File Upload Foto KTP
        if 'ktp_foto' not in request.files:
            return render_template('register.html', layanan=daftar_layanan, error_pesan="❌ Berkas visual KTP tidak ditemukan.")
            
        file = request.files['ktp_foto']
        if file.filename == '' or not allowed_file(file.filename):
            return render_template('register.html', layanan=daftar_layanan, error_pesan="❌ Format berkas salah! Hanya diizinkan dokumen gambar (.png/.jpg/.jpeg).")

        # Amankan nama berkas simpanan fisik
        filename = secure_filename(f"{nik}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # 4. Operasi Transaksional Pangkalan Data
        if not conn or not conn.is_connected():
            conn = get_db_connection()
            
        cursor = conn.cursor(dictionary=True)
        
        # Ambil nama spesialisasi layanan untuk pelaporan teks notifikasi
        if layanan_id:
            cursor.execute("SELECT nama_layanan FROM layanan WHERE id = %s", (layanan_id,))
            res_layanan = cursor.fetchone()
            if res_layanan:
                nama_layanan_terpilih = res_layanan['nama_layanan']

        # Jalankan Query Insert ke master tabel mitra
        sql_mitra = """
            INSERT INTO mitra (nama_lengkap, nik, no_whatsapp, no_rekening, telegram_id_mitra, foto_ktp, status_kerja, status_verifikasi) 
            VALUES (%s, %s, %s, %s, %s, %s, 'NONAKTIF', 'MENUNGGU')
        """
        cursor.execute(sql_mitra, (nama, nik, wa, no_rek, t_id, filename))
        mitra_id = cursor.lastrowid
        
        # Hubungkan ke tabel relasi mitra_layanan
        if layanan_id:
            sql_layanan = "INSERT INTO mitra_layanan (mitra_id, layanan_id) VALUES (%s, %s)"
            cursor.execute(sql_layanan, (mitra_id, layanan_id))
        
        conn.commit()
        logger.info(f"Pendaftaran berhasil disimpan ke DB untuk NIK: {nik}")

        
        # 5. Pengiriman Payload Berkas Foto KTP + Detail Mitra ke Telegram Admin Thread via sendPhoto
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            
            # Memformat teks detail agar sesuai dengan template Admin Panel pada gambar Anda
            caption_text = (
                "📋 **DETAIL CALON MITRA**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Nama:** {nama}\n"
                f"🆔 **NIK:** `{nik}`\n"
                f"📱 **WhatsApp:** `{wa}` [Hubungi](https://wa.me/{wa})\n"
                f"🏦 **No. Rekening:** `{no_rek}`\n"
                f"🛠️ **Spesialisasi:** *{nama_layanan_terpilih}*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ *Silakan tentukan verifikasi untuk mitra ini melalui panel admin bot.*"
            )
            
            # Menyiapkan payload data teks parameter Telegram
            data_payload = {
                "chat_id": GROUP_ID,
                "message_thread_id": TOPIC_RECRUITMENT,
                "parse_mode": "Markdown",
                "caption": caption_text
            }
            
            # Membuka berkas gambar KTP secara aman (read-binary) untuk dikirim ke API
            with open(file_path, 'rb') as photo_file:
                files_payload = {
                    'photo': photo_file
                }
                
                # Menggunakan httpx dengan skema multipart data (kombinasi data & files)
                with httpx.Client() as client:
                    response = client.post(
                        url, 
                        data=data_payload, 
                        files=files_payload, 
                        timeout=10.0  # Timeout dinaikkan menjadi 10 detik karena proses upload gambar butuh waktu lebih lama
                    )
                    
                    # Memastikan response sukses (jika error akan melempar exception ke block target)
                    response.raise_for_status()
                
        except Exception as bot_e:
            logger.error(f"Gagal mengirim berkas visual KTP & Notif ke API Telegram: {bot_e}")

        # Merender kembali form utuh dengan alert sukses tanpa menghilangkan elemen input
        return render_template(
            'register.html', 
            layanan=daftar_layanan, 
            sukses_pesan="Pendaftaran Berhasil! Data dan berkas KTP Anda sedang diperiksa oleh Admin."
        )

    except Exception as e:
        logger.error(f"Register Error: {e}")
        if conn:
            conn.rollback()
        return render_template('register.html', layanan=daftar_layanan, error_pesan=f"❌ Terjadi kesalahan sistem: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

# --- Endpoint API Opsional untuk Aksi Klien (AJAX) ---
@app.route('/pesan', methods=['POST'])
def pesan():
    """Menerima pesanan cepat via pemicu tombol website."""
    data = request.get_json() or {}
    nama = data.get('nama', '')
    layanan = data.get('layanan', '')
    alamat = data.get('alamat', '')
    telepon = data.get('telepon', '')

    if not all([nama, layanan, alamat, telepon]):
        return jsonify({'success': False, 'pesan': 'Semua field wajib diisi!'}), 400

    return jsonify({
        'success': True,
        'pesan': f'Terima kasih {nama}! Pesanan {layanan} Anda telah diterima. Tim kami akan segera menghubungi Anda.'
    })

if __name__ == '__main__':
    # Berjalan di port 5000 sesuai standarisasi workspace environment
    app.run(debug=True, port=5000)