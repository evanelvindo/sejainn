"""
File handler Modular untuk Manajemen Layanan (Service Operations) di sisi Admin.
Mengatur perubahan harga layanan secara instan menggunakan command teks.
Last Update: 2026-06-17 (Fix Markdown Syntax, HTML Mode Alignment, and Thread Awareness)
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from handlers.admin.dashboard import is_admin
from database.services import update_service_price

# Setup logging
logger = logging.getLogger(__name__)

def escape_html(text):
    """Mengamankan teks dari karakter khusus HTML agar Telegram tidak crash."""
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def edit_harga_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler untuk perintah /edit_harga [ID] [HARGA].
    Memungkinkan admin mengubah harga layanan secara instan melalui chat.
    """
    # Pastikan pesan valid dan bukan dari channel/system kosong
    if not update.message:
        return

    user_id = update.effective_user.id
    message_thread_id = update.message.message_thread_id

    # 1. Validasi Keamanan: Cek apakah user adalah Admin
    if not is_admin(user_id):
        logger.warning(f"Akses ditolak: User {user_id} mencoba menggunakan /edit_harga.")
        return

    # 2. Validasi Input Argumen
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "⚠️ <b>Format Salah!</b>\n\n"
            "Gunakan format: <code>/edit_harga [ID_Layanan] [Harga_Baru]</code>\n"
            "Contoh: <code>/edit_harga 1 75000</code>",
            parse_mode='HTML',
            message_thread_id=message_thread_id
        )
        return
    
    id_layanan = args[0]
    harga_raw = args[1]

    # 3. Validasi Tipe Data & Keamanan Nilai Harga
    if not harga_raw.isdigit():
        await update.message.reply_text(
            "⚠️ <b>Error:</b> Harga harus berupa angka bulat positif tanpa titik atau koma (Contoh: 50000).",
            parse_mode='HTML',
            message_thread_id=message_thread_id
        )
        return
    
    try:
        service_id = int(id_layanan)
        new_price = float(harga_raw)
        
        if new_price <= 0:
            await update.message.reply_text(
                "⚠️ <b>Error:</b> Harga baru harus lebih besar dari Rp0.",
                parse_mode='HTML',
                message_thread_id=message_thread_id
            )
            return
            
    except ValueError:
        await update.message.reply_text(
            "⚠️ <b>Error:</b> ID Layanan dan Harga harus berupa angka numerik yang valid.",
            parse_mode='HTML',
            message_thread_id=message_thread_id
        )
        return

    # 4. Eksekusi Perubahan Melalui Database Layer
    try:
        success = update_service_price(service_id, new_price)

        if success:
            await update.message.reply_text(
                f"✅ <b>Update Harga Berhasil!</b>\n\n"
                f"🆔 <b>ID Layanan:</b> <code>{service_id}</code>\n"
                f"💰 <b>Harga Baru:</b> <code>Rp{new_price:,.0f}</code>",
                parse_mode='HTML',
                message_thread_id=message_thread_id
            )
        else:
            await update.message.reply_text(
                "⚠️ <b>Gagal Update!</b>\n"
                "ID Layanan tidak ditemukan di database. Silakan periksa kembali daftar ID Anda di Dashboard Admin.",
                parse_mode='HTML',
                message_thread_id=message_thread_id
            )
            
    except Exception as e:
        logger.error(f"Error saat eksekusi update_service_price: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>Terjadi kesalahan database:</b>\n<code>{escape_html(str(e))}</code>",
            parse_mode='HTML',
            message_thread_id=message_thread_id
        )

# ==========================================================
# EXPORT HANDLER (Sesuai main.py)
# ==========================================================
edit_harga_command = edit_harga_command