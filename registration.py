import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import GROUP_ID, TOPIC_RECRUITMENT
from database.mitra import save_registration_attempt

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

async def worker_registration_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk memproses pendaftaran mitra baru dan mengirimkan 
    notifikasi interaktif ke grup admin (Recruitment Topic).
    """
    user = update.effective_user
    
    # 1. Ekstraksi Data dari user_data (Hasil input di ConversationHandler)
    nama_pendaftar = context.user_data.get('reg_nama', user.full_name)
    wa_pendaftar = context.user_data.get('reg_wa', '')
    peminatan = context.user_data.get('reg_peminatan', 'Tidak disebutkan') # Tambahan field jika ada
    
    # Membersihkan format nomor WA agar bisa dijadikan link https://wa.me/
    clean_wa = "".join(filter(str.isdigit, wa_pendaftar))
    if clean_wa.startswith('0'):
        clean_wa = '62' + clean_wa[1:]

    # 2. Simpan Data Pendaftaran ke Database
    try:
        # Menetapkan status awal sebagai 'PENDING'
        save_registration_attempt(user.id, nama_pendaftar, wa_pendaftar)
    except Exception as e:
        logging.error(f"Error saving registration for {user.id}: {e}")

    # 3. UI Tombol Verifikasi untuk Admin
    kb_admin = [
        [
            InlineKeyboardButton("✅ Terima", callback_data=f"acc_mitra_{user.id}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"dec_mitra_{user.id}")
        ],
        [
            InlineKeyboardButton("💬 Chat via WhatsApp", url=f"https://wa.me/{clean_wa}")
        ]
    ]

    # 4. Kirim Notifikasi ke Grup Admin (Topic Recruitment)
    try:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_RECRUITMENT,
            text=(
                f"👤 **PENDAFTARAN MITRA BARU**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **User ID:** `{user.id}`\n"
                f"📛 **Nama:** {nama_pendaftar}\n"
                f"📱 **WhatsApp:** `{wa_pendaftar}`\n"
                f"🎓 **Peminatan:** {peminatan}\n\n"
                f"Admin, silakan verifikasi pendaftar ini. Anda bisa menghubungi mereka langsung via WhatsApp sebelum mengambil keputusan."
            ),
            reply_markup=InlineKeyboardMarkup(kb_admin),
            parse_mode='Markdown'
        )

        # 5. Feedback ke Calon Mitra
        # Membersihkan user_data agar tidak konflik di pendaftaran berikutnya
        context.user_data.clear()
        
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "✅ **Pendaftaran Berhasil Dikirim!**\n\n"
                "Data Anda telah masuk ke sistem kami dan sedang dalam tahap peninjauan oleh tim admin Sejaiin Hub.\n\n"
                "Kami akan mengirimkan notifikasi di sini segera setelah status pendaftaran Anda diperbarui. Mohon pastikan WhatsApp Anda aktif."
            ),
            parse_mode='Markdown'
        )

    except Exception as e:
        logging.error(f"Error sending registration notification: {e}")
        if update.effective_message:
            await update.effective_message.reply_text("❌ Terjadi gangguan pada sistem pendaftaran. Silakan coba lagi nanti.")