import os
from flask import Flask, request, redirect, url_for, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kesin_anahtar_123'

# Verileri geçici olarak RAM bellekte saklıyoruz
USERS_DB = {}
ILANLAR_DB = []
TEKLIFLER_DB = []

# Hazır Giriş Bilgileri (Hatasız İngilizce Karakterler)
USERS_DB["05551234567"] = {
    "ad_soyad": "Ahmet Yilmaz",
    "sifre_hash": generate_password_hash("123456"),
    "hesap_tipi": "alici"
}
USERS_DB["05441234567"] = {
    "ad_soyad": "Oto Usta Garaj",
    "sifre_hash": generate_password_hash("123456"),
    "hesap_tipi": "esnaf"
}

# Örnek Başlangıç İlanı
ILANLAR_DB.append({
    "id": 1,
    "ad_soyad": "Ahmet Yilmaz",
    "telefon": "05551234567",
    "kategori": "Kaporta / Far",
    "detay": "2018 model Volkswagen Golf sol on LED far ariyorum. Orijinal cikma parca olmali.",
    "butce": "7.500 TL"
})

# --- TÜM ARAYÜZLER ( PREMIUM KOYU TEMA - CSS İÇİNDE GÖMÜLÜ ) ---
LOGIN_HTML = """
<body style="background:#0b1329; color:white; font-family:sans-serif; display:flex; justify-content:center; align-items:center; min-height:100vh; margin:0; padding:15px;">
    <div style="background:#1c2541; padding:25px; border-radius:16px; width:100%; max-width:440px; box-shadow:0 10px 30px rgba(0,0,0,0.4); border:1px solid #23315a;">
        <h2 style="text-align:center; color:#4cc9f0; margin-bottom:20px;">Ilan Uygulamasi</h2>
        {% if error %}<div style="background:#ff4d4d; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:15px; font-size:14px;">{{ error }}</div>{% endif %}
        <form method="POST" action="/login">
            <div style="margin-bottom:15px;">
                <label style="display:block; margin-bottom:5px; font-size:13px; color:#abc4ff;">Telefon Numarası</label>
                <input type="tel" name="telefon" placeholder="05551234567" required style="width:100%; padding:12px; background:#2a3457; border:none; border-radius:10px; color:white; outline:none;">
            </div>
            <div style="margin-bottom:20px;">
                <label style="display:block; margin-bottom:5px; font-size:13px; color:#abc4ff;">Şifre</label>
                <input type="password" name="sifre" placeholder="••••••" required style="width:100%; padding:12px; background:#2a3457; border:none; border-radius:10px; color:white; outline:none;">
            </div>
            <button type="submit" style="width:100%; padding:14px; background:#4cc9f0; color:#0b1329; border:none; border-radius:10px; font-size:16px; font-weight:bold; cursor:pointer;">Giris Yap</button>
        </form>
        <p style="text-align:center; margin-top:15px; font-size:14px; color:#abc4ff;">Hesabınız yok mu? <a href="/register" style="color:#4cc9f0; text-decoration:none; font-weight:bold;">Kayit Olun</a></p>
    </div>
</body>
"""

REGISTER_HTML = """
<body style="background:#0b1329; color:white; font-family:sans-serif; display:flex; justify-content:center; align-items:center; min-height:100vh; margin:0; padding:15px;">
    <div style="background:#1c2541; padding:25px; border-radius:16px; width:100%; max-width:440px; box-shadow:0 10px 30px rgba(0,0,0,0.4); border:1px solid #23315a;">
        <h2 style="text-align:center; color:#4cc9f0; margin-bottom:20px;">Yeni Hesap Olustur</h2>
        {% if error %}<div style="background:#ff4d4d; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:15px; font-size:14px;">{{ error }}</div>{% endif %}
        <form method="POST" action="/register">
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:5px; font-size:13px; color:#abc4ff;">Telefon Numarası</label>
                <input type="tel" name="telefon" placeholder="05551234567" required style="width:100%; padding:12px; background:#2a3457; border:none; border-radius:10px; color:white; outline:none;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:5px; font-size:13px; color:#abc4ff;">Ad Soyad / Firma Adı</label>
                <input type="text" name="ad_soyad" placeholder="Ahmet Yılmaz" required style="width:100%; padding:12px; background:#2a3457; border:none; border-radius:10px; color:white; outline:none;">
            </div>
            <div style="margin-bottom:12px;">
                <label style="display:block; margin-bottom:5px; font-size:13px; color:#abc4ff;">Şifre</label>
                <input type="password" name="sifre" placeholder="••••••" required style="width:100%; padding:12px; background:#2a3457; border:none; border-radius:10px; color:white; outline:none;">
            </div>
            <div style="margin-bottom:18px;">
                <label style="display:block; margin-bottom:5px; font-size:13px; color:#abc4ff;">Hesap Türü</label>
                <select name="hesap_turu" style="width:100%; padding:12px; background:#2a3457; border:none; border-radius:10px; color:white; outline:none;">
                    <option value="alici">Alıcı (Parça Arayan)</option>
                    <option value="esnaf">Esnaf (Parça Satıcısı / Teklif Veren)</option>
                </select>
            </div>
            <button type="submit" style="width:100%; padding:14px; background:#4cc9f0; color:#0b1329; border:none; border-radius:10px; font-size:16px; font-weight:bold; cursor:pointer;">Kayit Ol</button>
        </form>
        <p style="text-align:center; margin-top:15px; font-size:14px; color:#abc4ff;">Zaten üye misiniz? <a href="/login" style="color:#4cc9f0; text-decoration:none; font-weight:bold;">Giris Yapin</a></p>
    </div>
</body>
"""

ILANLAR_HTML = """
<body style="background:#0b1329; color:white; font-family:sans-serif; display:flex; justify-content:center; padding:20px; margin:0;">
    <div style="width:100%; max-width:650px; background:#1c2541; padding:20px; border-radius:16px; box-shadow:0 10px 30px rgba(0,0,0,0.4); border:1px solid #23315a;">
        <div style="display:flex; justify-content:between; align-items:center; border-bottom:2px solid #2a3457; padding-bottom:15px; margin-bottom:20px;">
            <div style="flex:1;">
                <h3 style="margin:0; color:#4cc9f0; font-size:20px;">Islem Paneli</h3>
                <span style="font-size:11px; color:#4cc9f0; background:rgba(76,201,240,0.1); padding:2px 6px; border-radius:4px; font-weight:bold; display:inline-block; margin-top:4px;">{{ session['hesap_tipi'].upper() }}</span>
            </div>
            <div style="text-align:right;">
                <span style="font-size:14px; color:#abc4ff; display:block; margin-bottom:4px;">👤 {{ session['ad_soyad'] }}</span>
                <a href="/logout" style="color:#ff4d4d; text-decoration:none; font-weight:bold; font-size:13px; background:rgba(255,77,77,0.1); padding:4px 8px; border-radius:4px;">Cikis Yap</a>
            </div>
        </div>

        {% if session['hesap_tipi'] == 'alici' %}
            <form method="POST" action="/yeni-ilan" style="background:#2a3457; padding:15px; border-radius:12px; margin-bottom:20px;">
                <h4 style="margin:0 0 10px 0; color:#4cc9f0; font-size:15px;">➕ Yeni Parca Talebi Olustur</h4>
                <input type="text" name="kategori" placeholder="Parça Adı / Araç Marka Model" required style="width:100%; padding:10px; background:#1c2541; border:none; border-radius:8px; color:white; margin-bottom:10px; outline:none;"><br>
                <input type="text" name="butce" placeholder="Bütçe (Örn: 5000 TL)" required style="width:100%; padding:10px; background:#1c2541; border:none; border-radius:8px; color:white; margin-bottom:10px; outline:none;"><br>
                <textarea name="detay" placeholder="İlan Detayı (Örn: Boyasız olsun, parça kodu...)" required style="width:100%; height:60px; padding:10px; background:#1c2541; border:none; border-radius:8px; color:white; margin-bottom:10px; outline:none; resize:none;"></textarea><br>
                <button type="submit" style="width:100%; padding:10px; background:#4cc9f0; color:#0b1329; border:none; border-radius:8px; font-weight:bold; cursor:pointer;">Ilan Yayınla</button>
            </form>
        {% endif %}

        <h3 style="text-align:left; font-size:16px; margin-bottom:15px; color:#abc4ff; border-bottom:1px solid #2a3457; padding-bottom:5px;">Aktif Parça Talepleri</h3>
        
        {% if not ilanlar %}
            <p style="color:#abc4ff; text-align:center; font-size:14px; padding:15px;">Henüz aktif ilan bulunmuyor.</p>
        {% endif %}

        {% for ilan in ilanlar %}
            <div style="background:#0b1329; padding:15px; border-radius:12px; margin-bottom:15px; border:1px solid #2a3457;">
                <div style="display:flex; justify-content:between; color:#4cc9f0; font-weight:bold; margin-bottom:8px; font-size:15px;">
                    <span>🔧 {{ ilan.kategori }}</span>
                    <span style="color:#52b788;">💰 {{ ilan.butce }}</span>
                </div>
                <p style="font-size:14px; background:#1c2541; padding:10px; border-radius:6px; line-height:1.4; margin:5px 0 8px 0;">{{ ilan.detay }}</p>
                <p style="font-size:11px; color:#abc4ff; margin:0;">📣 İlan Sahibi: {{ ilan.ad_soyad }}</p>
                
                <!-- Teklif Bölümü -->
                <div style="margin-top:12px; border-top:1px dashed #2a3457; padding-top:10px;">
                    <div style="color:#abc4ff; font-size:12px; font-weight:bold; margin-bottom:6px;">GELEN TEKLİFLER</div>
                    {% set ilan_teklifleri = [] %}
                    {% for teklif in teklifler %}
                        {% if teklif.ilan_id == ilan.id %}
                            <div style="background:#2a3457; padding:8px 12px; border-radius:6px; margin-bottom:5px; display:flex; justify-content:between; align-items:center; font-size:13px;">
