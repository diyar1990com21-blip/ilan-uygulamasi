import os
from flask import Flask, request, render_template, redirect, url_for, session

base_dir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ilan_uygulamasi_kesin_gizli_anahtar_123'

# --- HAZIR TASARIM ŞABLONU ---
# Klasörde login.html bulunamadığında devreye girecek modern koyu tema tasarımı
LOGIN_HTML_TEMPLATE = """
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
    </style>
</head>
<body>
    <div class="card">
        <h2>İlan Uygulaması</h2>
        <form method="POST">
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
        <div class="footer-text">Hesabınız yok mu? <a href="#">Kayıt Olun</a></div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return "Giriş işlemi tetiklendi (Veritabanı bağlantısı kapalı)", 200
        
    # Önce klasördeki login.html'i dener, bulamazsa yukarıdaki hazır tasarımı açar (Hata vermez!)
    try:
        return render_template('login.html')
    except:
        return LOGIN_HTML_TEMPLATE

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
