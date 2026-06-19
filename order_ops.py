import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from database.mitra import assign_worker, get_mitra_by_telegram_id
from database.orders import get_order_details
from config import GROUP_ID, TOPIC_ORDER_TAKEN

# Mengubah konfigurasi logging agar pesan debug tercetak jelas di terminal CMD
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def worker_take_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menangani aksi ketika mitra menekan tombol 'Ambil Pekerjaan'.
    Menggunakan validasi preventif, aman dari batasan edit pesan broadcast Telegram,
    serta memunculkan notifikasi pop-up instan agar tombol tidak hang/loading.
    """
    query = update.callback_query
    callback_data = query.data  # Contoh: "take_26"
    worker_telegram_id = update.effective_user.id
    
    logging.info(f"📥 worker_take_handler dipicu | Data: {callback_data} | User: {worker_telegram_id}")
    
    try:
        # =================================================================
        # 1. PARSING & SANITASI ORDER ID
        # =================================================================
        if '_' not in callback_data:
            await query.answer(f"❌ Format tombol rusak ({callback_data})", show_alert=True)
            return
            
        raw_order_id = callback_data.split('_')[-1]
        clean_order_id = ''.join(filter(str.isdigit, str(raw_order_id)))
        
        if not clean_order_id:
            await query.answer("❌ Gagal mengekstrak ID numerik dari payload tombol.", show_alert=True)
            return
            
        order_id = int(clean_order_id)
        
        # =================================================================
        # 2. VALIDASI DATA DARI DATABASE (MITRA & ORDER)
        # =================================================================
        mitra = get_mitra_by_telegram_id(worker_telegram_id)
        initial_order = get_order_details(order_id)
        
        if not initial_order:
            await query.answer(f"❌ Data Order #{order_id} tidak ditemukan di database Sejaiin.", show_alert=True)
            return
            
        if not mitra:
            await query.answer(
                f"❌ Akun Anda (ID: {worker_telegram_id}) BELUM TERDAFTAR sebagai Mitra.\n\n"
                f"Silakan kembali ke Bot Utama dan klik menu '🤝 Daftar Mitra'.", 
                show_alert=True
            )
            return

        db_mitra_id = mitra.get('id')  # Primary Key ID internal mitra
        current_mitra_id = initial_order.get('mitra_id')
        current_status = initial_order.get('status_order')

        # Setup nomor WhatsApp User untuk koordinasi kerja
        user_wa = initial_order.get('no_whatsapp_user', '') or initial_order.get('no_hp', '')
        wa_clean = ''.join(filter(str.isdigit, str(user_wa)))
        
        kb_mitra = [
            [InlineKeyboardButton("💬 Hubungi User (WhatsApp)", url=f"https://wa.me/{wa_clean}")],
            [InlineKeyboardButton("📷 Kirim Bukti Selesai", callback_data=f"send_proof_{order_id}")]
        ]

        # =================================================================
        # 3. VALIDASI IDEMPOTENSI (Antisipasi Klik Ganda / Double-Click)
        # =================================================================
        
        # KASUS A: Order ini ternyata SUDAH dikunci oleh Anda sendiri sebelumnya
        if current_mitra_id == db_mitra_id:
            context.user_data['active_order_id'] = order_id
            await query.answer("✅ Pekerjaan ini sudah resmi Anda ambil!", show_alert=True)
            
            # Kirim salinan detailnya ke PC Mitra sebagai back-up jika pesan grup tidak bisa di-edit
            try:
                await context.bot.send_message(
                    chat_id=worker_telegram_id,
                    text=(
                        f"🗂 **BACKUP DETAIL ORDER #{order_id}**\n\n"
                        f"🛠 **Jasa:** {initial_order.get('jenis_jasa')}\n"
                        f"📍 **Lokasi:** {initial_order.get('lokasi_pengguna')}\n━"
                    ),
                    reply_markup=InlineKeyboardMarkup(kb_mitra)
                )
            except Exception:
                pass
            return

        # KASUS B: Order sudah disambar duluan oleh mitra lain
        if current_status != 'MENUNGGU_MITRA' or (current_mitra_id is not None and current_mitra_id != db_mitra_id):
            await query.answer(f"❌ Telat! Order #{order_id} baru saja diambil oleh mitra lain.", show_alert=True)
            
            # Coba ubah teks tombolnya jika memungkinkan, abaikan jika itu pesan broadcast channel
            try:
                await query.edit_message_text(f"❌ Order #{order_id} sudah diambil oleh mitra lain.")
            except BadRequest:
                pass
            return

        # =================================================================
        # 4. EKSEKUSI MUTASI DATABASE (LOCK ORDER)
        # =================================================================
        is_success = assign_worker(order_id, worker_telegram_id)
        
        if is_success:
            order = get_order_details(order_id) or initial_order
            context.user_data['active_order_id'] = order_id

            # Berikan alert sukses berlatar hijau/pop-up di Telegram mitra
            await query.answer("🎉 BERHASIL AMBIL PEKERJAAN! Detail tugas dikirim ke Chat Pribadi Anda.", show_alert=True)

            # Mengirim antarmuka kerja eksklusif langsung ke Private Chat (PC) mitra
            msg_ke_mitra = (
                f"✅ **Pekerjaan Resmi Diambil!**\n\n"
                f"Anda berhasil mengunci **Order #{order_id}**.\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🛠 **Tugas:** {order.get('jenis_jasa')}\n"
                f"📍 **Lokasi:** {order.get('lokasi_pengguna')}\n\n"
                f"👉 *Langkah Selanjutnya:* Hubungi pelanggan via WhatsApp dengan tombol di bawah. "
                f"Jika pekerjaan telah selesai, upload **Foto Bukti Kerja** langsung di chat ini."
            )
            
            try:
                await context.bot.send_message(
                    chat_id=worker_telegram_id,
                    text=msg_ke_mitra,
                    reply_markup=InlineKeyboardMarkup(kb_mitra),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Gagal mengirim detail kerja ke PC Mitra {worker_telegram_id}: {e}")

            # Mencoba mengupdate tampilan tombol di grup lowongan agar mitra lain tahu order sudah sold out
            try:
                await query.edit_message_text(
                    f"🔒 **Order #{order_id} Telah Diambil**\n"
                    f"🏃‍♂️ Peluang kerja ini sudah ditutup karena diambil oleh Mitra Sejaiin."
                )
            except BadRequest:
                # Jika gagal edit (karena aturan pesan channel), skip tanpa merusak alur program
                pass

            # =================================================================
            # 5. NOTIFIKASI OTOMATIS KE SISI USER PENGGUNA
            # =================================================================
            mitra_wa = mitra.get('no_whatsapp', '')
            mitra_wa_clean = ''.join(filter(str.isdigit, str(mitra_wa)))
            kb_user = [[InlineKeyboardButton("💬 Chat Mitra via WA", url=f"https://wa.me/{mitra_wa_clean}")]]
            
            try:
                await context.bot.send_message(
                    chat_id=order['telegram_id_pengguna'],
                    text=(
                        f"✨ **Kabar Baik! Mitra Ditemukan.**\n\n"
                        f"Pesanan Anda `#{order_id}` telah diambil oleh **{mitra['nama_lengkap']}**.\n"
                        f"Beliau akan segera meluncur atau Anda dapat memulai koordinasi awal lewat tombol WhatsApp di bawah."
                    ),
                    reply_markup=InlineKeyboardMarkup(kb_user),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Gagal kirim notifikasi ke user {order['telegram_id_pengguna']}: {e}")
            
            # =================================================================
            # 6. KIRIM LOG MONITORING KE GRUP ADMIN CENTER
            # =================================================================
            try:
                await context.bot.send_message(
                    chat_id=GROUP_ID, 
                    message_thread_id=TOPIC_ORDER_TAKEN,
                    text=(
                        f"🏃‍♂️ **ORDER DIAMBIL MITRA**\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 **Order ID:** `#{order_id}`\n"
                        f"👤 **Mitra:** {mitra['nama_lengkap']}\n"
                        f"📱 **ID Telegram:** `{worker_telegram_id}`\n"
                        f"📊 **Status:** Progres Pengerjaan"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Gagal mengirim log ke grup admin: {e}")
                
        else:
            await query.answer("❌ Database gagal mengunci order. Kemungkinan status order sudah berubah.", show_alert=True)

    except Exception as e:
        logging.error(f"💥 Error fatal di worker_take_handler: {e}", exc_info=True)
        try:
            await query.answer(f"💥 Sistem Error: {str(e)}", show_alert=True)
        except Exception:
            pass


async def worker_send_proof_trigger_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menangani klik tombol '📷 Kirim Bukti Selesai' dari Mitra.
    Fungsi ini mematikan jam pasir berputar (loading) secara instan, mengunci session ID,
    dan memberikan instruksi interaktif yang mengarahkan mitra untuk menekan klip kertas/kamera.
    """
    query = update.callback_query
    callback_data = query.data  # Contoh: "send_proof_26"
    worker_telegram_id = update.effective_user.id
    
    logging.info(f"📸 worker_send_proof_trigger_handler dipicu | Data: {callback_data} | User: {worker_telegram_id}")
    
    try:
        # 1. PARSING & SANITASI ORDER ID
        if '_' not in callback_data:
            await query.answer(f"❌ Format tombol tidak dikenal ({callback_data})", show_alert=True)
            return
            
        raw_order_id = callback_data.split('_')[-1]
        clean_order_id = ''.join(filter(str.isdigit, str(raw_order_id)))
        
        if not clean_order_id:
            await query.answer("❌ Gagal mendeteksi nomor ID pesanan.", show_alert=True)
            return
            
        order_id = int(clean_order_id)

        # 2. LOCK STATE SESSION (Wajib agar file submission tahu target ordernya)
        context.user_data['active_order_id'] = order_id
        
        # 3. 🚨 FIX UTAMA: Matikan Jam Pasir / Loading berputar di aplikasi Telegram secara instan
        await query.answer("Sistem Siap! Silakan unggah foto bukti kerja Anda.", show_alert=False)
        
        # 4. KIRIMKAN PANDUAN NAVIGASI ANTARMUKA PADA CHAT
        await context.bot.send_message(
            chat_id=worker_telegram_id,
            text=(
                f"📸 **SUBMISSION SYSTEM (ORDER #{order_id})**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"Sistem Sejaiin Hub telah siap menerima berkas digital Anda.\n\n"
                f"**Silakan ikuti instruksi berikut:**\n"
                f"1. Tekan tombol **Klip Kertas (📎)** atau ikon **Kamera** di keyboard Telegram Anda.\n"
                f"2. Pilih foto bukti pengerjaan jasa yang valid.\n"
                f"3. Tekan **Kirim / Send**.\n\n"
                f"⚠️ *Catatan: Kirimkan dokumen dalam bentuk gambar langsung (Photo), jangan mengirimkannya dalam bentuk kompresi berkas (File/Document).*"
            ),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"💥 Error di worker_send_proof_trigger_handler: {e}", exc_info=True)
        try:
            await query.answer("❌ Terjadi kegagalan interaksi internal.", show_alert=True)
        except Exception:
            pass