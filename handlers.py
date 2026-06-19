import logging
import mysql.connector
from telegram import (
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    KeyboardButton, 
    Update
)
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

# Import database dan konfigurasi
from database.orders import create_order
from utils import get_address_from_coords
from config import (
    PAYMENT_INFO, 
    GROUP_ID, 
    TOPIC_SERVICES, 
    TOPIC_FINANCE, 
    ADMIN_ID,
    DB_CONFIG
)
from handlers.admin.dashboard import admin_menu_handler

# Import konstanta lokal
from handlers.conversation.states import (
    SERVICE, 
    ASK_LOCATION, 
    WAITING_LOCATION, 
    WAITING_CONTACT, 
    WAITING_PHOTO,
    WAITING_TITIPIAN
)
from handlers.conversation.data import LAYANAN

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

# --- Helper Admin ---
async def handle_admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mengarahkan admin langsung ke dashboard admin."""
    await admin_menu_handler(update, context)
    return ConversationHandler.END


# --- HANDLER BARU UNTUK MENU TAMBAHAN ---

async def daftar_mitra_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan informasi pendaftaran mitra dan link form registrasi."""
    teks_mitra = (
        "🤝 **Gabung Menjadi Mitra Sejaiin**\n\n"
        "Punya keahlian di bidang servis AC, kelistrikan, saluran air, atau kebersihan? "
        "Mari bergabung menjadi bagian dari teknisi andalan Sejaiin Hub!\n\n"
        "📌 **Keuntungan:**\n"
        "• Jam kerja fleksibel (cocok untuk mahasiswa/freelancer).\n"
        "• Pendapatan transparan per orderan.\n"
        "• Komunitas teknisi yang solid.\n\n"
        "📋 **Formulir Pendaftaran:**\n"
        "Silakan isi formulir registrasi mitra melalui tautan di bawah ini:\n"
        "[Klik di Sini untuk Mengisi Form Registrasi](https://sejaiin.com/registrasi-mitra)\n\n"
        "_Tim kami akan melakukan verifikasi berkas dan menghubungi Anda via WhatsApp._"
    )
    
    keyboard = [[InlineKeyboardButton("📝 Isi Form Registrasi Web", url="https://sejaiin.com/registrasi-mitra")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(teks_mitra, reply_markup=reply_markup, parse_mode='Markdown', disable_web_page_preview=False)
    return ConversationHandler.END

async def informasi_sejaiin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan profil singkat aplikasi dan mengarahkan ke dashboard utama Sejaiin."""
    teks_info = (
        "ℹ️ **Tentang Sejaiin Hub**\n\n"
        "Sejaiin Hub adalah platform digital manajemen operasional pangkalan terintegrasi, "
        "sekaligus penyedia jasa kebutuhan mahasiswa Sistem Informasi dan lingkungan kosan sekitar Mendalo.\n\n"
        "🌐 **Dashboard & Informasi Utama:**\n"
        "Akses situs resmi kami untuk melihat visual tracking, monitoring dashboard, serta daftar layanan lengkap kami di:\n"
        "[Kunjungi Website Sejaiin](https://sejaiin.com)\n\n"
        "🚀 _Sistem ini dioptimalkan dengan Escrow System untuk keamanan transaksi dana titipan Anda._"
    )
    
    keyboard = [[InlineKeyboardButton("🖥 Buka Dashboard Web", url="https://sejaiin.com")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(teks_info, reply_markup=reply_markup, parse_mode='Markdown')
    return ConversationHandler.END


# --- Handler Alur Pesanan ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu Utama Sejaiin Hub dengan Deteksi Otomatis MySQL DB_CONFIG."""
    current_user_id = update.effective_user.id
    
    keyboard = [
        ["🛒 Pesan Jasa"],
        ["🤝 Daftar Mitra", "ℹ️ Informasi Sejaiin"],
        ["⚠️ Laporkan Masalah", "💡 Beri Rekomendasi Jasa"],
        ["🔄 Refresh"]
    ]
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT id, status_order FROM orders 
            WHERE telegram_id_pengguna = %s 
            ORDER BY id DESC LIMIT 1
        """
        cursor.execute(query, (current_user_id,))
        last_order = cursor.fetchone()
        
        if last_order and last_order.get('status_order') == 'PROSES':
            keyboard.insert(0, ["🔄 Kirim Ulang Bukti Transaksi"])
            context.user_data['reupload_order_id'] = last_order.get('id')
            
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"Gagal memeriksa status order terakhir via DB_CONFIG: {e}")
    
    is_user_admin = False
    if isinstance(ADMIN_ID, (list, tuple)):
        is_user_admin = int(current_user_id) in [int(i) for i in ADMIN_ID]
    else:
        is_user_admin = int(current_user_id) == int(ADMIN_ID)

    if is_user_admin:
        keyboard.append(["🛠 Admin Panel"])
        
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "👋 **Selamat datang di Sejaiin Hub!**\n\n"
        "Solusi kebutuhan mahasiswa IS dan layanan kosan.\n"
        "Silakan pilih menu di bawah ini untuk memulai:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def pilih_kategori(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahap 1: Memilih Kategori (HUB)."""
    categories = [[cat] for cat in LAYANAN.keys()]
    categories.append(["❌ Batal"])
    
    await update.message.reply_text(
        "📂 **Pilih Kategori Layanan (HUB):**",
        reply_markup=ReplyKeyboardMarkup(categories, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return SERVICE

async def pilih_jasa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahap 2: Memilih Jasa Spesifik dalam Kategori."""
    category = update.message.text
    
    if category == "❌ Batal":
        await update.message.reply_text("Pesanan dibatalkan.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)

    if category not in LAYANAN:
        await update.message.reply_text("⚠️ Kategori tidak valid. Silakan pilih kembali:")
        return SERVICE
        
    context.user_data['cat'] = category
    services = [[s] for s in LAYANAN[category]]
    services.append(["⬅️ Kembali ke Kategori", "❌ Batal"])
    
    await update.message.reply_text(
        "🛠 **Layanan Tersedia:**",
        reply_markup=ReplyKeyboardMarkup(services, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='Markdown'
    )
    return ASK_LOCATION

async def minta_lokasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahap 3: Interseptor Deteksi Kategori & Meminta Lokasi Pengerjaan."""
    text = update.message.text
    
    if text == "❌ Batal":
        await update.message.reply_text("Pesanan dibatalkan.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)
        
    if text == "⬅️ Kembali ke Kategori":
        return await pilih_kategori(update, context)
        
    context.user_data['jasa'] = text
    kategori_terpilih = context.user_data.get('cat', '')

    if "HUB 1" in kategori_terpilih or kategori_terpilih == "HUB 1":
        await update.message.reply_text(
            "💰 **Estimasi Modal Belanja / Titipan**\n\n"
            "Layanan Jastip memerlukan dana awal untuk membeli barang belanjaan Anda.\n"
            "Silakan ketik nominal estimasi harga barang belanjaan Anda:\n"
            "_(Ketik angka saja tanpa titik/Rp, contoh: `25000` atau ketik '❌ Batal' untuk batalkan)_",
            reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=True),
            parse_mode='Markdown'
        )
        return WAITING_TITIPIAN
    
    context.user_data['uang_titipan'] = 0.0
    return await prompt_minta_lokasi(update, context)

async def terima_uang_titipan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahap Tambahan HUB 1: Menangkap nominal titipan belanja."""
    input_text = update.message.text.strip()
    
    if input_text == "❌ Batal":
        await update.message.reply_text("Pesanan dibatalkan.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)
    
    try:
        nominal = float(input_text.replace('.', '').replace(',', ''))
        context.user_data['uang_titipan'] = nominal
    except ValueError:
        await update.message.reply_text(
            "⚠️ Format input salah. Mohon masukkan angka murni tanpa simbol Rp atau titik.\n"
            "Contoh: `35000`"
        )
        return WAITING_TITIPIAN

    return await prompt_minta_lokasi(update, context)

async def prompt_minta_lokasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fungsi pembantu guna memunculkan UI form lokasi alamat."""
    button = KeyboardButton("📍 Kirim Lokasi GPS Saya", request_location=True)
    markup = ReplyKeyboardMarkup([[button], ["🏠 Tulis Alamat Manual"], ["❌ Batal"]], one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "📍 **Dimana lokasi pengerjaan / pengantaran?**\n\n"
        "Gunakan tombol GPS atau ketik alamat lengkap Anda secara manual.",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    return WAITING_LOCATION

async def simpan_lokasi_dan_minta_kontak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Amankan user_text jika update yang masuk berupa location (bukan text)
    user_text = update.message.text if update.message.text else ""

    # 1. Jika user klik Batal
    if user_text == "❌ Batal":
        await update.message.reply_text("Pesanan dibatalkan.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)

    # 2. JIKA USER KLIK TOMBOL TULIS ALAMAT MANUAL (Gunakan pencocokan kata kunci agar aman)
    if "Tulis" in user_text or "Manual" in user_text:
        markup_input = ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "✍️ **Silakan ketikkan alamat lengkap pengantaran/pengerjaan Anda secara manual:**\n\n"
            "_(Contoh: Jl. Panglima No. 12, Kos Sakinah, Kamar 03)_",
            reply_markup=markup_input,
            parse_mode='Markdown'
        )
        # 🌟 KUNCI: Potong alur di sini agar tidak bocor ke bawah!
        return WAITING_LOCATION 

    # 3. JIKA USER MENGIRIMKAN LOKASI GPS (Tombol Native)
    if update.message.location:
        lat, lon = update.message.location.latitude, update.message.location.longitude
        alamat_geocoded = get_address_from_coords(lat, lon)
        context.user_data['lokasi'] = f"{alamat_geocoded} (📍 http://maps.google.com/?q={lat},{lon})"
    
    # 4. JIKA USER BENAR-BENAR MENGETIK ALAMAT ASLINYA
    else:
        MAX_ALLOWED = 100 
        if len(user_text) > MAX_ALLOWED:
            markup_error = ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=True)
            await update.message.reply_text(
                "⚠️ **Alamat Terlalu Panjang!**\n"
                f"Batas maksimal adalah {MAX_ALLOWED} karakter. Mohon ringkas kembali alamat Anda.",
                reply_markup=markup_error,
                parse_mode='Markdown'
            )
            return WAITING_LOCATION
        
        # Alamat ketikan manual yang valid disimpan
        context.user_data['lokasi'] = user_text

    # --- TAHAP LANJUTAN: Hanya dieksekusi jika lolos dari poin 3 atau 4 ---
    button = KeyboardButton("📱 Bagikan Kontak WhatsApp", request_contact=True)
    markup = ReplyKeyboardMarkup([[button], ["❌ Batal"]], one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ Lokasi disimpan.\n\n"
        "Terakhir, mohon klik tombol di bawah untuk membagikan nomor WhatsApp Anda agar tim kami dapat berkoordinasi.",
        reply_markup=markup,
        parse_mode='Markdown'
    )
    return WAITING_CONTACT

async def proses_kontak_dan_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahap 5: Finalisasi Order - Menyimpan data ke DB dan memberikan instruksi pembayaran."""
    
    if update.message.text == "❌ Batal":
        await update.message.reply_text("Pesanan dibatalkan.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)

    if not update.message.contact:
        await update.message.reply_text(
            "⚠️ Anda harus menekan tombol **'Bagikan Kontak WhatsApp'**!",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📱 Bagikan Kontak WhatsApp", request_contact=True)], ["❌ Batal"]], one_time_keyboard=True, resize_keyboard=True)
        )
        return WAITING_CONTACT

    no_wa = update.message.contact.phone_number
    jasa = context.user_data.get('jasa')
    lokasi = context.user_data.get('lokasi')
    uang_titipan = float(context.user_data.get('uang_titipan', 0.0))
    user_id = update.message.from_user.id
    
    try:
        # Buat order di database dengan status default (misal: 'MENUNGGU_PEMBAYARAN')
        order_id, harga_jasa = create_order(user_id, jasa, lokasi, no_wa, uang_titipan)
        context.user_data['order_id'] = order_id
        
        total_transfer = harga_jasa + uang_titipan
        
        rincian_user = (
            f"**Order #{order_id} Berhasil Dibuat!**\n\n"
            f"🛠 **Layanan:** `{jasa}`\n"
            f"💵 **Biaya Jasa:** Rp{harga_jasa:,.0f}\n"
        )
        if uang_titipan > 0:
            rincian_user += f"💰 **Deposit Uang Titipan:** Rp{uang_titipan:,.0f}\n"
            
        rincian_user += f"━━━━━━━━━━━━━━━━━━\n"
        rincian_user += f"🚨 **TOTAL TRANSFER:** **Rp{total_transfer:,.0f}**"
        
        await update.message.reply_text(rincian_user, parse_mode='Markdown')
        
        # Berikan info rekening bank ke user
        await update.message.reply_text(
            PAYMENT_INFO, 
            parse_mode='Markdown', 
            reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=True)
        )
        
        context.user_data['order_id'] = order_id
        context.user_data['dalam_proses_order'] = True
        
        # 🌟 LOGIKA FIX: JANGAN kirim pesan apa pun ke TOPIC_SERVICES di sini.
        # Tunggu sampai user benar-benar mengirimkan foto bukti transfernya.

        return WAITING_PHOTO
        
    except Exception as e:
        logging.error(f"Gagal membuat order: {e}", exc_info=True)
        await update.message.reply_text("❌ Terjadi kesalahan teknis saat membuat pesanan.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END


async def terima_bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahap Akhir: Menerima Bukti Foto dan Mendistribusikan Log secara Sinkron ke Grup Admin."""
    
    if update.message.text == "❌ Batal":
        await update.message.reply_text("Proses dibatalkan.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop('dalam_proses_order', None)
        return await start(update, context)

    if update.message.document:
        file_name = update.message.document.file_name or "Dokumen"
        await update.message.reply_text(
            f"❌ **Format Berkas Tidak Didukung!**\n\nHarap kirimkan bukti berupa **Foto/Gambar langsung (JPG/PNG)**.",
            reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=True),
            parse_mode='Markdown'
        )
        return WAITING_PHOTO

    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Silakan kirimkan **FOTO/SCREENSHOT** bukti transfer Anda.",
            reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=True),
            parse_mode='Markdown'
        )
        return WAITING_PHOTO

    # Ambil data dari context
    order_id = context.user_data.get('order_id', 'N/A')
    jasa = context.user_data.get('jasa', '-')
    lokasi = context.user_data.get('lokasi', '-')
    uang_titipan = float(context.user_data.get('uang_titipan', 0.0))
    
    # Ambil detail tambahan dari update data
    photo_file_id = update.message.photo[-1].file_id
    username = update.effective_user.username or 'NoUsername'
    
    # Tombol Aksi Verifikasi Terpusat untuk Admin Finansial
    keyboard_finance = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Verifikasi & Semburkan Order", callback_data=f"verify_{order_id}"),
            InlineKeyboardButton("❌ Tolak Struk", callback_data=f"reject_transfer_{order_id}")
        ]
    ])
    
    try:
        # 1. Kirim Notifikasi Validasi ke TOPIC_FINANCE (Lengkap dengan FOTO & TOMBOL VERIFIKASI)
        await context.bot.send_photo(
            chat_id=GROUP_ID, 
            message_thread_id=TOPIC_FINANCE,
            photo=photo_file_id, 
            caption=(
                f"📸 **BUKTI PEMBAYARAN BARU**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **Order:** #{order_id}\n"
                f"👤 **User:** @{username}\n"
                f"🛠 **Jasa:** {jasa}\n"
                f"💰 **Titipan:** Rp{uang_titipan:,.0f}\n\n"
                f"👉 _Mohon periksa mutasi bank Anda sebelum menekan tombol verifikasi di bawah._"
            ),
            parse_mode='Markdown',
            reply_markup=keyboard_finance
        )
        
        # 2. Kirim Notifikasi Pemantauan ke TOPIC_SERVICES (HANYA INFORMASI TEKS / LOG TANPA TOMBOL)
        # Ini berguna agar divisi lapangan tahu ada antrean masuk tanpa bisa melakukan verifikasi ganda
        admin_services_text = (
            f"⏳ **ANTREAN PESANAN BARU**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **Order ID:** #{order_id}\n"
            f"🛠 **Jenis Jasa:** {jasa}\n"
            f"📍 **Lokasi Tujuan:** {lokasi}\n"
            f"📊 **Status Finansial:** Menunggu Verifikasi Mutasi Bank..."
        )
        
        await context.bot.send_message(
            chat_id=GROUP_ID,
            message_thread_id=TOPIC_SERVICES,
            text=admin_services_text,
            parse_mode='Markdown'
        )
        
        # 3. Respon Akhir ke User Pendonor / Pelanggan
        await update.message.reply_text(
            "✅ **Bukti Pembayaran Terkirim!**\n\n"
            "Admin sedang mencocokkan dana pada mutasi bank. Pesanan Anda akan segera diproses begitu verifikasi selesai. Terima kasih! 🙏",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        
        context.user_data.pop('dalam_proses_order', None)
        return ConversationHandler.END

    except Exception as e:
        logging.error(f"Gagal mendistribusikan data transaksi: {e}")
        await update.message.reply_text(
            "❌ Sistem penanganan log penuh, data Anda telah diamankan secara lokal. Mohon tunggu konfirmasi admin.", 
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END


# ---💡 FALLBACK HANDLER CADANGAN UNTUK MENGATASI TIMEOUT ---

async def perangkap_foto_nyasar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyelamatkan foto jika percakapan utama terputus di tengah jalan akibat timeout telegram."""
    if update.message.chat.type == "private" and context.user_data.get('dalam_proses_order'):
        logging.info("Memproses bukti pembayaran lewat rute penyelamat (anti-timeout).")
        return await terima_bukti(update, context)

async def mulai_kirim_ulang_bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menjembatani user langsung masuk ke status WAITING_PHOTO untuk re-upload."""
    order_id = context.user_data.get('reupload_order_id')
    
    if not order_id:
        await update.message.reply_text("⚠️ Tidak ada order aktif yang memerlukan upload ulang bukti.")
        return await start(update, context)
        
    context.user_data['order_id'] = order_id
    context.user_data['dalam_proses_order'] = True
    
    await update.message.reply_text(
        f"🔄 **Kirim Ulang Bukti Pembayaran (Order #{order_id})**\n\n"
        f"Silakan kirimkan foto/screenshot bukti transfer yang baru dan valid di sini:",
        reply_markup=ReplyKeyboardMarkup([["❌ Batal"]], resize_keyboard=True, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    return WAITING_PHOTO

# --- ROUTER UTAMA CONVERSATION ---

order_conversation_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Text(["🛒 Pesan Jasa"]), pilih_kategori),
        MessageHandler(filters.Text(["🔄 Kirim Ulang Bukti Transaksi"]), mulai_kirim_ulang_bukti)
    ],
    states={
        SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pilih_jasa)],
        ASK_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, minta_lokasi)],
        WAITING_TITIPIAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, terima_uang_titipan)],
        # Mengubah fungsi target ke nama yang sinkron (tanpa embel-embel bank)
        WAITING_LOCATION: [MessageHandler(filters.LOCATION | (filters.TEXT & ~filters.COMMAND), simpan_lokasi_dan_minta_kontak)],
        WAITING_CONTACT: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), proses_kontak_dan_order)],
        # Mengizinkan teks masuk ke WAITING_PHOTO agar tombol "❌ Batal" berfungsi
        WAITING_PHOTO: [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), terima_bukti)]
    },
    fallbacks=[MessageHandler(filters.Text(["❌ Batal"]), start)]
)

foto_backup_handler = MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, perangkap_foto_nyasar)