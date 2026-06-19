import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import GROUP_ID, TOPIC_REPORT

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

async def user_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk menerima laporan masalah dari pengguna dan 
    meneruskannya ke grup admin dengan link chat langsung.
    """
    user = update.effective_user
    
    # Pastikan pesan mengandung teks
    if not update.message or not update.message.text:
        return

    # Menghapus command /report jika ada (opsional, tergantung cara panggil)
    report_text = update.message.text.replace('/report', '').strip()
    
    # Jika dipanggil via menu "⚠️ Laporkan Masalah", teks biasanya murni isi laporan
    if not report_text or report_text == "⚠️ Laporkan Masalah":
        await update.message.reply_text(
            "📝 **Silakan kirimkan laporan Anda.**\n\n"
            "Tuliskan masalah atau kendala yang Anda alami secara detail dalam satu pesan ini.",
            parse_mode='Markdown'
        )
        return

    # Validasi panjang pesan agar laporan cukup informatif
    if len(report_text) < 10:
        await update.message.reply_text(
            "⚠️ **Laporan Terlalu Singkat**\n\n"
            "Mohon jelaskan masalah Anda dengan lebih detail agar admin dapat membantu."
        )
        return

    # 1. Identitas Pelapor
    user_id = user.id
    user_name = user.full_name
    username = f"@{user.username}" if user.username else "Tidak ada username"

    # 2. UI Tombol untuk Admin
    kb_admin = [
        [
            # Link chat langsung menggunakan protocol tg://user?id=
            InlineKeyboardButton("💬 Chat Pengguna", url=f"tg://user?id={user_id}")
        ],
        [
            InlineKeyboardButton("✅ Tandai Selesai", callback_data=f"resolve_report_{user_id}")
        ]
    ]

    # 3. Kirim ke Grup Admin (Topik Laporan Masalah)
    try:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_REPORT,
            text=(
                f"⚠️ **LAPORAN MASALAH BARU**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Dari:** {user_name} ({username})\n"
                f"🆔 **User ID:** `{user_id}`\n\n"
                f"📝 **Isi Laporan:**\n_{report_text}_\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Admin silakan hubungi pengguna melalui tombol di bawah jika diperlukan."
            ),
            reply_markup=InlineKeyboardMarkup(kb_admin),
            parse_mode='Markdown'
        )

        # 4. Feedback ke Pengguna
        await update.message.reply_text(
            "✅ **Laporan Berhasil Terkirim**\n\n"
            "Admin telah menerima laporan Anda dan akan segera meninjau masalah tersebut. "
            "Terima kasih atas laporannya."
        )

    except Exception as e:
        logging.error(f"Error sending report: {e}")
        await update.message.reply_text("❌ Gagal mengirim laporan ke sistem. Silakan coba lagi nanti.")

async def admin_resolve_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk memproses tombol 'Tandai Selesai' di sisi admin.
    Fungsi ini akan memperbarui pesan di grup admin sebagai tanda laporan selesai.
    """
    query = update.callback_query
    await query.answer("Laporan ditandai sebagai selesai.")
    
    # Ambil info admin yang memproses
    admin_name = query.from_user.full_name
    
    # Update pesan laporan di grup agar admin lain tahu sudah ditangani
    try:
        await query.edit_message_text(
            f"{query.message.text_markdown}\n\n✅ **STATUS: SELESAI DITANGANI**\n👤 Oleh Admin: {admin_name}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Error updating report status: {e}")