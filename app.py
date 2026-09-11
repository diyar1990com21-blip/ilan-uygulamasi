import os
from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Kök dizin yolunu sunucuya kesin olarak bildiriyoruz
base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, 'templates'),
    static_folder=os.path.join(base_dir, 'static')
)

# Veritabanı dosya yolu ayarı
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(base_dir, 'ilan_uygulamasi.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kesin_gizli_anahtar_123'

db = SQLAlchemy(app)

# Modeller
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

class Teklif(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ilan_id = db.Column(db.Integer, db.ForeignKey('ilan.id'), nullable=False)
    esnaf_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fiyat = db.Column(db.Float, nullable=False)
    aciklama = db.Column(db.Text, nullable=False)
    durum = db.Column(db.String(20), default='Beklemede')

# Sayfalar
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
        return "Hatalı telefon numarası veya şifre!", 401
    return render_template('login.html')

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
            return "Bu telefon numarası zaten kayıtlı!", 400

        hashed_sifre = generate_password_hash(sifre)
        yeni_kullanici = User(
            telefon=telefon, ad_soyad=ad_soyad, sifre_hash=hashed_sifre,
            hesap_tipi=hesap_turu, vergi_no=vergi_no, dukan_adresi=dukkan_adresi
        )
        db.session.add(yeni_kullanici)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/ilanlar')
def ilanlar_sayfasi():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "<h1>Giriş Başarılı! İlanlar Sayfası Yakında Eklenecek.</h1>"

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
