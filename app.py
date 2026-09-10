# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "pazaryeri_gizli_anahtar_2026"

# --- SIMULATED DATABASE ---
USERS = {}
LISTINGS = [
    {
        "id": 1,
        "title": "Temiz Kullanılmış Köşe Koltuk Takımı",
        "category": "Eşya",
        "city": "İstanbul",
        "district": "Kadıköy",
        "price": "8500",
        "description": "Herhangi bir yırtığı veya lekesi yoktur. Taşınma nedeniyle satılık.",
        "contact": "0532 111 2233",
        "user": "ahmet1"
    },
    {
        "id": 2,
        "title": "VW Golf 7 Sağ Ön Çamurluk (Orijinal)",
        "category": "Araç Parçası",
        "city": "Ankara",
        "district": "Çankaya",
        "price": "4200",
        "description": "Boyasız, hatasız orijinal çıkma parça.",
        "contact": "0544 222 3344",
        "user": "mehmet2"
    }
]

# --- TURKEY CITY & DISTRICT DATA ---
TURKEY_DATA = {
    "İstanbul": ["Kadıköy", "Beşiktaş", "Üsküdar", "Fatih", "Esenyurt", "Pendik", "Şişli"],
    "Ankara": ["Çankaya", "Keçiören", "Yenimahalle", "Mamak", "Etimesgut", "Sincan"],
    "İzmir": ["Konak", "Karşıyaka", "Bornova", "Buca", "Çeşme", "Aliağa"],
    "Bursa": ["Osmangazi", "Nilüfer", "Yıldırım", "İnegöl", "Mudanya"],
    "Antalya": ["Muratpaşa", "Kepez", "Alanya", "Manavgat", "Konyaaltı"],
    "Adana": ["Seyhan", "Çukurova", "Yüreğir", "Sarıçam"],
    "Gaziantep": ["Şahinbey", "Şehitkamil", "Nizip"],
    "Konya": ["Selçuklu", "Meram", "Karatay"],
}

TÜM_ILLER = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir",
    "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli",
    "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari",
    "Hatay", "Isparta", "İçel (Mersin)", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir",
    "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
    "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman",
    "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
]

for il in TÜM_ILLER:
    if il not in TURKEY_DATA:
        TURKEY_DATA[il] = ["Merkez", "İlçe 1", "İlçe 2"]

# --- HTML TEMPLATES ---
LAYOUT = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>PazarYeri</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f6f9; }
        .navbar { background-color: #1e293b !important; }
        .btn-primary { background-color: #0f766e; border: none; }
        .btn-primary:hover { background-color: #0d9488; }
        .hero { background: linear-gradient(135deg, #1e293b, #0f766e); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark mb-4">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">🚗 📦 PazarYeri</a>
            <div class="ms-auto">
                {% if "username" in session %}
                    <span class="text-white me-3">Merhaba, {{ session["username"] }}</span>
                    <a href="/create" class="btn btn-sm btn-primary">+ İlan Ver</a>
                    <a href="/logout" class="btn btn-sm btn-outline-light ms-2">Çıkış</a>
                {% else %}
                    <a href="/login" class="btn btn-sm btn-outline-light me-2">Giriş Yap</a>
                    <a href="/register" class="btn btn-sm btn-light">Üye Ol</a>
                {% endif %}
            </div>
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for cat, msg in messages %}
                    <div class="alert alert-{{ cat }}">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>"""

@app.route("/")
def index():
    cat = request.args.get("category", "")
    city = request.args.get("city", "")
    search = request.args.get("search", "")
    
    filtered = LISTINGS
    if cat: filtered = [x for x in filtered if x["category"] == cat]
    if city: filtered = [x for x in filtered if x["city"] == city]
    if search: filtered = [x for x in filtered if search.lower() in x["title"].lower() or search.lower() in x["description"].lower()]
    
    content = """
    <div class="hero text-center">
        <h2>İkinci El Eşya ve Yedek Parça Alım Satım Platformu</h2>
        <p>Güvenli, sade ve tüm Türkiye il/ilçeleri aktif.</p>
    </div>
    <div class="card p-3 mb-4 shadow-sm">
        <form method="GET" class="row g-2">
            <div class="col-md-3">
                <select name="category" class="form-select">
                    <option value="">Kategori Seçin</option>
                    <option value="Eşya">İkinci El Eşya</option>
                    <option value="Araç Parçası">Araç Parçası</option>
                </select>
            </div>
            <div class="col-md-3">
                <select name="city" class="form-select">
                    <option value="">İl Seçin</option>
                    {% for c in cities %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
                </select>
            </div>
            <div class="col-md-4">
                <input type="text" name="search" class="form-control" placeholder="Kelime ile ara...">
            </div>
            <div class="col-md-2 d-grid">
                <button type="submit" class="btn btn-primary">Filtrele</button>
            </div>
        </form>
    </div>
    <div class="row g-3">
        {% for item in listings %}
        <div class="col-md-6">
            <div class="card p-3 h-100 shadow-sm">
                <div class="d-flex justify-content-between">
                    <span class="badge bg-secondary mb-2">{{ item.category }}</span>
                    <h5 class="text-success fw-bold">{{ item.price }} TL</h5>
                </div>
                <h4>{{ item.title }}</h4>
                <p class="text-muted small">{{ item.description }}</p>
                <div class="mt-auto pt-2 border-top d-flex justify-content-between text-secondary small">
                    <span>📍 {{ item.city }} / {{ item.district }}</span>
                    <span>📞 İletişim: {{ item.contact }}</span>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    """
    return render_template_string(LAYOUT.replace("{% block content %}{% endblock %}", content), listings=filtered, cities=sorted(TURKEY_DATA.keys()))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if username in USERS:
            flash("Bu kullanıcı adı zaten mevcut.", "danger")
        else:
            USERS[username] = generate_password_hash(password)
            flash("Kayıt başarılı! Giriş yapabilirsiniz.", "success")
            return redirect(url_for("login"))
    content = """
    <div class="row justify-content-center"><div class="col-md-4"><div class="card p-4 shadow-sm">
    <h3 class="mb-3">Güvenli Üye Ol</h3>
    <form method="POST">
        <div class="mb-3"><label>Kullanıcı Adı</label><input type="text" name="username" class="form-control" required></div>
        <div class="mb-3"><label>Şifre</label><input type="password" name="password" class="form-control" required></div>
        <button type="submit" class="btn btn-primary w-100">Kayıt Ol</button>
    </form>
    </div></div></div>
    """
    return render_template_string(LAYOUT.replace("{% block content %}{% endblock %}", content))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        h = USERS.get(username)
        if h and check_password_hash(h, password):
            session["username"] = username
            flash("Giriş yapıldı.", "success")
            return redirect(url_for("index"))
        flash("Hatalı kullanıcı adı veya şifre.", "danger")
    content = """
    <div class="row justify-content-center"><div class="col-md-4"><div class="card p-4 shadow-sm">
    <h3 class="mb-3">Giriş Yap</h3>
    <form method="POST">
        <div class="mb-3"><label>Kullanıcı Adı</label><input type="text" name="username" class="form-control" required></div>
        <div class="mb-3"><label>Şifre</label><input type="password" name="password" class="form-control" required></div>
        <button type="submit" class="btn btn-primary w-100">Giriş Yap</button>
    </form>
    </div></div></div>
    """
    return render_template_string(LAYOUT.replace("{% block content %}{% endblock %}", content))

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

@app.route("/create", methods=["GET", "POST"])
def create():
    if "username" not in session: return redirect(url_for("login"))
    if request.method == "POST":
        LISTINGS.insert(0, {
            "title": request.form["title"],
            "category": request.form["category"],
            "city": request.form["city"],
            "district": request.form["district"],
            "price": request.form["price"],
            "description": request.form["description"],
            "contact": request.form["contact"],
            "user": session["username"]
        })
        flash("İlan başarıyla yayınlandı!", "success")
        return redirect(url_for("index"))
    
    content = """
    <div class="row justify-content-center"><div class="col-md-6"><div class="card p-4 shadow-sm">
    <h3 class="mb-3">Yeni İlan Ver</h3>
    <form method="POST">
        <div class="mb-3"><label>Başlık</label><input type="text" name="title" class="form-control" required></div>
        <div class="mb-3"><label>Kategori</label><select name="category" class="form-select"><option value="Eşya">Eşya</option><option value="Araç Parçası">Araç Parçası</option></select></div>
        <div class="mb-3"><label>Fiyat (TL)</label><input type="number" name="price" class="form-control" required></div>
        <div class="mb-3"><label>İl</label><select name="city" id="c_sel" class="form-select">{% for c in cities %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select></div>
        <div class="mb-3"><label>İlçe</label><select name="district" id="d_sel" class="form-select"><option value="Merkez">Merkez</option></select></div>
        <div class="mb-3"><label>İletişim</label><input type="text" name="contact" class="form-control" required></div>
        <div class="mb-3"><label>Açıklama</label><textarea name="description" class="form-control" required></textarea></div>
        <button type="submit" class="btn btn-primary w-100">Yayınla</button>
    </form>
    </div></div></div>
    """
    return render_template_string(LAYOUT.replace("{% block content %}{% endblock %}", content), cities=sorted(TURKEY_DATA.keys()))

if __name__ == "__main__":
    app.run(debug=True)
