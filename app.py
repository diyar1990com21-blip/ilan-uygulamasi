import os
from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Render ve Yerel ortamda sorunsuz çalışacak veritabanı ve gizli anahtar ayarları
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/ilan.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ilan_uygulamasi_cok_gizli_anahtar_123'

db = SQLAlchemy(app)

# ==========================================
# 🗄️ VERİTABANI MODELLERİ
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telefon = db.Column(db.String(15), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(128), nullable=False)
    ad_soyad = db.Column(db.String(100), nullable=False)
    hesap_tipi = db.Column(db.String(20), nullable=False) # 'alici' veya 'esnaf'
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

class Teklif(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ilan_id = db.Column(db.Integer, db.ForeignKey('ilan.id'), nullable=False)
    esnaf_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fiyat = db.Column(db.Float, nullable=False)
    aciklama = db.Column(db.Text, nullable=False)
    durum = db.Column(db.String(20), default='Beklemede')

# ==========================================
# 🛣️ SAYFA YÖNLENDİRMELERİ (ROUTES)
# ==========================================

# Ana Sayfa Kontrolü
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('ilanlar_sayfasi'))
    return redirect(url_for('login'))

# Giriş Yap Sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        telefon = request.form.get('telefon')
        sifre = request.form.get('sifre')
        
        user = User.query.filter_by(telefon=telefon).first()
        
        if user and check_password_hash(user.sifre_hash, sifre):
            session['user_id'] = user.id
            session['ad_soyad'] = user.ad_soyad
            session['hesap_tipi'] = user.hesap_tipi
            return redirect(url_for('ilanlar_sayfasi'))
        
        return "Hatalı telefon numarası veya şifre! Lütfen tekrar deneyin.", 401
        
    return render_template('login.html')

# Kayıt Ol Sayfası
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        telefon = request.form.get('telefon')
        ad_soyad = request.form.get('ad_soyad')
        sifre = request.form.get('sifre')
        hesap_turu = request.form.get('hesap_turu')
        vergi_no = request.form.get('vergi_no')
        dukkan_adresi = request.form.get('dukkan_adresi')

        if not telefon or not sifre or not ad_soyad:
            return "Lütfen zorunlu alanları doldurun!", 400

        if User.query.filter_by(telefon=telefon).first():
            return "Bu telefon numarası zaten sisteme kayıtlı!", 400

        # Güvenli şifreleme metodu
        hashed_sifre = generate_password_hash(sifre)
        
        yeni_kullanici = User(
            telefon=telefon,
            ad_soyad=ad_soyad,
            sifre_hash=hashed_sifre,
            hesap_tipi=hesap_turu,
            vergi_no=vergi_no if hesap_turu == 'esnaf' else None,
            dukan_adresi=dukkan_adresi if hesap_turu == 'esnaf' else None
        )
        
        db.session.add(yeni_kullanici)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template('register.html')

# İlanlar Paneli (Dashboard)
@app.route('/ilanlar')
def ilanlar_sayfasi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    tum_ilanlar = Ilan.query.all()
    # Eğer templates içinde ilanlar.html varsa onu açar, yoksa genel dashboard şablonunu tetikler
    try:
        return render_template('ilanlar.html', ilanlar=tum_ilanlar)
    except:
        return render_template('dashboard.html', ilanlar=tum_ilanlar)

# Güvenli Çıkış Yapma
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==========================================
# 🛠️ VERİTABANI BAŞLATMA VE PORT AYARLARI
# ==========================================

# Veritabanı tablolarını otomatik ayağa kaldırır
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    # Render için PORT ortam değişkenini dinamik olarak çeker
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
