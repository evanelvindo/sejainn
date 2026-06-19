"""
File entry point utama untuk menjalankan Bot Telegram Sejaiin Hub.
Mengatur inisialisasi aplikasi, job queue otomatis, dan registrasi handler.
Last Update: 2026-06-17 (Fix Full Admin Dashboard Button Routing and Regex Boundaries)
"""

import sys
import os
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ConversationHandler,
    PicklePersistence, TypeHandler, ContextTypes
)

# Setup path agar folder bot terbaca secara global dalam project
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import TOKEN 
# Mengimport conv_handler serta fungsi handler mandiri untuk menu baru
from handlers import conversation as conv
from handlers.conversation.handlers import (
    start,                      # 🌟 WAJIB DIIMPORT DI SINI
    daftar_mitra_handler, 
    informasi_sejaiin_handler
)
from database.orders import auto_complete_orders 

# --- IMPORT MODULAR (Admin Command Center) ---
from handlers.admin.dashboard import admin_menu_handler, admin_dashboard_navigation
from handlers.admin.order_ops import (
    admin_order_detail_handler,
    admin_verify_handler,
    admin_verify_proof_handler,
    admin_reject_transfer_handler
)
from handlers.admin.mitra_ops import admin_mitra_decision_handler, admin_mitra_detail_handler
from handlers.admin.finance_ops import (
    admin_payout_done_handler, 
    admin_report_command,
    admin_report_preview_handler,
    admin_report_pdf_callback
)
from handlers.admin.service_ops import edit_harga_command

# --- IMPORT MODULAR (User & Worker) ---
from handlers.user.feedback_ops import (
    user_finish_handler, 
    user_rate_handler, 
    user_save_rating_handler,
    user_report_handler 
)
from handlers.user.report import admin_resolve_report_handler

# Import Worker Handlers
from handlers.worker.order_ops import worker_take_handler, worker_send_proof_trigger_handler
from handlers.worker.submission import worker_send_bukti

# --- IMPORT MODULAR (User Interaction) ---
from handlers.user_interaction import (
    report_start, report_finish, 
    recom_start, recom_finish, 
    refresh_handler, REPORT, RECOM,
    handle_reupload_request, process_reuploaded_payment, REUPLOAD_PROOF  
)

# Konfigurasi Logging - Set ke INFO agar bisa melihat aktivitas di terminal
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

async def error_handler(update, context):
    """Log error yang terjadi agar bot tidak mati mendadak."""
    logging.error(f"Update {update} menyebabkan error {context.error}", exc_info=True)

async def job_auto_complete(context):
    """Fungsi otomatis pembersihan rutin order."""
    try:
        auto_complete_orders()
        logging.info("Job rutin: Membersihkan order kadaluarsa...")
    except Exception as e:
        logging.error(f"Gagal menjalankan auto_complete: {e}")

async def main():
    # 0. Persistence (Menjaga data state tetap aman)
    my_persistence = PicklePersistence(filepath="sejaiin_bot_persistence.pickle")

    # 1. Inisialisasi Application
    app = Application.builder() \
        .token(TOKEN) \
        .persistence(my_persistence) \
        .build()

    # 2. JobQueue (Eksekusi otomatis berkala tiap 1 jam)
    if app.job_queue:
        app.job_queue.run_repeating(job_auto_complete, interval=3600, first=60)

    # =================================================================
    # 🔍 SENSOR PELACAK GLOBAL (DETEKTIF TERMINAL)
    # =================================================================
    # Menangkap semua aktivitas klik tombol secara transparan untuk diprint ke CMD
    async def global_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            logging.info(f"📡 [TRACKER GLOBAL] Klik Tombol Terdeteksi! Payload Data: '{update.callback_query.data}'")
        return

    app.add_handler(TypeHandler(Update, global_tracker), group=-3)

    # =================================================================
    # 🌟 PRIORITY GROUP (-2): BYPASS ULTRA LOCK UNTUK WORKER/MITRA
    # =================================================================
    # Ditempatkan di Group -2 (Lebih tinggi dari conversation handler apa pun)
    # 1. Handler untuk Ambil Kerja
    app.add_handler(CallbackQueryHandler(worker_take_handler, pattern=r'^take_order_'), group=-2)
    # 2. Handler untuk Pemicu Kirim Bukti (Mencegah tombol 'send_proof_' hang/loading)
    app.add_handler(CallbackQueryHandler(worker_send_proof_trigger_handler, pattern=r'^send_proof_'), group=-2)

    # =================================================================
    # 3. KELOMPOK CALLBACK HANDLERS (GROUP 0 Bawaan)
    # =================================================================
    # FIX REGEX MATCH GROUP: Menambahkan tangkapan (brackets) agar lolos context.matches di finance_ops
    app.add_handler(CallbackQueryHandler(admin_payout_done_handler, pattern='^payout_done_([0-9]+)'))
    app.add_handler(CallbackQueryHandler(user_finish_handler, pattern='^finish_'))
    app.add_handler(CallbackQueryHandler(user_rate_handler, pattern='^rate_'))
    app.add_handler(CallbackQueryHandler(user_save_rating_handler, pattern='^save_rate_'))
    app.add_handler(CallbackQueryHandler(user_report_handler, pattern='^report_'))
    app.add_handler(CallbackQueryHandler(admin_reject_transfer_handler, pattern='^reject_transfer_'))
    
    # FIX REGEX BOUNDARY: Menghilangkan pembatas '$' kaku agar flexibel membaca data string ID order
    app.add_handler(CallbackQueryHandler(admin_verify_handler, pattern='^verify_'))
    app.add_handler(CallbackQueryHandler(admin_verify_proof_handler, pattern='^verify_proof_'))
    
    app.add_handler(CallbackQueryHandler(admin_mitra_detail_handler, pattern='^det_mitra_'))
    # MATCH GROUP INTEGRATION: Menjaga interaksi tombol setuju/tolak di mitra_ops tetap konsisten
    app.add_handler(CallbackQueryHandler(admin_mitra_decision_handler, pattern='^(acc|dec)_mitra_'))
    app.add_handler(CallbackQueryHandler(admin_order_detail_handler, pattern='^order_detail_'))
    app.add_handler(CallbackQueryHandler(admin_resolve_report_handler, pattern='^resolve_report_'))
    app.add_handler(CallbackQueryHandler(admin_report_preview_handler, pattern='^admin_report_preview$'))
    app.add_handler(CallbackQueryHandler(admin_report_pdf_callback, pattern='^admin_report_pdf$'))
    
    # 🚨 FIX DASHBOARD ROUTING: Mengubah '^admin$' menjadi '^admin' agar seluruh callback menu utama tertangkap
    app.add_handler(CallbackQueryHandler(admin_dashboard_navigation, pattern='^admin'))

    # 4. Conversation Handler Utama & User Interaction (Alur Belanja/Jasa)
    app.add_handler(conv.conv_handler)

    conv_user_interact = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^⚠️ Laporkan Masalah$'), report_start),
            MessageHandler(filters.Regex('^💡 Beri Rekomendasi Jasa$'), recom_start),
            MessageHandler(filters.Regex('^🔄 Kirim Ulang Bukti Transaksi$'), handle_reupload_request)
        ],
        states={
            REPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_finish)],
            RECOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, recom_finish)],
            REUPLOAD_PROOF: [MessageHandler(filters.PHOTO, process_reuploaded_payment)]
        },
        fallbacks=[CommandHandler("cancel", refresh_handler), MessageHandler(filters.Regex('^🔄 Refresh$'), refresh_handler)],
        persistent=True,
        name="interaction_conversation"
    )
    app.add_handler(conv_user_interact)
    
    # 5. Global Commands & Text Buttons
    app.add_handler(CommandHandler("start", start)) 
    app.add_handler(CommandHandler("admin", admin_menu_handler))
    app.add_handler(MessageHandler(filters.Regex("^🛠 Admin Panel$"), admin_menu_handler))
    app.add_handler(CommandHandler("edit_harga", edit_harga_command))
    app.add_handler(CommandHandler("laporan", admin_report_command))
    app.add_handler(MessageHandler(filters.Regex('^🔄 Refresh$'), refresh_handler))

    # --- REGISTRASI HANDLER MENU BARU ---
    app.add_handler(MessageHandler(filters.Regex('^🤝 Daftar Mitra$'), daftar_mitra_handler))
    app.add_handler(MessageHandler(filters.Regex('^ℹ️ Informasi Sejaiin$'), informasi_sejaiin_handler))
    
    # --- WORKER MEDIA SUBMISSION ---
    app.add_handler(MessageHandler(filters.PHOTO, worker_send_bukti))
    app.add_error_handler(error_handler)
    
    # --- ENGINE POLLING MANUAL (Mencegah Deadlock Terminal) ---
    print("\n" + "="*30)
    print("🚀 SEJAIIN HUB BOT IS RUNNING...")
    print("Tekan Ctrl + C di terminal untuk menghentikan bot.")
    print("="*30 + "\n")
    
    try:
        # Inisialisasi siklus hidup bot secara asinkron
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        # Jaga loop utama tetap hidup tanpa mengunci thread
        while True:
            await asyncio.sleep(3600)
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n🛑 Menangkap sinyal interupsi (Ctrl+C)...")
    finally:
        print("⚙️ Sedang mengamankan status persistence data & mematikan engine...")
        # Matikan komponen bot satu per satu dengan bersih
        if app.updater.running:
            await app.updater.stop()
        await app.stop()
        await app.shutdown()
        print("✅ Bot Sejaiin Hub berhasil dihentikan dengan aman.")

if __name__ == '__main__':
    try:
        # Menjalankan main loop asinkron secara native
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)