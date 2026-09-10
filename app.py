import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/ilan.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'gizli123'
db = SQLAlchemy(app)

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

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/kayit', methods=['POST'])
def kayit():
    data = request.get_json() or {}
    if 'telefon' not in data or 'sifre' not in data:
        return jsonify({"error": "eksik"}), 400
    if User.query.filter_by(telefon=data['telefon']).first():
        return jsonify({"error": "var"}), 400
    u = User(telefon=data['telefon'], ad_soyad=data.get('ad_soyad',''), hesap_tipi=data.get('hesap_tipi','alici'))
    u.sifre_hash = generate_password_hash(data['sifre'])
    db.session.add(u)
    db.session.commit()
    return jsonify({"status": "success"}), 201

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
