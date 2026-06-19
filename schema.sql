-- =============================================
-- SEJAIIN HUB DATABASE SCHEMA (PROD READY)
-- Last Update: 2026-05-16 (Upgraded: Escrow System)
-- Prodi: Sistem Informasi
-- =============================================

-- 1. Setup Database
DROP DATABASE IF EXISTS sejaiin_db;
CREATE DATABASE sejaiin_db;
USE sejaiin_db;

-- 2. Tabel Mitra (Ditambah: no_rekening & admin_note)
CREATE TABLE mitra (
    id INT PRIMARY KEY AUTO_INCREMENT,
    telegram_id_mitra BIGINT UNIQUE NOT NULL, 
    nama_lengkap VARCHAR(100) NOT NULL,
    nik VARCHAR(20) UNIQUE NOT NULL,
    no_whatsapp VARCHAR(20),
    no_rekening VARCHAR(50) DEFAULT '-', 
    foto_ktp VARCHAR(255),
    status_verifikasi ENUM('MENUNGGU', 'DISETUJUI', 'DITOLAK') DEFAULT 'MENUNGGU',
    status_kerja ENUM('AKTIF', 'SIBUK', 'NONAKTIF') DEFAULT 'NONAKTIF',
    rating FLOAT DEFAULT 5.0,
    admin_note TEXT, -- Alasan jika verifikasi ditolak
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabel Layanan
CREATE TABLE layanan (
    id INT PRIMARY KEY AUTO_INCREMENT,
    kategori VARCHAR(50) NOT NULL,
    kode_layanan VARCHAR(10) NOT NULL,
    nama_layanan VARCHAR(100) NOT NULL,
    harga DECIMAL(15,2) DEFAULT 0.00,
    deskripsi TEXT
);

-- 4. Tabel Relasi Mitra - Layanan
CREATE TABLE mitra_layanan (
    mitra_id INT NOT NULL,
    layanan_id INT NOT NULL,
    PRIMARY KEY (mitra_id, layanan_id),
    FOREIGN KEY (mitra_id) REFERENCES mitra(id) ON DELETE CASCADE,
    FOREIGN KEY (layanan_id) REFERENCES layanan(id) ON DELETE CASCADE
);

-- 5. Tabel Orders (UPGRADED: Ditambahkan kolom uang_titipan)
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    telegram_id_pengguna BIGINT NOT NULL, 
    mitra_id INT NULL, 
    jenis_jasa VARCHAR(100) NOT NULL,
    lokasi_pengguna TEXT,
    no_whatsapp_user VARCHAR(20),
    harga_final DECIMAL(15,2) DEFAULT 0.00,    -- Digunakan sebagai Biaya Jasa Flat
    uang_titipan DECIMAL(15,2) DEFAULT 0.00,   -- UPGRADE: Tempat mengunci deposit modal belanja (HUB 1)
    status_order ENUM(
        'PROSES',               -- User sedang input data
        'VERIFIKASI_ADMIN',      -- Menunggu admin konfirmasi order
        'MENUNGGU_MITRA',       -- Sudah dikonfirmasi admin, menunggu mitra ambil
        'KERJA',                -- Mitra sedang mengerjakan
        'MENUNGGU_VERIFIKASI',  -- Mitra sudah kirim bukti, nunggu admin cek foto
        'SELESAI',              -- Order selesai (payout terbuat)
        'BATAL'                 -- Order dibatalkan admin/user
    ) DEFAULT 'PROSES',
    bukti_kerja VARCHAR(255),   -- Menyimpan file_id foto telegram
    admin_note TEXT,            -- Alasan jika order ditolak/batal
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (mitra_id) REFERENCES mitra(id) ON DELETE SET NULL
);

-- 6. Tabel Laporan (Reports)
CREATE TABLE reports (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    pelapor_id BIGINT NOT NULL, -- Telegram ID pelapor
    pesan TEXT,
    status_report ENUM('OPEN', 'RESOLVED') DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- 7. Tabel Payouts (Pembukuan Margin)
CREATE TABLE payouts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    mitra_id INT NOT NULL,
    total_bayar DECIMAL(15,2) NOT NULL,     -- Total uang dari user (Jasa + Titipan)
    gaji_mitra DECIMAL(15,2) NOT NULL,      -- Bersih ke mitra (90% Jasa + 100% Titipan)
    keuntungan_admin DECIMAL(15,2) NOT NULL, -- Potongan murni (10% dari Jasa)
    status_bayar ENUM('PENDING', 'PAID') DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (mitra_id) REFERENCES mitra(id) ON DELETE CASCADE
);

-- 8. Tabel Reviews (Ditambah ON DELETE CASCADE)
CREATE TABLE reviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    mitra_id INT NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    ulasan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (mitra_id) REFERENCES mitra(id) ON DELETE CASCADE
);

-- 9. Indexing (Optimasi Pencarian Bot)
CREATE INDEX idx_order_status ON orders(status_order);
CREATE INDEX idx_payout_status ON payouts(status_bayar);
CREATE INDEX idx_mitra_telegram ON mitra(telegram_id_mitra);
CREATE INDEX idx_layanan_kode ON layanan(kode_layanan);

-- 10. Data Awal Layanan (Sejaiin Hub v1.1 - Upgraded & Clean)
INSERT INTO layanan (kategori, kode_layanan, nama_layanan, harga, deskripsi) VALUES 
-- HUB 1: Kategori Jastip (Membutuhkan input nominal uang titipan awal di Bot)
('HUB 1', '1.1', 'Jastip Print & Jilid Tugas', 10000.00, 'Tarif jasa flat. Selisih biaya cetak fisik kertas diselesaikan COD langsung dengan mitra.'),
('HUB 1', '1.2', 'Jastip Makanan & Minuman', 8000.00, 'Tarif jasa flat radius kampus. Selisih harga menu asli diselesaikan COD dengan mitra.'),
('HUB 1', '1.3', 'Jastip Belanja Minimarket/Kos', 12000.00, 'Tarif jasa flat belanja. Selisih uang belanja asli diselesaikan via COD dengan mitra.'),

-- HUB 2: Kategori Digital & IT (Murni 100% Harga Jasa, Tanpa Uang Titipan)
('HUB 2', '2.1', 'Jasa Instalasi Software Kuliah', 30000.00, 'Jasa instal & konfigurasi tools coding, SPSS, Adobe, dll (Harga per software).'),
('HUB 2', '2.2', 'Cleaning & Ganti Thermal Paste', 50000.00, 'Pembersihan debu fan laptop dan penggantian thermal paste standar.'),
('HUB 2', '2.3', 'Desain PPT / Poster Kuliah', 35000.00, 'Jasa pembuatan slide presentasi tugas atau desain poster pameran/matakuliah.'),

-- HUB 3: Kategori Domestik & Tenaga (Fixed Price dengan batasan satuan yang terukur)
('HUB 3', '3.1', 'Jasa Cuci Sepatu atau Helm', 25000.00, 'Harga flat pembersihan untuk 1 pasang sepatu sneakers atau 1 buah helm standar.'),
('HUB 3', '3.2', 'Deep Cleaning Kamar Kos', 40000.00, 'Jasa sapu, pel, sikat kamar mandi untuk ukuran kamar maksimal 3x4 meter.'),
('HUB 3', '3.3', 'Jasa Setrika Kiloan', 7000.00, 'Harga jasa setrika per kilogram (minimal order 3 kg).');