import os
from flask import Flask, request, redirect, url_for, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ilan_uygulamasi_tam_ve_eksiksiz_gizli_anahtar_998877'

# ==========================================
# 🗄️ RAM TABANLI VERİ SİSTEMİ (SIFIR KİLİTLENME)
# ==========================================
USERS_DB = {}
ILANLAR_DB = []
TEKLIFLER_DB = []

# --- Hazır Test Kullanıcıları ---
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

# --- Örnek Başlangıç İlanı ---
ILANLAR_DB.append({
    "id": 1,
    "ad_soyad": "Ahmet Yilmaz",
    "telefon": "05551234567",
    "kategori": "Kaporta / Far",
    "detay": "2018 model Volkswagen Golf sol ön LED far arıyorum. Orijinal çıkma parça olmalı.",
    "butce": "7.500 TL"
})

# ==========================================
# 🎨 PREMIUM COMFORT DARK TEMPLATE TASARIMLARI
# ==========================================

# Ortak CSS Stil Dosyası Gömülü
ORTAK_CSS = """
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: #0b1329; color: #ffffff; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 15px; }
    .card { background-color: #1c2541; padding: 25px; border-radius: 16px; width: 100%; max-width: 550px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); border: 1px solid #23315a; }
    .panel-card { background-color: #1c2541; padding: 25px; border-radius: 16px; width: 100%; max-width: 700px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); border: 1px solid #23315a; }
    h2, h3 { text-align: center; margin-bottom: 20px; color: #4cc9f0; font-weight: 700; }
    .input-group { margin-bottom: 16px; }
    label { display: block; margin-bottom: 6px; font-size: 13px; color: #abc4ff; font-weight: 500; }
    input, select, textarea { width: 100%; padding: 12px 14px; background-color: #2a3457; border: 2px solid transparent; border-radius: 10px; color: #ffffff; font-size: 15px; outline: none; transition: all 0.2s; }
    input:focus, select:focus, textarea:focus { border-color: #4cc9f0; background-color: #1c2541; }
    textarea { height: 75px; resize: none; }
    .main-btn { width: 100%; padding: 14px; background-color: #4cc9f0; color: #0b1329; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; transition: all 0.2s; margin-top: 5px; }
    .main-btn:hover { background-color: #4361ee; color: white; }
    .footer-text { text-align: center; margin-top: 18px; font-size: 14px; color: #abc4ff; }
    .footer-text a { color: #4cc9f0; text-decoration: none; font-weight: bold; }
    .error-msg { background-color: #ff4d4d; color: white; padding: 12px; border-radius: 8px; text-align: center; margin-bottom: 15px; font-size: 14px; font-weight: bold; }
    .header-panel { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2a3457; padding-bottom: 15px; margin-bottom: 20px; }
    .logout-link { color: #ff4d4d; text-decoration: none; font-weight: bold; font-size: 14px; background: rgba(255,77,77,0.1); padding: 6px 12px; border-radius: 6px; }
    .logout-link:hover { background: #ff4d4d; color: white; }
    .ilan-box { background: #0b1329; padding: 18px; border-radius: 12px; margin-bottom: 18px; border: 1px solid #2a3457; }
    .ilan-top { display: flex; justify-content: space-between; color: #4cc9f0; font-weight: bold; margin-bottom: 8px; font-size: 16px; }
    .teklif-title { margin: 12px 0 6px 0; color: #abc4ff; font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
    .teklif-box { background: #2a3457; padding: 10px 14px; border-radius: 8px; margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
    .teklif-form { display: flex; gap: 8px; margin-top: 12px; border-top: 1px dashed #2a3457; padding-top: 12px; }
</style>
"""

LOGIN_HTML = ORTAK_CSS + """
<div class="card">
    <h2>İlan Uygulaması</h2>
    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
    <form method="POST" action="/login">
        <div class="input-group">
            <label>Telefon Numarası</label>
            <input type="tel" name="telefon" placeholder="Örn: 05551234567" required>
        </div>
        <div class="input-group">
            <label>Şifre</label>
            <input type="password" name="sifre" placeholder="••••••" required>
        </div>
        <button type="submit" class="main-btn">Güvenli Giriş Yap</button>
    </form>
    <div class="footer-text">Hesabınız yok mu? <a href="/register">Hemen Kayıt Olun</a></div>
</div>
"""

REGISTER_HTML = ORTAK_CSS + """
<div class="card">
    <h2>Yeni Hesap Oluştur</h2>
    {% if error %}<div class="error-msg">{{ error }}</div>{% endif %}
    <form method="POST" action="/register">
        <div class="input-group">
            <label>Telefon Numarası</label>
            <input type="tel" name="telefon" placeholder="Örn: 05551234567" required>
        </div>
        <div class="input-group">
            <label>Ad Soyad / Firma Ünvanı</label>
            <input type="text" name="ad_soyad" placeholder="Örn: Ahmet Yılmaz" required>
        </div>
        <div class="input-group">
            <label>Giriş Şifreniz</label>
            <input type="password" name="sifre" placeholder="••••••" required>
        </div>
        <div class="input-group">
            <label>Hesap Türü Seçimi</label>
            <select name="hesap_turu">
                <option value="alici">Alıcı (Yedek Parça Arayan)</option>
                <option value="esnaf">Esnaf (Yedek Parça Satıcısı / Teklif Veren)</option>
            </select>
        </div>
        <button type="submit" class="main-btn">Kayıt İşlemini Tamamla</button>
    </form>
    <div class="footer-text">Zaten üye misiniz? <a href="/login">Giriş Yapın</a></div>
</div>
"""

ILANLAR_HTML = ORTAK_CSS + """
<div class="panel-card">
    <div class="header-panel">
        <div>
            <h3 style="text-align:left; margin:0; font-size:22px;">Yedek Parça İşlem Paneli</h3>
            <span style="font-size:12px; color:#4cc9f0; background:rgba(76,201,240,0.1); padding:3px 8px; border-radius:4px; font-weight:bold; margin-top:4px; display:inline-block;">
                YETKİ: {{ session['hesap_tipi'].upper() }}
            </span>
        </div>
        <div style="text-align:right;">
            <span style="font-size:14px; color:#abc4ff; display:block; margin-bottom:5px;">👤 {{ session['ad_soyad'] }}</span>
            <a href="/logout" class="logout-link">Güvenli Çıkış</a>
        </div>
    </div>
    
    {% if session['hesap_tipi'] == 'alici' %}
        <form method="POST" action="/yeni-ilan" style="background:#2a3457; padding:20px; border-radius:12px; margin-bottom:25px; border:1px solid #334273;">
            <h4 style="margin-bottom:12px; color:#4cc9f0;">➕ Yeni Parça İhtiyaç İlanı Ver</h4>
            <div class="input-group">
                <input type="text" name="kategori" placeholder="Parça Adı / Araç Marka Model (Örn: Golf 7 Ön Tampon)" required>
            </div>
            <div class="input-group">
                <input type="text" name="butce" placeholder="Ayırdığınız Tahmini Bütçe (Örn: 5.000 TL)" required>
            </div>
            <div class="input-group">
                <textarea name="detay" placeholder="Aradığınız parçanın detaylarını yazın (Örn: Boyasız hatasız olsun, parça kodu...)" required></textarea>
            </div>
            <button type="submit" class="main-btn" style="padding:10px;">Talebi Yayınla</button>
        </form>
    {% endif %}

    <h3 style="text-align:left; font-size:18px; margin-bottom:15px; border-bottom:1px solid #2a3457; padding-bottom:8px; color:#abc4ff;">Aktif Parça Talepleri</h3>
    
    {% if not ilanlar %}
        <p style="color:#abc4ff; font-size:14px; text-align:center; padding:20px;">Henüz sistemde aktif ilan bulunmuyor.</p>
    {% endif %}

    {% for ilan in ilanlar %}
        <div class="ilan-box">
            <div class="ilan-top">
                <span>🔧 {{ ilan.kategori }}</span>
                <span style="color:#52b788;">💰 {{ ilan.butce }}</span>
            </div>
            <p style="font-size:14px; color:#ffffff; line-height:1.4; margin-bottom:10px; background:#1c2541; padding:10px; border-radius:6px;">
                {{ ilan.detay }}
            </p>
            <p style="font-size:11px; color:#abc4ff;">📣 İlan Sahibi: {{ ilan.ad_soyad }}</p>
            
            <!-- Tekliflerin Listelenmesi -->
            <div style="margin-top:15px;">
                <div class="teklif-title">Gelen Fiyat Teklifleri</div>
                {% set ilan_teklifleri = [] %}
                {% for teklif in teklifler %}
                    {% if teklif.ilan_id == ilan.id %}
                        <div class="teklif-box">
                            <span>🛠️ <b>{{ teklif.esnaf_adi }}</b>: {{ teklif.aciklama }}</span>
                            <span style="color:#52b788; font-weight:bold; font-size:15px;">{{ teklif.fiyat }} TL</span>
                        </div>
                        {% set _ = ilan_teklifleri.append(1) %}
                    {% endif %}
                {% endfor %}
                {% if ilan_teklifleri|length == 0 %}
                    <p style="font-size:12px; color:#abc4ff; font-style:italic; padding-left:5px;">Henüz teklif verilmedi.</p>
                {% endif %}
            </div>

            <!-- Esnaflar İçin Teklif Verme Formu -->
            {% if session['hesap_tipi'] == 'esnaf' %}
                <form method="POST" action="/teklif-ver/{{ ilan.id }}" class="teklif-form">
