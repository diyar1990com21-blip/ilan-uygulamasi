import os
from flask import Flask, request, redirect, url_for, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kesin_gizli_anahtar_123'

# ==========================================
# 🗄️ GEÇİCİ BELLEK VERİ SİSTEMİ (Render İzin Sorunlarını Aşmak İçin)
# ==========================================
# Sunucu izinlerine takılmamak için kullanıcıları RAM bellekte saklıyoruz
USERS_DB = {}

# Test için varsayılan bir kullanıcı ekleyelim (Telefon: 05551234567 | Şifre: 123456)
USERS_DB["05551234567"] = {
    "ad_soyad": "Ahmet Yılmaz",
    "sifre_hash": generate_password_hash("123456"),
    "hesap_tipi": "alici",
    "vergi_no": None,
    "dukan_adresi": None
}

# ==========================================
# 🎨 GÜVENLİ TASARIM ŞABLONLARI
# ==========================================

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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

# ==========================================
# 🛣️ SAYFA YÖNLENDİRMELERİ (ROUTES)
# ==========================================

@app.route('/')
def home():
    if 'telefon' in session:
        return redirect(url_for('ilanlar_sayfasi'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        telefon = request.form.get('telefon')
        sifre = request.form.get('sifre')
        
        user = USERS_DB.get(telefon)
        if user and check_password_hash(user["sifre_hash"], sifre):
            session['telefon'] = telefon
            session['ad_soyad'] = user["ad_soyad"]
            return redirect(url_for('ilanlar_sayfasi'))
            
        return render_template_string(LOGIN_HTML, error="Hatalı telefon veya şifre!")
        
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        telefon = request.form.get('telefon')
        ad_soyad = request.form.get('ad_soyad')
        sifre = request.form.get('sifre')
        hesap_turu = request.form.get('hesap_turu')
        vergi_no = request.form.get('vergi_no')
        dukkan_adresi = request.form.get('dukkan_adresi')

        if telefon in USERS_DB:
            return render_template_string(REGISTER_HTML, error="Bu telefon numarası zaten kayıtlı!")

        # Belleğe güvenli bir şekilde kaydediyoruz
        USERS_DB[telefon] = {
            "ad_soyad": ad_soyad,
            "sifre_hash": generate_password_hash(sifre),
            "hesap_tipi": hesap_turu,
            "vergi_no": vergi_no if hesap_turu == 'esnaf' else None,
            "dukan_adresi": dukkan_adresi if hesap_turu == 'esnaf' else None
        }
        return redirect(url_for('login'))
        
    return render_template_string(REGISTER_HTML)

@app.route('/ilanlar')
def ilanlar_sayfasi():
    if 'telefon' not in session:
        return redirect(url_for('login'))
    return f"<body style='background-color:#0b1329; color:white; font-family:sans-serif; padding:30px;'><h1>Giriş Başarılı!</h1><h2>Hoş geldiniz, {session.get('ad_soyad')}</h2><p>İlanlar Sayfası ve panel fonksiyonları yakında eklenecek.</p><br><a href='/logout' style='color:#4cc9f0; text-decoration:none; font-weight:bold;'>Çıkış Yap</a></body>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
