import os
from flask import Flask, request, redirect, url_for, session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kesin_anahtar_123'

# Verileri geçici olarak RAM bellekte saklıyoruz
USERS_DB = {}
ILANLAR_DB = []
TEKLIFLER_DB = []

# Hazır Giriş Bilgileri
USERS_DB["05551234567"] = {"ad_soyad": "Ahmet Yilmaz", "sifre": "123456", "hesap_tipi": "alici"}
USERS_DB["05441234567"] = {"ad_soyad": "Oto Usta Garaj", "sifre": "123456", "hesap_tipi": "esnaf"}

# Örnek Başlangıç İlanı
ILANLAR_DB.append({
    "id": 1,
    "ad_soyad": "Ahmet Yilmaz",
    "kategori": "Kaporta / Far",
    "detay": "2018 model Golf sol on LED far ariyorum.",
    "butce": "7500 TL"
})

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
        if user and user["sifre"] == sifre:
            session['telefon'] = telefon
            session['ad_soyad'] = user["ad_soyad"]
            session['hesap_tipi'] = user["hesap_tipi"]
            return redirect(url_for('ilanlar_sayfasi'))
        return "<h3>Hatali telefon veya sifre!</h3><br><a href='/login'>Geri Don</a>"

    return '''
    <body style="background:#0b1329; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
        <div style="background:#1c2541; display:inline-block; padding:30px; border-radius:12px;">
            <h2>Ilan Uygulamasi - Giris Yap</h2>
            <form method="POST" action="/login">
                <input type="tel" name="telefon" placeholder="Telefon (05551234567)" required style="padding:10px; margin:10px; width:220px;"><br>
                <input type="password" name="sifre" placeholder="Sifre" required style="padding:10px; margin:10px; width:220px;"><br>
                <button type="submit" style="padding:10px 20px; background:#4cc9f0; border:none; font-weight:bold;">Giris Yap</button>
            </form>
            <p>Hesabiniz yok mu? <a href="/register" style="color:#4cc9f0;">Kayit Olun</a></p>
        </div>
    </body>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        telefon = request.form.get('telefon')
        ad_soyad = request.form.get('ad_soyad')
        sifre = request.form.get('sifre')
        hesap_turu = request.form.get('hesap_turu')

        if telefon in USERS_DB:
            return "<h3>Bu telefon numarasi zaten kayitli!</h3><br><a href='/register'>Geri Don</a>"

        USERS_DB[telefon] = {"ad_soyad": ad_soyad, "sifre": sifre, "hesap_tipi": hesap_turu}
        return redirect(url_for('login'))

    return '''
    <body style="background:#0b1329; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
        <div style="background:#1c2541; display:inline-block; padding:30px; border-radius:12px;">
            <h2>Yeni Hesap Olustur</h2>
            <form method="POST" action="/register">
                <input type="tel" name="telefon" placeholder="Telefon Numarasi" required style="padding:10px; margin:10px; width:220px;"><br>
                <input type="text" name="ad_soyad" placeholder="Ad Soyad" required style="padding:10px; margin:10px; width:220px;"><br>
                <input type="password" name="sifre" placeholder="Sifre" required style="padding:10px; margin:10px; width:220px;"><br>
                <select name="hesap_turu" style="padding:10px; margin:10px; width:220px;">
                    <option value="alici">Alici (Ilan Veren)</option>
                    <option value="esnaf">Esnaf (Teklif Veren)</option>
                </select><br>
                <button type="submit" style="padding:10px 20px; background:#4cc9f0; border:none; font-weight:bold;">Kayit Ol</button>
            </form>
            <p>Zaten uye misiniz? <a href="/login" style="color:#4cc9f0;">Giris Yapin</a></p>
        </div>
    </body>
    '''

@app.route('/ilanlar')
def ilanlar_sayfasi():
    if 'telefon' not in session:
        return redirect(url_for('login'))
    
    html_kod = f'''
    <body style="background:#0b1329; color:white; font-family:sans-serif; padding:20px;">
        <div style="max-width:600px; margin:0 auto; background:#1c2541; padding:20px; border-radius:12px;">
            <h3 style="margin:0; color:#4cc9f0;">Islem Paneli</h3>
            <p style="font-size:14px; color:#abc4ff;">Hos geldiniz, {session['ad_soyad']} ({session['hesap_tipi'].upper()})</p>
            <a href="/logout" style="color:#ff4d4d; font-weight:bold; float:right; text-decoration:none;">Cikis Yap</a><br><br>
    '''

    if session['hesap_tipi'] == 'alici':
        html_kod += '''
        <form method="POST" action="/yeni-ilan" style="background:#2a3457; padding:15px; border-radius:8px; margin-bottom:20px;">
            <h4 style="margin:0 0 10px 0; color:#4cc9f0;">➕ Yeni Parca Talebi Olustur</h4>
            <input type="text" name="kategori" placeholder="Parca Adi / Kategori" required style="width:90%; padding:8px; margin:5px;"><br>
            <input type="text" name="butce" placeholder="Butce (Orn: 5000 TL)" required style="width:90%; padding:8px; margin:5px;"><br>
            <input type="text" name="detay" placeholder="Ilan Detayi" required style="width:90%; padding:8px; margin:5px;"><br>
            <button type="submit" style="padding:8px 15px; background:#4cc9f0; border:none; font-weight:bold; cursor:pointer; margin:5px;">Ilan Yayinla</button>
        </form>
        '''

    html_kod += "<h4>Aktif Parca Talepleri</h4>"
    
    if not ILANLAR_DB:
        html_kod += "<p style='color:#abc4ff;'>Henüz ilan bulunmuyor.</p>"

    for ilan in ILANLAR_DB:
        html_kod += f'''
        <div style="background:#0b1329; padding:15px; border-radius:8px; margin-bottom:15px; border:1px solid #2a3457;">
            <p style="color:#4cc9f0; font-weight:bold;">🔧 {ilan['kategori']} | <span style="color:#52b788;">💰 {ilan['butce']}</span></p>
            <p style="background:#1c2541; padding:8px; border-radius:6px; font-size:14px;">{ilan['detay']}</p>
            <p style="font-size:11px; color:#abc4ff; margin:0;">📣 Ilan Sahibi: {ilan['ad_soyad']}</p>
            <div style="margin-top:10px; border-top:1px dashed #2a3457; padding-top:8px;">
                <p style="font-size:12px; color:#abc4ff; font-weight:bold; margin:0 0 5px 0;">GELEN TEKLIFLER</p>
        '''
        
        teklif_var_mi = False
        for teklif in TEKLIFLER_DB:
            if teklif["ilan_id"] == ilan["id"]:
                teklif_var_mi = True
                html_kod += f'''
                <div style="background:#2a3457; padding:6px; border-radius:4px; margin-bottom:4px; font-size:13px; display:flex; justify-content:space-between;">
                    <span>🛠️ <b>{teklif['esnaf_adi']}</b>: {teklif['aciklama']}</span>
                    <span style="color:#52b788; font-weight:bold;">{teklif['fiyat']} TL</span>
                </div>
                '''
        if not teklif_var_mi:
            html_kod += "<p style='font-size:12px; color:#abc4ff; font-style:italic; margin:0;'>Henuz teklif verilmedi.</p>"
            
        html_kod += "</div>"

        if session['hesap_tipi'] == 'esnaf':
            html_kod += f'''
            <form method="POST" action="/teklif-ver/{ilan['id']}" style="display:flex; gap:5px; margin-top:10px;">
                <input type="number" name="fiyat" placeholder="Fiyat (TL)" required style="width:90px; padding:6px;">
                <input type="text" name="aciklama" placeholder="Aciklama" required style="flex:1; padding:6px;">
                <button type="submit" style="padding:6px 12px; background:#52b788; border:none; color:white; font-weight:bold; cursor:pointer;">Teklif Ver</button>
            </form>
            '''
            
        html_kod += "</div>"

    html_kod += "</div></body>"
    return html_kod

@app.route('/yeni-ilan', methods=['POST'])
def yeni_ilan():
    if 'telefon' not in session or session.get('hesap_tipi') != 'alici':
        return redirect(url_for('ilanlar_sayfasi'))
    
    yeni_id = len(ILANLAR_DB) + 1
    ILANLAR_DB.insert(0, {
        "id": yeni_id,
        "ad_soyad": session['ad_soyad'],
        "kategori": request.form.get('kategori'),
        "detay": request.form.get('detay'),
        "butce": request.form.get('butce')
    })
    return redirect(url_for('ilanlar_sayfasi'))

@app.route('/teklif-ver/<int:ilan_id>', methods=['POST'])
def teklif_ver(ilan_id):
    if 'telefon' not in session or session.get('hesap_tipi') != 'esnaf':
        return redirect(url_for('ilanlar_sayfasi'))
        
    TEKLIFLER_DB.append({
        "ilan_id": ilan_id,
        "esnaf_adi": session['ad_soyad'],
        "fiyat": request.form.get('fiyat'),
        "aciklama": request.form.get('aciklama')
    })
    return redirect(url_for('ilanlar_sayfasi'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
