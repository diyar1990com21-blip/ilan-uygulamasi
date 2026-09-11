import os
from flask import Flask, request, redirect, url_for, session, render_template_string

app = Flask(__name__)
app.config['SECRET_KEY'] = 'profesyonel_pazar_yeri_kesin_anahtar_998877'

# --- GELİŞMİŞ RAM VERİ TABANI (PROFESYONEL VERİ YAPISI) ---
USERS_DB = {}
ILANLAR_DB = []
TEKLIFLER_DB = []

# Hazır Profesyonel Test Verileri
USERS_DB["05551234567"] = {"ad_soyad": "Can Yılmaz", "sifre": "123456", "hesap_tipi": "kullanici"}
USERS_DB["05441234567"] = {"ad_soyad": "Yıldız Oto Premium Garaj", "sifre": "123456", "hesap_tipi": "esnaf"}

ILANLAR_DB.append({
    "id": 1,
    "tur": "oto_yedek_parca",
    "ad_soyad": "Can Yılmaz",
    "marka": "Volkswagen",
    "model": "Golf",
    "yil": "2018",
    "kasa_tipi": "Hatchback (5 Kapı)",
    "motor": "1.6 TDI",
    "paket": "Comfortline",
    "parca_kategori": "Aydınlatma / Far Grubu",
    "detay": "Sol ön Bi-Xenon LED far ihtiyacım var. Tamir görmemiş, orijinal çıkma arıyorum.",
    "konum": "Bursa / Osmangazi",
    "harita_link": "https://google.com",
    "butce": "12.500 TL"
})

# ==========================================
# 🎨 GÖMÜLÜ MODULAR HTML ŞABLONLARI
# ==========================================

NAVBAR = """
<nav class="navbar navbar-expand-lg navbar-dark bg-dark border-bottom border-secondary mb-4">
    <div class="container">
        <a class="navbar-brand text-info fw-bold" href="/ilanlar">⚙️ PRO-PAZAR</a>
        <div class="d-flex align-items-center">
            <span class="text-light me-3 small">👤 {{ session['ad_soyad'] }} ({{ session['hesap_tipi'].upper() }})</span>
            <a href="/logout" class="btn btn-sm btn-outline-danger fw-bold">Çıkış Yap</a>
        </div>
    </div>
</nav>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giriş Yap - ProPazar</title>
    <link href="https://jsdelivr.net" rel="stylesheet">
    <style>body{background-color:#0f172a; color:#f8fafc; min-height:100vh; display:flex; align-items:center;}</style>
</head>
<body>
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-5">
            <div class="card bg-secondary text-white border-0 shadow-lg p-4" style="background-color:#1e293b !important;">
                <h2 class="text-center text-info fw-bold mb-2">PRO-PAZAR</h2>
                <p class="text-center text-muted small mb-4">Oto Parça & İkinci El Eşya Profesyonel Otomasyonu</p>
                {% if error %}<div class="alert alert-danger p-2 text-center small">{{ error }}</div>{% endif %}
                <form method="POST" action="/login">
                    <div class="mb-3"><label class="form-label small text-info">Telefon Numarası</label><input type="tel" name="telefon" class="form-control bg-dark text-white border-0" placeholder="05551234567" required></div>
                    <div class="mb-4"><label class="form-label small text-info">Şifre</label><input type="password" name="sifre" class="form-control bg-dark text-white border-0" placeholder="••••••" required></div>
                    <button type="submit" class="btn btn-info w-100 fw-bold text-dark">Sisteme Güvenli Giriş Yap</button>
                </form>
                <p class="text-center mt-3 small mb-0">Hesabınız yok mu? <a href="/register" class="text-info text-decoration-none fw-bold">Hemen Kayıt Olun</a></p>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kayıt Ol - ProPazar</title>
    <link href="https://jsdelivr.net" rel="stylesheet">
    <style>body{background-color:#0f172a; color:#f8fafc; min-height:100vh; display:flex; align-items:center; padding:20px 0;}</style>
</head>
<body>
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card bg-secondary text-white border-0 shadow-lg p-4" style="background-color:#1e293b !important;">
                <h3 class="text-center text-info fw-bold mb-4">Yeni Kurumsal / Bireysel Hesap</h3>
                <form method="POST" action="/register">
                    <div class="mb-3"><label class="form-label small text-info">Telefon Numarası</label><input type="tel" name="telefon" class="form-control bg-dark text-white border-0" required></div>
                    <div class="mb-3"><label class="form-label small text-info">Ad Soyad / Firma Ünvanı</label><input type="text" name="ad_soyad" class="form-control bg-dark text-white border-0" required></div>
                    <div class="mb-3"><label class="form-label small text-info">Güvenlik Şifresi</label><input type="password" name="sifre" class="form-control bg-dark text-white border-0" required></div>
                    <div class="mb-4">
                        <label class="form-label small text-info">Hesap Rolü</label>
                        <select name="hesap_turu" class="form-select bg-dark text-white border-0">
                            <option value="kullanici">Bireysel Kullanıcı (İlan Veren / Parça Arayan)</option>
                            <option value="esnaf">Esnaf / Spotçu / Çıkmacı (Teklif Veren)</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-info w-100 fw-bold text-dark">Kayıt İşlemini Tamamla</button>
                </form>
                <p class="text-center mt-3 small mb-0">Zaten üye misiniz? <a href="/login" class="text-info text-decoration-none fw-bold">Giriş Yapın</a></p>
            </div>
        </div>
    </div>
</div>
</body>
</html>
"""

ILANLAR_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>İşlem Paneli - ProPazar</title>
    <link href="https://jsdelivr.net" rel="stylesheet">
    <style>body{background-color:#0f172a; color:#f8fafc;}.card{background-color:#1e293b; border:1px solid #334155;}</style>
</head>
<body>
""" + NAVBAR + """
<div class="container mb-5">
    <div class="row">
        <!-- İLAN VERME FORMU PANELİ (Sadece normal kullanıcılar görebilir) -->
        {% if session['hesap_tipi'] == 'kullanici' %}
        <div class="col-lg-5 mb-4">
            <div class="card p-4 text-white shadow">
                <h4 class="text-info fw-bold mb-3">➕ Profesyonel İlan Girişi</h4>
                
                <!-- Kategori Seçimi Kontrolü (JS ile form değişir) -->
                <div class="mb-3">
                    <label class="form-label small text-muted">Yayın Kategorisi</label>
                    <select id="kategoriSecici" onchange="switchForm()" class="form-select bg-dark text-white border-0">
                        <option value="oto">🚗 Oto Yedek Parça Talebi</option>
                        <option value="esya">📺 İkinci El Eşya Satış İlanı</option>
                    </select>
                </div>

                <form method="POST" action="/yeni-ilan">
                    <input type="hidden" id="form_turu" name="tur" value="oto_yedek_parca">

                    <!-- OTO YEDEK PARÇA DETAY FORMU -->
                    <div id="otoFormu">
                        <div class="row g-2 mb-2">
                            <div class="col"><input type="text" name="marka" class="form-control bg-dark text-white border-0 small" placeholder="Marka (Örn: BMW)"></div>
                            <div class="col"><input type="text" name="model" class="form-control bg-dark text-white border-0 small" placeholder="Model (Örn: 3 Serisi)"></div>
                        </div>
                        <div class="row g-2 mb-2">
                            <div class="col"><input type="number" name="yil" class="form-control bg-dark text-white border-0 small" placeholder="Yıl (Örn: 2016)"></div>
                            <div class="col"><input type="text" name="kasa_tipi" class="form-control bg-dark text-white border-0 small" placeholder="Kasa (Örn: Sedan F30)"></div>
                        </div>
                        <div class="row g-2 mb-2">
                            <div class="col"><input type="text" name="motor" class="form-control bg-dark text-white border-0 small" placeholder="Motor (Örn: 320d / 2.0)"></div>
                            <div class="col"><input type="text" name="paket" class="form-control bg-dark text-white border-0 small" placeholder="Paket (Örn: M Sport)"></div>
                        </div>
                        <div class="mb-3">
                            <select name="parca_kategori" class="form-select bg-dark text-white border-0 small">
                                <option value="Motor Mekanik">Motor Mekanik Parçaları</option>
                                <option value="Kaporta / Karoser">Kaporta / Karoser / Çamurluk</option>
                                <option value="Aydınlatma / Far Grubu">Aydınlatma / Far / Stop Grubu</option>
                                <option value="Şanzıman / Aktarma">Şanzıman / Aktarma Organları</option>
                            </select>
                        </div>
                    </div>

                    <!-- İKİNCİ EL EŞYA DETAY FORMU (Varsayılan Gizli) -->
                    <div id="esyaFormu" style="display:none;">
                        <div class="mb-2">
                            <select name="esya_kategori" class="form-select bg-dark text-white border-0 small">
                                <option value="Beyaz Eşya">Beyaz Eşya (Buzdolabı, Çamaşır M.)</option>
                                <option value="Mobilya / Ev Tekstili">Mobilya / Koltuk / Masa</option>
