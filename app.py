import os
from flask import Flask, request, redirect, url_for, session, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Sunucunun kilitlenmesini önleyen en kritik ayar (Oturum şifreleme anahtarı)
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kalici_ve_kesin_gizli_anahtar_9988'

# Verileri geçici olarak RAM bellekte saklıyoruz
USERS_DB = {}
ILANLAR_DB = []

# Hazır Giriş Bilgileri
USERS_DB["05551234567"] = {
    "ad_soyad": "Ahmet Yilmaz",
    "sifre_hash": generate_password_hash("123456"),
    "hesap_tipi": "alici"
}
USERS_DB["05441234567"] = {
    "ad_soyad": "Oto Usta",
    "sifre_hash": generate_password_hash("123456"),
    "hesap_tipi": "esnaf"
}

# --- TEMEL ARAYÜZLER (Hatasız Yalın HTML) ---
LOGIN_HTML = """
<body style="background:#0b1329; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
    <h2>Ilan Uygulamasi - Giris Yap</h2>
    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
    <form method="POST" action="/login" style="display:inline-block; background:#1c2541; padding:30px; border-radius:10px;">
        <input type="tel" name="telefon" placeholder="Telefon (05551234567)" required style="padding:10px; margin:10px; width:250px;"><br>
        <input type="password" name="sifre" placeholder="Sifre" required style="padding:10px; margin:10px; width:250px;"><br>
        <button type="submit" style="padding:10px 20px; background:#4cc9f0; border:none; font-weight:bold; cursor:pointer;">Giris</button>
    </form>
    <p>Hesabiniz yok mu? <a href="/register" style="color:#4cc9f0;">Kayit Olun</a></p>
</body>
"""

REGISTER_HTML = """
<body style="background:#0b1329; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
    <h2>Ilan Uygulamasi - Kayit Ol</h2>
    {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
    <form method="POST" action="/register" style="display:inline-block; background:#1c2541; padding:30px; border-radius:10px;">
        <input type="tel" name="telefon" placeholder="Telefon Numarasi" required style="padding:10px; margin:10px; width:250px;"><br>
        <input type="text" name="ad_soyad" placeholder="Ad Soyad" required style="padding:10px; margin:10px; width:250px;"><br>
        <input type="password" name="sifre" placeholder="Sifre" required style="padding:10px; margin:10px; width:250px;"><br>
        <select name="hesap_turu" style="padding:10px; margin:10px; width:250px;">
            <option value="alici">Alici (Ilan Veren)</option>
            <option value="esnaf">Esnaf (Teklif Veren)</option>
        </select><br>
        <button type="submit" style="padding:10px 20px; background:#4cc9f0; border:none; font-weight:bold; cursor:pointer;">Kayit Ol</button>
    </form>
    <p>Zaten uye misiniz? <a href="/login" style="color:#4cc9f0;">Giris Yapin</a></p>
</body>
"""

ILANLAR_HTML = """
<body style="background:#0b1329; color:white; font-family:sans-serif; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:#1c2541; padding:20px; border-radius:10px;">
        <h3>Hos geldiniz, {{ session['ad_soyad'] }} ({{ session['hesap_tipi'].upper() }})</h3>
        <a href="/logout" style="color:red; float:right; font-weight:bold; text-decoration:none;">Cikis Yap</a><br><br>
        
        {% if session['hesap_tipi'] == 'alici' %}
            <form method="POST" action="/yeni-ilan" style="background:#3a506b; padding:15px; border-radius:8px; margin-bottom:20px;">
                <h4>Yeni Parca Talebi Olustur</h4>
                <input type="text" name="kategori" placeholder="Parca Adi / Kategori" required style="padding:8px; margin:5px; width:90%;"><br>
                <input type="text" name="detay" placeholder="Ilan Detayi" required style="padding:8px; margin:5px; width:90%;"><br>
                <input type="text" name="butce" placeholder="Butce (Orn: 3000 TL)" required style="padding:8px; margin:5px; width:90%;"><br>
                <button type="submit" style="padding:8px 15px; background:#4cc9f0; border:none; font-weight:bold; cursor:pointer;">Ilan Ver</button>
            </form>
        {% endif %}

        <h4>Mevcut Ilanlar</h4>
        {% if not ilanlar %}
            <p style="color:#abc4ff; font-size:14px; margin-top:10px;">Henuz hic ilan verilmemis.</p>
        {% endif %}
        {% for ilan in ilanlar %}
            <div style="background:#0b1329; padding:15px; border-radius:8px; margin-bottom:15px; border:1px solid #3a506b;">
                <p><b>Parca:</b> {{ ilan.kategori }} | <b>Butce:</b> {{ ilan.butce }}</p>
                <p><b>Detay:</b> {{ ilan.detay }}</p>
                <p style="font-size:12px; color:#abc4ff;">Ilan Sahibi: {{ ilan.ad_soyad }}</p>
            </div>
        {% endfor %}
    </div>
</body>
"""

# --- ROTALAR ---
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
            session['hesap_tipi'] = user["hesap_tipi"]
            return redirect(url_for('ilanlar_sayfasi'))
        return render_template_string(LOGIN_HTML, error="Hatali telefon veya sifre!")
    return render_template_string(LOGIN_HTML)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        telefon = request.form.get('telefon')
        ad_soyad = request.form.get('ad_soyad')
        sifre = request.form.get('sifre')
        hesap_turu = request.form.get('hesap_turu')

        if telefon in USERS_DB:
            return render_template_string(REGISTER_HTML, error="Bu telefon numarasi zaten kayitli!")

        USERS_DB[telefon] = {
            "ad_soyad": ad_soyad,
            "sifre_hash": generate_password_hash(sifre),
            "hesap_tipi": hesap_turu
        }
        return redirect(url_for('login'))
    return render_template_string(REGISTER_HTML)

@app.route('/ilanlar')
def ilanlar_sayfasi():
    if 'telefon' not in session:
        return redirect(url_for('login'))
    return render_template_string(ILANLAR_HTML, ilanlar=ILANLAR_DB)

@app.route('/yeni-ilan', methods=['POST'])
def yeni_ilan():
    if 'telefon' not in session or session.get('hesap_tipi') != 'alici':
        return redirect(url_for('ilanlar_sayfasi'))
    ILANLAR_DB.append({
        "ad_soyad": session['ad_soyad'],
        "kategori": request.form.get('kategori'),
        "detay": request.form.get('detay'),
        "butce": request.form.get('butce')
    })
    return redirect(url_for('ilanlar_sayfasi'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
