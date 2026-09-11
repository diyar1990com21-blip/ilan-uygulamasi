import os
from flask import Flask, request, redirect, url_for, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'ilan_uygulamasi.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kesin_gizli_anahtar_123'

db = SQLAlchemy(app)

# ==========================================
# 🗄️ VERİTABANI MODELLERİ
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telefon = db.Column(db.String(15), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(128), nullable=False)
    ad_soyad = db.Column(db.String(100), nullable=False)
    hesap_tipi = db.Column(db.String(20), nullable=False)
    onayli_esnaf = db.Column(db.Boolean, default=False)
    vergi_no = db.Column(db.String(50), nullable=True)
    dukan_adresi = db.Column(db.Text, nullable=True)

class Ilan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alici_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    marka = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=True)
    yil = db.Column(db.Integer, nullable=True)
    detay = db.Column(db.Text, nullable=False)
    il = db.Column(db.String(50), nullable=False)
    ilce = db.Column(db.String(50), nullable=False)
    butce = db.Column(db.String(50), nullable=False)

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
    if 'user_id' in session:
        return redirect(url_for('ilanlar_sayfasi'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        telefon = request.form.get('telefon')
        sifre = request.form.get('sifre')
        
        user = User.query.filter_by(telefon=telefon).first()
        if user and check_password_hash(user.sifre_hash, sifre):
            session['user_id'] = user.id
            session['ad_soyad'] = user.ad_soyad
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

        if User.query.filter_by(telefon=telefon).first():
            return render_template_string(REGISTER_HTML, error="Bu telefon numarası zaten kayıtlı!")

        hashed_sifre = generate_password_hash(sifre)
        yeni_kullanici = User(
            telefon=telefon, ad_soyad=ad_soyad, sifre_hash=hashed_sifre,
            hesap_tipi=hesap_turu, vergi_no=vergi_no, dukan_adresi=dukkan_adresi
        )
        db.session.add(yeni_kullanici)
        db.session.commit()
        return redirect(url_for('login'))
        
