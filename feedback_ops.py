import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import GROUP_ID, TOPIC_SERVICES, PROFIT_MARGIN
# TAMBAHKAN import save_finance_report di sini
from database.orders import get_order_details, update_order_status, save_report, save_review, save_finance_report
from database.mitra import get_mitra_by_id

# Setup logging ke ERROR agar lebih bersih
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

async def user_finish_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menyelesaikan order, menghitung bagi hasil (nett), 
    menyimpan laporan keuangan ke tabel payouts, dan memberi notifikasi ke Admin.
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # 1. Identifikasi Order
        parts = query.data.split('_')
        order_id = parts[1]
        order = get_order_details(order_id)
        
        if not order:
            await query.edit_message_text("⚠️ Data order tidak ditemukan.")
            return

        # 2. Update status di database menjadi SELESAI
        update_order_status(order_id, 'SELESAI')

        # 3. Ambil data mitra
        mitra_id = order.get('worker_id') or order.get('mitra_id')
        mitra_data = get_mitra_by_id(mitra_id) if mitra_id else None

        # --- FIX LOGIKA PERHITUNGAN KEUANGAN ---
        harga_raw = order.get('harga_final') 
        harga_total = float(harga_raw) if harga_raw else 0.0
        
        from config import PROFIT_MARGIN, GROUP_ID, TOPIC_SERVICES
        nominal_potongan = harga_total * PROFIT_MARGIN
        nominal_bersih_mitra = harga_total - nominal_potongan
        persen_tampilan = int(PROFIT_MARGIN * 100)
        
        # --- [EKSEKUSI PENYELAMATAN DATA PAYOUTS] ---
        # Memanggil fungsi database untuk menyimpan data keuangan ke tabel payouts
        print(f"\n🚀 DEBUG: Memicu fungsi save_finance_report untuk Order #{order_id}...")
        payout_saved = save_finance_report(order_id, harga_total, nominal_potongan, nominal_bersih_mitra)
        
        if payout_saved:
            print(f"✅ DEBUG: Data payout Order #{order_id} BERHASIL masuk ke MySQL.")
        else:
            print(f"❌ DEBUG: Data payout Order #{order_id} GAGAL disimpan. Cek terminal/log database!")
        # --------------------------------------------

        # 4. NOTIFIKASI KE ADMIN (Grup/Thread)
        admin_notif_text = (
            f"💰 **PERMINTAAN PEMBAYARAN MITRA**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✅ **Order #{order_id} SELESAI**\n\n"
            f"👤 **Pelanggan:** {update.effective_user.full_name}\n"
            f"🤝 **Mitra:** {mitra_data['nama_lengkap'] if mitra_data else 'Tidak terdeteksi'}\n\n"
            f"💵 **Total Bayar User:** Rp{harga_total:,.0f}\n"
            f"✂️ **Potongan Admin ({persen_tampilan}%):** Rp{nominal_potongan:,.0f}\n"
            f"💸 **Nett ke Mitra:** Rp{nominal_bersih_mitra:,.0f}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Admin harap segera memproses komisi ke mitra."
        )
        
        kb_admin = [[InlineKeyboardButton("✅ Tandai Sudah Dibayar", callback_data=f"payout_done_{order_id}")]]
        
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_SERVICES,
            text=admin_notif_text,
            reply_markup=InlineKeyboardMarkup(kb_admin),
            parse_mode='Markdown'
        )

        # 5. Notifikasi ke Mitra
        target_id = mitra_data.get('telegram_id_mitra') or mitra_data.get('telegram_id') if mitra_data else None
        if target_id:
            await context.bot.send_message(
                chat_id=target_id,
                text=(
                    f"🏁 **Order #{order_id} Selesai!**\n\n"
                    f"Pelanggan telah mengonfirmasi penyelesaian.\n"
                    f"Pendapatan Anda: **Rp{nominal_bersih_mitra:,.0f}**\n"
                    f"_(Setelah potongan admin {persen_tampilan}%)_\n\n"
                    f"Saldo akan segera diproses oleh Admin. Terima kasih!"
                ),
                parse_mode='Markdown'
            )

        # 6. Update UI User (Menampilkan Rating)
        kb_user = [
            [InlineKeyboardButton(f"{i} ⭐", callback_data=f"rate_{order_id}_{i}") for i in range(1, 4)],
            [InlineKeyboardButton(f"{i} ⭐", callback_data=f"rate_{order_id}_{i}") for i in range(4, 6)]
        ]
        
        await query.edit_message_text(
            text=(
                f"✅ **Pekerjaan Selesai!**\n\n"
                f"Terima kasih telah mempercayakan kebutuhan Anda di Sejaiin Hub.\n"
                f"Mohon berikan penilaian untuk pelayanan mitra pada Order **#{order_id}**:"
            ),
            reply_markup=InlineKeyboardMarkup(kb_user),
            parse_mode='Markdown'
        )

    except Exception as e:
        logging.error(f"Error pada user_finish_handler: {e}", exc_info=True)

async def user_rate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dipicu saat user klik salah satu bintang (1-5). Menampilkan konfirmasi sebelum simpan."""
    query = update.callback_query
    await query.answer()
    
    try:
        parts = query.data.split('_')
        if len(parts) < 3: return
        
        order_id = parts[1]
        rating = parts[2]
        
        kb = [
            [InlineKeyboardButton("✅ Simpan Penilaian", callback_data=f"save_rate_{order_id}_{rating}")],
            [InlineKeyboardButton("⬅️ Ganti Rating", callback_data=f"finish_{order_id}")]
        ]
        
        await query.edit_message_text(
            f"Anda memilih: **{rating} ⭐**\n"
            "Apakah Anda yakin ingin menyimpan penilaian ini?",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Error pada user_rate_handler: {e}")

async def user_save_rating_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simpan rating ke database reviews."""
    query = update.callback_query
    await query.answer()
    
    try:
        parts = query.data.split('_')
        if len(parts) < 4: return
        
        order_id = parts[2]
        rating = parts[3]
        
        order = get_order_details(order_id)
        if not order:
            await query.edit_message_text("❌ Data order hilang.")
            return

        mitra_id = order.get('worker_id') or order.get('mitra_id')
        if not mitra_id:
            await query.edit_message_text("⚠️ Data mitra tidak ditemukan.")
            return
        
        success = save_review(order_id, mitra_id, int(rating), "Rating via Bot")
        
        if success:
            await query.edit_message_text(
                "✅ **Penilaian Disimpan!**\n\n"
                "Terima kasih atas feedback Anda. Masukan Anda sangat berarti bagi pengembangan Sejaiin Hub.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Gagal menyimpan ke database.")

    except Exception as e:
        logging.error(f"Error pada user_save_rating_handler: {e}")

async def user_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Laporan kendala ke Admin Grup."""
    query = update.callback_query
    await query.answer()
    
    try:
        parts = query.data.split('_')
        order_id = parts[1]
        order = get_order_details(order_id)
        if not order: return

        mitra_id = order.get('worker_id')
        mitra = get_mitra_by_id(mitra_id) if mitra_id else None
        
        save_report(order_id, update.effective_user.id, "User menekan tombol Lapor Kendala.")
        
        admin_msg = (
            f"🚨 **LAPORAN KENDALA USER**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Order: #{order_id}\n"
            f"👤 User: {update.effective_user.full_name}\n"
            f"🤝 Mitra: {mitra['nama_lengkap'] if mitra else 'Belum diambil'}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        
        kb_admin = []
        links = []
        if order.get('no_whatsapp_user'):
            links.append(InlineKeyboardButton("💬 WA User", url=f"https://wa.me/{order['no_whatsapp_user']}"))
        if mitra and mitra.get('no_whatsapp'):
            links.append(InlineKeyboardButton("💬 WA Mitra", url=f"https://wa.me/{mitra['no_whatsapp']}"))
        
        if links: kb_admin.append(links)
            
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_SERVICES,
            text=admin_msg,
            reply_markup=InlineKeyboardMarkup(kb_admin),
            parse_mode='Markdown'
        )
        
        await query.edit_message_text(
            "⚠️ **Laporan Terkirim.**\n\n"
            "Admin sedang meninjau kendala Anda. Mohon tunggu informasi selanjutnya."
        )
    except Exception as e:
        logging.error(f"Error pada user_report_handler: {e}")