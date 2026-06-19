import logging
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config import GROUP_ID, TOPIC_REPORT, TOPIC_REKOMENDASI, TOPIC_FINANCE

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

# 🌟 PEMBARUAN STATE: Tambahkan REUPLOAD_PROOF ke dalam jajaran state angka
REPORT, RECOM, REUPLOAD_PROOF = range(3)

# --- REFRESH ---
async def refresh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menampilkan kembali menu utama. Mengarahkan user kembali ke fungsi start
    untuk memuat ulang keyboard menu sesuai role mereka.
    """
    from handlers.conversation import start
    await start(update, context) 

# --- LAPORAN MASALAH ---
async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur penginputan laporan masalah."""
    await update.message.reply_text(
        "📝 **Pusat Laporan Masalah**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Silakan tuliskan keluhan atau masalah yang Anda alami secara detail.\n\n"
        " Contoh: _'Pembayaran saya belum diverifikasi meskipun sudah kirim bukti.'_\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    return REPORT

async def report_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim isi laporan ke grup admin dan mengakhiri state."""
    user = update.effective_user
    isi_laporan = update.message.text
    
    try:
        await context.bot.send_message(
            chat_id=GROUP_ID, 
            message_thread_id=TOPIC_REPORT,
            text=(
                f"⚠️ **LAPORAN MASALAH BARU**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Dari:** {user.full_name} (@{user.username})\n"
                f"🆔 **ID:** `{user.id}`\n"
                f"📝 **Pesan:**\n\n{isi_laporan}"
            ),
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ **Laporan Terkirim.**\n\nAdmin akan segera meninjau laporan Anda. Terima kasih atas laporannya!")
    except Exception as e:
        logging.error(f"Gagal mengirim laporan dari {user.id}: {e}")
        await update.message.reply_text("❌ **Gagal mengirim laporan.**\nSilakan coba lagi nanti atau hubungi admin langsung.")
        
    return ConversationHandler.END

# --- REKOMENDASI JASA ---
async def recom_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Memulai alur penginputan rekomendasi jasa baru."""
    await update.message.reply_text(
        "💡 **Saran & Rekomendasi Jasa**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Punya ide jasa baru yang dibutuhkan mahasiswa? Tuliskan ide Anda di sini!\n\n"
        "Ketik /cancel untuk membatalkan."
    )
    return RECOM

async def recom_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengirim isi rekomendasi ke grup admin dan mengakhiri state."""
    user = update.effective_user
    isi_rekom = update.message.text
    
    try:
        await context.bot.send_message(
            chat_id=GROUP_ID, 
            message_thread_id=TOPIC_REKOMENDASI,
            text=(
                f"💡 **REKOMENDASI JASA BARU**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Dari:** {user.full_name} (@{user.username})\n"
                f"🆔 **ID:** `{user.id}`\n"
                f"📝 **Rekomendasi:**\n\n{isi_rekom}"
            ),
            parse_mode='Markdown'
        )
        await update.message.reply_text("✅ **Saran Diterima.**\n\nTerika kasih! Rekomendasi Anda sangat berharga bagi pengembangan Sejaiin ke depan.")
    except Exception as e:
        logging.error(f"Gagal mengirim rekomendasi dari {user.id}: {e}")
        await update.message.reply_text("❌ Gagal mengirim rekomendasi.")

    return ConversationHandler.END


# =====================================================================
# 🌟 FITUR TAMBAHAN: HANDLER RE-UPLOAD BUKTI TRANSAKSI PELANGGAN
# =====================================================================

async def handle_reupload_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil saat user klik '🔄 Kirim Ulang Bukti Transaksi'."""
    order_id = context.user_data.get('reupload_order_id')
    
    if not order_id:
        await update.message.reply_text(
            "⚠️ **Sesi Pengiriman Ulang Kedaluwarsa**\n\n"
            "Sistem tidak menemukan ID pesanan aktif untuk di-upload ulang.\n"
            "Silakan ketik /start untuk memuat ulang menu atau hubungi Admin."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"📸 **Sistem Siap Menerima Bukti Baru**\n\n"
        f"Silakan kirimkan **foto bukti transfer terbaru** Anda di sini untuk Order **#{order_id}**.\n"
        f"Admin Finansial akan segera memeriksa kembali mutasi setelah foto masuk.",
        reply_markup=ReplyKeyboardRemove() # Sembunyikan keyboard agar user fokus kirim foto
    )
    return REUPLOAD_PROOF


async def process_reuploaded_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangkap foto bukti transfer baru dan mengirimkannya ke ruang obrolan Admin Finance."""
    if not update.message.photo:
        await update.message.reply_text("⚠️ Mohon kirimkan dokumen dalam bentuk **Gambar/Foto**, bukan teks.")
        return REUPLOAD_PROOF

    order_id = context.user_data.get('reupload_order_id')
    photo_file_id = update.message.photo[-1].file_id  

    try:
        from database.orders import update_order_status
        # Kembalikan status ke VERIFIKASI_ADMIN di database agar divalidasi ulang oleh admin keuangan
        success = update_order_status(order_id, 'VERIFIKASI_ADMIN')
        
        if success:
            kb_admin = [
                [
                    InlineKeyboardButton("✅ Verifikasi & Broadcast", callback_data=f"verify_{order_id}"),
                    InlineKeyboardButton("❌ Tolak Bukti", callback_data=f"reject_transfer_{order_id}")
                ]
            ]
            
            # Kirim kembali foto bukti baru tersebut langsung ke grup Admin Finansial (TOPIC_FINANCE)
            await context.bot.send_photo(
                chat_id=GROUP_ID,
                message_thread_id=TOPIC_FINANCE,
                photo=photo_file_id,
                caption=(
                    f"🔄 **BUKTI PEMBAYARAN DI-RESUBMIT (KIRIM ULANG)**\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 **Order:** #{order_id}\n"
                    f"👤 **Pelanggan:** {update.effective_user.full_name} (@{update.effective_user.username if update.effective_user.username else 'NoUsername'})\n"
                    f"🔑 **ID Telegram:** `{update.effective_user.id}`\n\n"
                    f"👉 *Silakan periksa mutasi bank Anda kembali, kemudian tentukan tindakan.*"
                ),
                reply_markup=InlineKeyboardMarkup(kb_admin),
                parse_mode='Markdown'
            )
            
            # Beri umpan balik ke obrolan pelanggan dan kembalikan tombol menu utama
            await update.message.reply_text(
                "✅ **Bukti transfer berhasil dikirim ulang!**\n\n"
                "Pesanan Anda saat ini telah kembali masuk antrean verifikasi Admin. Mohon tunggu prosesnya.",
                reply_markup=ReplyKeyboardMarkup([["🔄 Refresh"]], resize_keyboard=True)
            )
            
            # Bersihkan tanda ID order di sesi memory RAM
            context.user_data.pop('reupload_order_id', None)
            return ConversationHandler.END
            
        else:
            await update.message.reply_text("❌ Gagal memperbarui status order di database. Silakan hubungi admin.")
            return REUPLOAD_PROOF
            
    except Exception as e:
        logging.error(f"Error reupload: {e}")
        await update.message.reply_text(f"❌ Terjadi kesalahan sistem internal: {e}")
        return ConversationHandler.END