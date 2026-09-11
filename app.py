import os
from flask import Flask, request, redirect, url_for, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kesin_gizli_anahtar_123'

# ==========================================
# 🗄️ GEÇİCİ BELLEK VERİ SİSTEMİ (RAM)
# ==========================================
USERS_DB = {}
ILANLAR_DB = []
TEKLIFLER_DB = []

# --- Test İçin Hazır Veriler ---
# 1. Alıcı Kullanıcı
USERS_DB["05551234567"] = {
    "ad_soyad": "Ahmet Yılmaz",
    "sifre_hash": generate_password_hash("123456"),
    "hesap_tipi": "alici",
    "vergi_no": None,
    "dukan_adresi": None
}
# 2. Esnaf Kullanıcı
USERS_DB["05441234567"] = {
    "ad_soyad": "Oto Garaj Ustası",
    "sifre_hash": generate_password_hash("123456"),
    "hesap_tipi": "esnaf",
    "vergi_no": "12345678",
    "dukan_adresi": "Sanayi Sitesi No: 12"
}
# 3. Örnek İlan
ILANLAR_DB.append({
    "id": 1,
    "alici_id": "05551234567",
    "ad_soyad": "Ahmet Yılmaz",
    "kategori": "Oto Yedek Parça",
    "marka": "Toyota",
    "model": "Corolla",
    "yil": "2015",
    "detay": "Sağ ön çamurluk ve far ihtiyacım var. Orijinal çıkma parça arıyorum.",
    "il": "Bursa",
    "ilce": "Osmangazi",
    "butce": "5000 TL"
})

# ==========================================
# 🎨 GÜVENLİ TASARIM ŞABLONLARI
# ==========================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Giriş Yap - İlan Uygulaması</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
        body { background-color: #0b1329; color: #ffffff; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .card { background-color: #1c2541; padding: 30px; border-radius: 16px; width: 100%; max-width: 440px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }
        h2 { text-align: center; margin-bottom: 25px; color: #4cc9f0; }
        .input-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #abc4ff; }
        input { width: 100%; padding: 12px 16px; background-color: #3a506b; border: 2px solid transparent; border-radius: 8px; color: #ffffff; font-size: 15px; outline: none; }
        input:focus { border-color: #4cc9f0; }
        .main-btn { width: 100%; padding: 14px; background-color: #4cc9f0; color: #0b1329; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .footer-text { text-align: center; margin-top: 20px; font-size: 14px; color: #abc4ff; }
        .footer-text a { color: #4cc9f0; text-decoration: none; font-weight: bold; }
        .error-msg { background-color: #ff4d4d; color: white; padding: 10px; border-radius: 6px; text-align: center; margin-bottom: 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>İlan Uygulaması</h2>
        {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
        <form action="/login" method="POST">
            <div class="input-group">
                <label>Telefon Numarası</label>
                <input type="tel" name="telefon" placeholder="05551234567" required>
            </div>
            <div class="input-group">
                <label>Şifre</label>
                <input type="password" name="sifre" placeholder="••••••" required>
            </div>
            <button type="submit" class="main-btn">Giriş Yap</button>
        </form>
        <div class="footer-text">Hesabınız yok mu? <a href="/register">Kayıt Olun</a></div>
    </div>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kayıt Ol - İlan Uygulaması</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
        body { background-color: #0b1329; color: #ffffff; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 20px; }
        .card { background-color: #1c2541; padding: 30px; border-radius: 16px; width: 100%; max-width: 440px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }
        h2 { text-align: center; margin-bottom: 25px; color: #4cc9f0; }
        .input-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 8px; font-size: 14px; color: #abc4ff; }
        input, textarea { width: 100%; padding: 12px 16px; background-color: #3a506b; border: 2px solid transparent; border-radius: 8px; color: #ffffff; font-size: 15px; outline: none; }
        input:focus, textarea:focus { border-color: #4cc9f0; }
        textarea { height: 70px; resize: none; }
        .radio-group { display: flex; gap: 20px; background: #3a506b; padding: 12px; border-radius: 8px; margin-top: 5px; }
        .radio-group label { display: flex; align-items: center; gap: 6px; color: white; cursor: pointer; margin: 0; }
        .main-btn { width: 100%; padding: 14px; background-color: #4cc9f0; color: #0b1329; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .footer-text { text-align: center; margin-top: 20px; font-size: 14px; color: #abc4ff; }
        .footer-text a { color: #4cc9f0; text-decoration: none; font-weight: bold; }
        .error-msg { background-color: #ff4d4d; color: white; padding: 10px; border-radius: 6px; text-align: center; margin-bottom: 15px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Hesap Oluştur</h2>
        {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
        <form action="/register" method="POST">
            <div class="input-group">
                <label>Telefon Numarası</label>
                <input type="tel" name="telefon" placeholder="05551234567" required>
            </div>
            <div class="input-group">
                <label>Ad Soyad / Firma Adı</label>
                <input type="text" name="ad_soyad" placeholder="Ahmet Yılmaz" required>
            </div>
            <div class="input-group">
                <label>Şifre</label>
                <input type="password" name="sifre" placeholder="••••••" required>
            </div>
            <div class="input-group">
                <label>Hesap Türü</label>
                <div class="radio-group">
                    <label><input type="radio" name="hesap_turu" value="alici" checked onclick="toggleEsnaf(false)"> Alıcı</label>
                    <label><input type="radio" name="hesap_turu" value="esnaf" onclick="toggleEsnaf(true)"> Esnaf</label>
                </div>
            </div>
            
            <div id="esnaf-alanlari" style="display: none;">
                <div class="input-group">
                    <label>Vergi Numarası</label>
                    <input type="text" name="vergi_no" placeholder="1234567890">
                </div>
                <div class="input-group">
                    <label>Dükkan Adresi</label>
                    <textarea name="dukkan_adresi" placeholder="Sanayi Sitesi No: 5..."></textarea>
                </div>
            </div>

            <button type="submit" class="main-btn">Kayıt Ol</button>
        </form>
        <div class="footer-text">Zaten üye misiniz? <a href="/login">Giriş Yapın</a></div>
    </div>

    <script>
        function toggleEsnaf(show) {
            document.getElementById('esnaf-alanlari').style.display = show ? 'block' : 'none';
        }
    </script>
</body>
</html>
"""

ILANLAR_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>İlanlar Paneli - İlan Uygulaması</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
        body { background-color: #0b1329; color: #ffffff; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid #1c2541; padding-bottom: 15px; }
        .header h1 { color: #4cc9f0; font-size: 24px; }
        .user-info { font-size: 14px; color: #abc4ff; text-align: right; }
        .logout-btn { color: #ff4d4d; text-decoration: none; margin-left: 10px; font-weight: bold; }
        .action-btn { display: inline-block; background-color: #4cc9f0; color: #0b1329; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-bottom: 20px; }
        .ilan-card { background-color: #1c2541; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .ilan-header { display: flex; justify-content: space-between; color: #4cc9f0; font-weight: bold; margin-bottom: 10px; border-bottom: 1px dashed #3a506b; padding-bottom: 5px; }
        .ilan-info { font-size: 14px; color: #abc4ff; margin-bottom: 10px; display: flex; gap: 15px; }
        .ilan-detay { background-color: #0b1329; padding: 12px; border-radius: 6px; font-size: 15px; line-height: 1.5; margin-bottom: 15px; }
        .teklif-section { border-top: 1px solid #3a506b; padding-top: 10px; }
        .teklif-item { background: #3a506b; padding: 8px 12px; border-radius: 6px; margin-bottom: 5px; font-size: 14px; display: flex; justify-content: space-between; }
        .teklif-form input { padding: 10px; background: #3a506b; border: none; border-radius: 6px; color: white; width: 130px; outline: none; }
        .teklif-form button { padding: 10px 15px; background: #4cc9f0; border: none; border-radius: 6px; color: #0b1329; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
