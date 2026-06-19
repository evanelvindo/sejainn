import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import GROUP_ID, TOPIC_SUBMISSION 
from database.orders import save_bukti_kerja, get_order_details
from database.mitra import get_mitra_by_telegram_id

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

async def worker_send_bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk menerima foto bukti kerja dari Mitra dan mengirimnya ke Admin
    di topik verifikasi khusus (TOPIC_SUBMISSION).
    """
    # 1. Validasi Utama: Pastikan pesan yang masuk mengandung media foto/gambar
    if not update.message.photo:
        # Diabaikan jika pesan bukan foto agar tidak mengganggu chat berbasis teks lainnya
        return

    # 🌟 LANGKAH PERBAIKAN: Validasi Peran (Role Validation)
    # Ambil data mitra berdasarkan Telegram ID pengirim pesan
    mitra_id = update.effective_user.id
    mitra = get_mitra_by_telegram_id(mitra_id)
    
    # Jika pengirim tidak terdaftar sebagai Mitra di database sejiian_db,
    # hentikan fungsi di sini agar foto diproses oleh handler re-upload bukti transfer user
    if not mitra:
        return

    # 2. Validasi Kerja: Pastikan ada data order aktif di dalam session context milik mitra
    # Data ini tersimpan otomatis saat mitra menekan tombol 'Ambil Order'
    order_id = context.user_data.get('active_order_id')
    
    if not order_id:
        await update.message.reply_text(
            "⚠️ **Tidak Ada Order Aktif**\n\n"
            "Sistem tidak mendeteksi order yang sedang Anda kerjakan. "
            "Pastikan Anda sudah menekan tombol 'Ambil Pekerjaan' sebelum mengirimkan bukti."
        )
        return

    # 3. Ambil data detail order terkait dari database
    order = get_order_details(order_id)
    
    if not order:
        await update.message.reply_text("❌ Data order tidak ditemukan di sistem database.")
        return

    # 4. Ambil file_id foto dari server Telegram (Gunakan indeks -1 untuk resolusi tertinggi)
    photo_file = update.message.photo[-1].file_id
    
    # 5. Simpan file_id bukti kerja tersebut ke database MySQL
    try:
        # Fungsi ini akan otomatis mengubah status_order menjadi 'MENUNGGU_VERIFIKASI'
        save_bukti_kerja(order_id, photo_file)
    except Exception as e:
        logging.error(f"Gagal simpan bukti kerja Order #{order_id}: {e}")
        await update.message.reply_text(f"❌ Gagal menyimpan bukti ke database: {e}")
        return

    # Kumpulkan properti tampilan untuk diserahkan ke admin
    mitra_nama = mitra.get('nama_lengkap', update.effective_user.full_name)
    user_id_pelanggan = order.get('telegram_id_pengguna')
    
    # 6. Susun Inline Keyboard Manajemen Aksi untuk Sisi Admin
    kb_admin = [
        [
            InlineKeyboardButton("✅ Setujui", callback_data=f"verify_proof_{order_id}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"reject_proof_{order_id}")
        ],
        [
            # Pintasan komunikasi langsung via deeplinking tg://
            InlineKeyboardButton("💬 Chat Mitra", url=f"tg://user?id={mitra_id}"),
            InlineKeyboardButton("👤 Chat Pelanggan", url=f"tg://user?id={user_id_pelanggan}")
        ]
    ]
    
    # 7. Kirim data bukti fisik pekerjaan ke Grup Perusahaan di Topik SUBMISSION
    try:
        await context.bot.send_photo(
            chat_id=GROUP_ID, 
            message_thread_id=TOPIC_SUBMISSION,
            photo=photo_file,
            caption=(
                f"📸 **VERIFIKASI BUKTI KERJA**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **Order ID:** `#{order_id}`\n"
                f"👤 **Mitra:** {mitra_nama}\n"
                f"📞 **Customer ID:** `{user_id_pelanggan}`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Admin, silakan periksa bukti kerja di atas. Gunakan tombol di bawah untuk komunikasi atau konfirmasi penyelesaian."
            ),
            reply_markup=InlineKeyboardMarkup(kb_admin),
            parse_mode='Markdown'
        )
        
        # 8. Berikan respon sukses (Feedback) ke ruang obrolan pribadi Mitra
        await update.message.reply_text(
            "✅ **Bukti kerja berhasil terkirim!**\n\n"
            "Admin akan melakukan verifikasi. Anda akan menerima notifikasi jika pekerjaan ini telah disetujui (Selesai). "
            "Terima kasih atas kerja kerasnya!"
        )
        
        # Catatan: context.user_data.pop('active_order_id', None) sengaja dinonaktifkan
        # agar mitra dapat mengirim lebih dari satu foto lampiran kerja jika dibutuhkan.

    except Exception as e:
        logging.error(f"Error mengirim submission ke admin: {e}")
        await update.message.reply_text("❌ Gagal mengirim bukti ke Admin. Silakan coba kirim ulang foto.")