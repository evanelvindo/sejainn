import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.mitra import update_mitra_status

# Setup logging untuk tracking aktivitas admin
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

async def admin_mitra_decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk memproses keputusan admin (Terima/Tolak) pendaftaran mitra baru.
    Terintegrasi dengan database untuk mengubah status pendaftaran.
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # Parsing data callback. Format: 'acc_mitra_12345' atau 'dec_mitra_12345'
        data_parts = query.data.split('_')
        action = data_parts[0]  # 'acc' (Accept) atau 'dec' (Decline)
        target_user_id = int(data_parts[2])
        
        # Nama atau username admin yang memproses
        admin_info = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.full_name

        if action == "acc":
            # 1. Update status mitra di database menjadi ACTIVE
            update_mitra_status(target_user_id, "ACTIVE")
            
            # 2. Update tampilan pesan di grup log admin
            await query.edit_message_text(
                f"{query.message.text_markdown}\n\n✅ **STATUS: DISETUJUI**\n👤 Diproses Oleh: {admin_info}",
                parse_mode='Markdown'
            )
            
            # 3. Kirim notifikasi sambutan ke mitra yang baru diterima
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        "🎉 **Selamat! Pendaftaran Anda Disetujui.**\n\n"
                        "Anda sekarang resmi menjadi mitra **Sejaiin Hub**. "
                        "Silakan ketik /start untuk memuat ulang menu dan mulai menerima notifikasi order pekerjaan.\n\n"
                        "Selamat bekerja dan berikan layanan terbaik!"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Gagal mengirim notifikasi penerimaan ke user {target_user_id}: {e}")

        elif action == "dec":
            # 1. Update status mitra di database menjadi REJECTED
            update_mitra_status(target_user_id, "REJECTED")
            
            # 2. Update tampilan pesan di grup log admin
            await query.edit_message_text(
                f"{query.message.text_markdown}\n\n❌ **STATUS: DITOLAK**\n👤 Diproses Oleh: {admin_info}",
                parse_mode='Markdown'
            )
            
            # 3. Notifikasi penolakan ke calon mitra
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        "⚠️ **Informasi Pendaftaran**\n\n"
                        "Mohon maaf, pendaftaran Anda sebagai mitra Sejaiin Hub belum dapat kami setujui saat ini. "
                        "Terima kasih telah menunjukkan ketertarikan untuk bergabung."
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Gagal mengirim notifikasi penolakan ke user {target_user_id}: {e}")

    except Exception as e:
        logging.error(f"Error pada admin_mitra_decision_handler: {e}")
        await query.message.reply_text(f"❌ Terjadi kesalahan saat memproses keputusan mitra: {str(e)}")