# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Veri tabanı ayarları (Render üzerinde kalıcı olması için SQLite dosya yolu)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'parca_ve_esya.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'cok-gizli-bir-anahtar-12345'

db = SQLAlchemy(app)

# ------------------ VERİ TABANI MODELLERİ ------------------

# 1. Kullanıcılar Tablosu (Alıcı ve Esnaf)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telefon = db.Column(db.String(15), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(128), nullable=False)
    ad_soyad = db.Column(db.String(100), nullable=False)
    hesap_tipi = db.Column(db.String(20), nullable=False) # 'alici' veya 'esnaf'
    onayli_esnaf = db.Column(db.Boolean, default=False)
    vergi_no = db.Column(db.String(50), nullable=True)
    dukan_adresi = db.Column(db.Text, nullable=True)
    
    def set_sifre(self, sifre):
        self.sifre_hash = generate_password_hash(sifre)
        
    def sifre_kontrol(self, sifre):
        return check_password_hash(self.sifre_hash, sifre)

# 2. İlanlar Tablosu (Alıcıların Açtığı İlanlar)
class Ilan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alici_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kategori = db.Column(db.String(50), nullable=False) # 'Araç Parçası', 'Aksesuar', 'İkinci El Eşya'
    marka = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(50), nullable=True)
    yil = db.Column(db.Integer, nullable=True)
    detay = db.Column(db.Text, nullable=False)
    il = db.Column(db.String(50), nullable=False)
    ilce = db.Column(db.String(50), nullable=False)
    butce = db.Column(db.String(50), nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    durum = db.Column(db.String(20), default='Aktif') # 'Aktif', 'Tamamlandi'

# 3. Teklifler Tablosu (Esnafların İlanlara Verdiği Teklifler)
class Teklif(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ilan_id = db.Column(db.Integer, db.ForeignKey('ilan.id'), nullable=False)
    esnaf_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fiyat = db.Column(db.Float, nullable=False)
    aciklama = db.Column(db.Text, nullable=False)
    fotograf_url = db.Column(db.String(255), nullable=True)
    durum = db.Column(db.String(20), default='Beklemede') # 'Beklemede', 'Kabul Edildi', 'Reddedildi'

# ------------------ API / URL YÖNLENDİRMELERİ ------------------

@app.route('/')
def home():
    return jsonify({
        "durum": "Calisiyor", 
        "mesaj": "Parca ve Esya Ilan Platformu API Motoru Aktif!"
    })

# Kayıt Olma API'si
@app.route('/api/kayit', methods=['POST'])
def kayit():
    data = request.get_json()
    if not data or 'telefon' not in data or 'sifre' not in data:
        return jsonify({"hata": "Eksik bilgi gönderildi"}), 400
        
    if User.query.filter_by(telefon=data['telefon']).first():
        return jsonify({"hata": "Bu telefon numarası zaten kayıtlı"}), 400
        
    yeni_kullanici = User(
        telefon=data['telefon'],
        ad_soyad=data.get('ad_soyad', ''),
        hesap_tipi=data.get('hesap_tipi', 'alici'),
        vergi_no=data.get('vergi_no', None),
        dukan_adresi=data.get('dukan_adresi', None)
    )
    yeni_kullanici.set_sifre(data['sifre'])
    
    db.session.add(yeni_kullanici)
    db.session.commit()
    return jsonify({"mesaj": "Kullanıcı başarıyla oluşturuldu"}), 201

# Veri tabanını ilk çalıştırmada otomatik oluştur
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
