import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.mitra import get_eligible_workers

# Pastikan level logging diubah ke INFO agar print log kita terlihat di terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def broadcast_to_workers(context: ContextTypes.DEFAULT_TYPE, order: dict):
    """
    Mengirimkan notifikasi order baru ke semua mitra yang sesuai dengan jenis jasa.
    Dilengkapi sistem fail-safe key extractor untuk mencegah salah parsing ID Order.
    """
    # 🔍 LINE DETEKTIF: Cetak isi asli dict order ke terminal XAMPP / VS Code Anda
    print("\n" + "="*50)
    print("DEBUG: ISI DICT ORDER YANG DITERIMA DARI ADMIN PANEL:")
    print(order)
    print("👉 Tipe Data ID:", type(order.get('id_order')), "Nilai:", order.get('id_order'))
    print("="*50 + "\n")

    # 1. Ekstraksi Data Order dengan Multi-Key Fail-Safe
    # Mengantisipasi perbedaan nama kolom antara object database ('id') dan response UI ('id_order')
    order_id = order.get('id_order') or order.get('order_id') or order.get('id')
    jasa = order.get('jenis_jasa') or order.get('jasa')
    lokasi = order.get('lokasi_pengguna') or order.get('lokasi', 'Lokasi tidak tersedia')
    
    # Ambil data harga/pendapatan jika ada (untuk melengkapi visual escrow system)
    pendapatan = order.get('pendapatan_mitra') or order.get('harga_mitra') or order.get('harga')
    if isinstance(pendapatan, (int, float)):
        pendapatan_text = f"Rp{pendapatan:,}"
    else:
        pendapatan_text = str(pendapatan) if pendapatan else "Rp10,000"

    # Validasi Krusial: Jika ID Order gagal di-extract, batalkan broadcast agar tidak melahirkan tombol rusak
    if not order_id:
        logging.error(f"❌ Broadcast Gagal ditolak: ID Order tidak ditemukan dalam dictionary. Isi data: {order}")
        return False
    
    # Pastikan order_id bertipe integer murni/string bersih tanpa spasi
    order_id = str(order_id).strip()
    
    # 2. Ambil Daftar Mitra yang Memiliki Keahlian Sesuai
    workers = get_eligible_workers(jasa)
    if not workers: 
        logging.warning(f"⚠️ Broadcast dihentikan: Tidak ada mitra yang cocok untuk jasa '{jasa}'.")
        return False
    
    count_sent = 0
    
    # 3. Iterasi Kirim Pesan ke Setiap Mitra
    for worker in workers:
        try:
            target_id = worker.get('telegram_id') or worker.get('telegram_id_mitra') or worker.get('chat_id')
            if not target_id:
                continue

            # 🔒 VERIFIKASI UTAMA: Callback data harus murni diawali 'take_' + Angka ID Order
            # Format ini harus klop dengan pattern=r'take_' di main.py Anda
            kb = [[InlineKeyboardButton("🛒 Ambil Pekerjaan", callback_data=f"take_{order_id}")]]
            
            text_msg = (
                f"🔔 **PESANAN BARU TERSEDIA! (ESCROW SYSTEM)**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **Order ID:** `#{order_id}`\n"
                f"🛠 **Jenis Jasa:** {jasa}\n"
                f"💵 **Pendapatan Mitra:** {pendapatan_text}\n"
                f"📍 **Lokasi Layanan:** {lokasi}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"📥 *Silakan klik tombol di bawah ini untuk mengambil pekerjaan! Siapa cepat, dia dapat.*"
            )
            
            await context.bot.send_message(
                chat_id=target_id, 
                text=text_msg, 
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
            count_sent += 1
            logging.info(f"✅ Broadcast Berhasil Terkirim ke Mitra ID: {target_id} untuk Order #{order_id}")
            
        except Exception as e:
            logging.error(f"❌ Gagal mengirim paket broadcast ke salah satu mitra: {e}")
            continue
            
    return count_sent > 0