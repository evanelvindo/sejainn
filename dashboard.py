"""
File handler untuk mengatur Dashboard Command Center Admin.
Mengelola verifikasi hak akses admin, render menu utama, dan navigasi callback tombol.
Last Update: 2026-06-17 (Fix Silent Ignore on Security Check & Alert Response)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

# Setup logging
logger = logging.getLogger(__name__)

# =========================================================================
# 🚨 PENTING: GANTI ANGKA DI BAWAH INI DENGAN USER ID TELEGRAM ASLI ANDA
# =========================================================================
ADMIN_LIST = [1453357152]  # <-- Masukkan ID hasil pelacakan CMD Anda di sini

def is_admin(user_id: int) -> bool:
    """Fungsi pembantu untuk memvalidasi apakah user_id terdaftar sebagai admin."""
    return user_id in ADMIN_LIST

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Menghasilkan struktur keyboard grid sesuai dengan mockup Command Center."""
    keyboard = [
        [
            InlineKeyboardButton("📦 Order Aktif", callback_data="admin_orders"),
            InlineKeyboardButton("👥 Verifikasi Mitra", callback_data="admin_mitra")
        ],
        [
            InlineKeyboardButton("💰 Keuangan & Payout", callback_data="admin_finance"),
            InlineKeyboardButton("🛠 Edit Layanan", callback_data="admin_services")
        ],
        [
            InlineKeyboardButton("📢 Broadcast Pesan", callback_data="admin_broadcast"),
            InlineKeyboardButton("🚨 Laporan Masalah", callback_data="admin_problems")
        ],
        [
            InlineKeyboardButton("📊 Laporan Ringkas", callback_data="admin_report_preview"),
            InlineKeyboardButton("❌ Tutup Menu", callback_data="admin_close")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menampilkan menu utama Command Center via perintah teks /admin atau tombol '🛠 Admin Panel'.
    """
    if not update.message:
        return

    user_id = update.effective_user.id
    
    # JIKA BUKAN ADMIN: Jangan biarkan bot diam, beri feedback edukatif
    if not is_admin(user_id):
        logger.warning(f"Akses Ditolak: User {user_id} tidak terdaftar di ADMIN_LIST.")
        await update.message.reply_text(
            f"❌ <b>Akses Ditolak!</b>\n\n"
            f"ID Telegram Anda (<code>{user_id}</code>) belum terdaftar sebagai administrator sistem Sejaiin Hub.\n"
            f"Hubungi Developer Utama untuk mendaftarkan ID ini.",
            parse_mode="HTML"
        )
        return

    # JIKA LOLOS VALIDASI: Kirim menu utama dashboard admin
    await update.message.reply_text(
        "🤖 <b>SEJAIIN HUB - COMMAND CENTER</b>\n"
        "-----------------------------------------\n"
        "Selamat datang di pusat kendali operasional sistem.\n"
        "Silakan pilih menu manajemen di bawah ini:",
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )

async def admin_dashboard_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler pusat untuk memproses semua klik tombol navigasi di Dashboard Admin.
    Menghubungkan interaksi tombol ke modul operasionalnya masing-masing.
    """
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Keamanan berlapis untuk query callback
    if not is_admin(user_id):
        await query.answer("❌ Anda tidak memiliki hak akses admin.", show_alert=True)
        return

    # Wajib panggil answer agar animasi loading/jam berputar di Telegram hilang
    await query.answer()
    
    data = query.data
    logger.info(f"Admin {user_id} mengeklik menu: {data}")

    # Alur Percabangan Menu Navigasi
    if data == "admin":
        await query.edit_message_text(
            "🤖 <b>SEJAIIN HUB - COMMAND CENTER</b>\n"
            "-----------------------------------------\n"
            "Selamat datang di pusat kendali operasional sistem.\n"
            "Silakan pilih menu manajemen di bawah ini:",
            parse_mode="HTML",
            reply_markup=get_admin_keyboard()
        )
        
    elif data == "admin_orders":
        await query.edit_message_text(
            "📦 <b>Manajemen Order Aktif</b>\n\n"
            "Sistem siap menampilkan data antrean order aktif Sejaiin.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="admin")]])
        )
        
    elif data == "admin_mitra":
        await query.edit_message_text(
            "👥 <b>Manajemen Verifikasi Mitra</b>\n\n"
            "Silakan periksa berkas pendaftaran calon mitra yang masuk ke dalam sistem.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="admin")]])
        )
        
    elif data == "admin_finance":
        await query.edit_message_text(
            "💰 <b>Manajemen Keuangan & Payout</b>\n\n"
            "Sistem siap memproses rekapitulasi data saldo harian dan penarikan dana (payout) mitra.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="admin")]])
        )
        
    elif data == "admin_services":
        await query.edit_message_text(
            "🛠 <b>Manajemen Edit Layanan</b>\n\n"
            "Untuk mengubah harga layanan secara instan, gunakan perintah teks langsung:\n\n"
            "Format: <code>/edit_harga [ID_Layanan] [Harga_Baru]</code>\n"
            "Contoh: <code>/edit_harga 1 75000</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="admin")]])
        )
        
    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 <b>Fitur Broadcast Pesan Masal</b>\n\n"
            "Fitur ini digunakan untuk menyebarkan informasi ke seluruh pengguna Sejaiin Hub.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="admin")]])
        )
        
    elif data == "admin_problems":
        await query.edit_message_text(
            "🚨 <b>Pusat Pengaduan & Laporan Masalah</b>\n\n"
            "Menampilkan keluhan masuk dari pelanggan maupun mitra.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data="admin")]])
        )
        
    elif data == "admin_close":
        await query.delete_message()