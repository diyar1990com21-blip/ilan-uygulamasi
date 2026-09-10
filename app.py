# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Render sunucusunda klasör izin hatası almamak için veri tabanını /tmp altına taşıdık
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/parca_ve_esya.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'cok-gizli-bir-anahtar-12345'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Model.dataclass if hasattr(db.Model, 'dataclass') else db.Column(db.Integer, primary_key=True)
    id = db.Column(db.Integer, primary_key=True)
    telefon = db.Column(db.String(15), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(128), nullable=False)
    ad_soyad = db.Column(db.String(100), nullable=False)
    hesap_tipi = db.Column(db.String(20), nullable=False)
    onayli_esnaf = db.Column(db.Boolean, default=False)
    vergi_no = db.Column(db.String(50), nullable=True)
    dukan_adresi = db.Column(db.Text, nullable=True)
    
    def set_sifre(self, sifre):
        self.sifre_hash = generate_password_hash(sifre)
        
    def sifre_kontrol(self, sifre):
        return check_password_hash(self.sifre_hash, sifre)

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
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    durum = db.Column(db.String(20), default='Aktif')

class Teklif(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ilan_id = db.Column(db.Integer, db.ForeignKey('ilan.id'), nullable=False)
    esnaf_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fiyat = db.Column(db.Float, nullable=False)
    aciklama = db.Column(db.Text, nullable=False)
    fotograf_url = db.Column(db.String(255), nullable=True)
    durum = db.Column(db.String(20), default='Beklemede')

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "Parca ve Esya Ilan Platformu API Motoru Aktif!"
    })

@app.route('/api/kayit', methods=['POST'])
def kayit():
    data = request.get_json()
    if not data or 'telefon' not in data or 'sifre' not in data:
        return jsonify({"error": "Eksik bilgi"}), 400
        
    if User.query.filter_by(telefon=data['telefon']).first():
        return jsonify({"error": "Bu numara kayitli"}), 400
        
    yeni_user = User(
        telefon=data['telefon'],
        ad_soyad=data.get('ad_soyad', ''),
        hesap_tipi=data.get('hesap_tipi', 'alici'),
        vergi_no=data.get('vergi_no', None),
        dukan_adresi=data.get('dukan_adresi', None)
    )
    yeni_user.set_sifre(data['sifre'])
    
    db.session.add(yeni_user)
    db.session.commit()
    return jsonify({"message": "Basarili"}), 201

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
