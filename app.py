import os
import re
import json
import uuid
from datetime import datetime
from typing import Any
from urllib.request import urlopen, Request

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="ParçaTeklif Reverse Marketplace", version="1.0.0")

# Render için PORT dinamik olarak kullanılır: uvicorn main:app --host 0.0.0.0 --port $PORT

VEHICLES = {
    "Volkswagen": ["Golf", "Passat", "Polo", "Jetta", "Tiguan", "Caddy", "Transporter", "Amarok"],
    "Renault": ["Clio", "Megane", "Symbol", "Fluence", "Captur", "Kadjar", "Austral", "Kangoo", "Master"],
    "Fiat": ["Egea", "Linea", "Doblo", "Fiorino", "Punto", "500", "Tipo", "Ducato"],
    "Ford": ["Focus", "Fiesta", "Mondeo", "Kuga", "Courier", "Transit", "Ranger", "Tourneo"],
    "Toyota": ["Corolla", "Yaris", "C-HR", "Auris", "RAV4", "Hilux", "Proace"],
    "Opel": ["Astra", "Corsa", "Insignia", "Mokka", "Crossland", "Grandland", "Combo", "Vivaro"],
    "BMW": ["1 Serisi", "2 Serisi", "3 Serisi", "4 Serisi", "5 Serisi", "X1", "X3", "X5"],
    "Mercedes-Benz": ["A Serisi", "B Serisi", "C Serisi", "E Serisi", "CLA", "GLA", "GLC", "Sprinter", "Vito"],
    "Audi": ["A1", "A3", "A4", "A5", "A6", "Q2", "Q3", "Q5"],
    "Hyundai": ["i10", "i20", "i30", "Accent", "Elantra", "Tucson", "Kona", "Bayon", "Staria"],
    "Kia": ["Picanto", "Rio", "Ceed", "Cerato", "Sportage", "Stonic", "Sorento"],
    "Honda": ["Civic", "Jazz", "CR-V", "HR-V", "City"],
    "Peugeot": ["208", "301", "308", "508", "2008", "3008", "5008", "Partner", "Expert"],
    "Citroën": ["C3", "C4", "C5 Aircross", "Berlingo", "Jumpy", "Nemo"],
    "Dacia": ["Sandero", "Logan", "Duster", "Lodgy", "Dokker", "Jogger"],
    "Nissan": ["Micra", "Qashqai", "Juke", "X-Trail", "Navara", "Primastar"],
    "Skoda": ["Fabia", "Scala", "Octavia", "Superb", "Kamiq", "Karoq", "Kodiaq"],
    "Seat": ["Ibiza", "Leon", "Arona", "Ateca", "Tarraco"],
    "Volvo": ["S60", "S90", "V40", "V60", "XC40", "XC60", "XC90"],
    "Tesla": ["Model 3", "Model Y", "Model S", "Model X"],
}
COLORS = ["Beyaz", "Siyah", "Gri", "Gümüş", "Kırmızı", "Mavi", "Lacivert", "Yeşil", "Sarı", "Turuncu", "Kahverengi", "Bej", "Bordo", "Mor", "Altın"]
CATEGORIES = ["Far", "Tampon", "Kaporta", "Motor", "Şanzıman", "Süspansiyon", "Elektrik / Elektronik", "İç Trim", "Jant & Lastik", "Diğer"]

# MVP veri deposu: uygulama yeniden başlatıldığında sıfırlanır; üretimde PostgreSQL'e taşınabilir.
LISTINGS: list[dict[str, Any]] = [
    {"id": "demo-1", "brand": "Volkswagen", "model": "Golf", "year": "2018", "trim": "1.6 TDI Comfortline", "color": "Beyaz", "category": "Far", "province": "İstanbul", "district": "Kadıköy", "description": "Sağ ön far arıyorum, temiz çıkma veya orijinal olabilir.", "phone": "0532 000 00 00", "created_at": "Bugün", "offers": 2},
    {"id": "demo-2", "brand": "Renault", "model": "Clio", "year": "2020", "trim": "1.0 TCe Joy", "color": "Kırmızı", "category": "Tampon", "province": "Ankara", "district": "İvedik OSB", "description": "Ön tampon ve ızgara seti, kırmızı renk tercih.", "phone": "0544 000 00 00", "created_at": "Bugün", "offers": 1},
]
OFFERS: list[dict[str, Any]] = []
LOCATION_CACHE: dict[str, Any] = {"data": None, "loaded_at": None}

class ListingPayload(BaseModel):
    brand: str = Field(min_length=1)
    model: str = Field(min_length=1)
    year: str = Field(min_length=4)
    trim: str = Field(min_length=1)
    color: str = Field(min_length=1)
    category: str = Field(min_length=1)
    province: str = Field(min_length=1)
    district: str = Field(min_length=1)
    description: str = Field(min_length=5)
    phone: str = Field(min_length=10)

class OfferPayload(BaseModel):
    listing_id: str
    seller_name: str = Field(min_length=2)
    amount: str = Field(min_length=1)
    note: str = Field(min_length=2)
    premium: bool = False

@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(INDEX_HTML)

@app.get("/api/config")
def config():
    return {"vehicles": VEHICLES, "colors": COLORS, "categories": CATEGORIES}

@app.get("/api/listings")
def get_listings():
    return {"listings": LISTINGS, "count": len(LISTINGS)}

@app.post("/api/listings")
def create_listing(payload: ListingPayload):
    if payload.brand not in VEHICLES or payload.model not in VEHICLES[payload.brand]:
        return JSONResponse({"ok": False, "message": "Geçersiz araç seçimi."}, status_code=400)
    if not re.fullmatch(r"(?:\+90|0)?5\d{9}", re.sub(r"[\s()-]", "", payload.phone)):
        return JSONResponse({"ok": False, "message": "Geçerli bir cep telefonu girin."}, status_code=400)
    listing = {"id": str(uuid.uuid4()), **payload.model_dump(), "created_at": "Az önce", "offers": 0}
    LISTINGS.insert(0, listing)
    return {"ok": True, "listing": listing}

@app.post("/api/verify-phone")
def verify_phone(phone: str = Form(...)):
    normalized = re.sub(r"[\s()-]", "", phone)
    valid = bool(re.fullmatch(r"(?:\+90|0)?5\d{9}", normalized))
    return {"ok": valid, "message": "Simülasyon kodu gönderildi: 1234" if valid else "Geçerli bir cep telefonu girin."}

@app.post("/api/ai-vision")
async def ai_vision(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    await file.read()
    if "far" in filename:
        result = {"brand": "Volkswagen", "model": "Golf", "color": "Beyaz", "category": "Far", "description": "Görsel analizine göre araç farında hasar / kırık tespit edildi. Uyumlu çıkma veya orijinal parça aranıyor."}
    elif "tampon" in filename:
        result = {"brand": "Renault", "model": "Clio", "color": "Kırmızı", "category": "Tampon", "description": "Görsel analizine göre ön tamponda deformasyon ve çizik tespit edildi. Kırmızı renk tampon aranıyor."}
    else:
        result = {"brand": "Fiat", "model": "Egea", "color": "Gri", "category": "Kaporta", "description": "Görsel analizine göre kaporta parçasında hasar tespit edildi. Uyumlu çıkma parça aranıyor."}
    return {"ok": True, "confidence": 0.94, "result": result}

@app.post("/api/offers")
def create_offer(payload: OfferPayload):
    listing = next((x for x in LISTINGS if x["id"] == payload.listing_id), None)
    if not listing:
        return JSONResponse({"ok": False, "message": "İlan bulunamadı."}, status_code=404)
    offer = {"id": str(uuid.uuid4()), "created_at": "Az önce", **payload.model_dump()}
    OFFERS.append(offer)
    listing["offers"] += 1
    return {"ok": True, "offer": offer}

@app.get("/api/locations")
def locations():
    # TürkiyeAPI canlı kaynağı: ilçeler dahil 81 il. CDN/API erişilemezse frontend kendi fallback mesajını gösterir.
    if LOCATION_CACHE["data"] is None:
        try:
            req = Request("https://turkiyeapi.dev/api/v1/provinces", headers={"User-Agent": "ParcaTeklif-MVP/1.0"})
            with urlopen(req, timeout=4) as response:
                raw = json.loads(response.read().decode("utf-8"))
                rows = raw.get("data", raw)
                normalized = []
                for row in rows:
                    name = row.get("name")
                    districts = [d.get("name") if isinstance(d, dict) else str(d) for d in row.get("districts", [])]
                    if name: normalized.append({"name": name, "districts": districts})
                if normalized:
                    LOCATION_CACHE["data"] = normalized
        except Exception:
            LOCATION_CACHE["data"] = []
    return {"provinces": LOCATION_CACHE["data"] or [], "source": "turkiyeapi.dev"}

INDEX_HTML = r'''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ParçaTeklif — Aradığın Parça, En İyi Teklif</title>
<script src="https://cdn.tailwindcss.com"></script>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
<script>tailwind.config={theme:{extend:{fontFamily:{sans:['DM Sans','sans-serif'],display:['Space Grotesk','sans-serif']},colors:{ink:'#152235',brand:'#ef6c3c',cream:'#fffaf5',mint:'#dff5e9'}}}};</script>
<style>body{background:#fffaf5;color:#152235}.glass{background:rgba(255,255,255,.78);backdrop-filter:blur(14px)}.grid-bg{background-image:linear-gradient(#f3e9df 1px,transparent 1px),linear-gradient(90deg,#f3e9df 1px,transparent 1px);background-size:32px 32px}.field{width:100%;border:1px solid #eadfd5;border-radius:12px;padding:.72rem .85rem;background:#fff;outline:none;transition:.2s}.field:focus{border-color:#ef6c3c;box-shadow:0 0 0 3px #ef6c3c22}.chip{border:1px solid #eadfd5;border-radius:999px;padding:.38rem .7rem;font-size:.8rem;background:#fff}.locked{filter:blur(4px);user-select:none}.toast{animation:toast 3.5s forwards}@keyframes toast{0%,100%{opacity:0;transform:translateY(12px)}10%,85%{opacity:1;transform:translateY(0)}} </style>
</head>
<body class="font-sans">
<header class="sticky top-0 z-20 border-b border-orange-100/80 glass"><div class="max-w-6xl mx-auto px-4 py-3 flex justify-between items-center"><a href="#top" class="flex items-center gap-2"><span class="w-9 h-9 rounded-xl bg-brand text-white grid place-items-center"><i class="fa-solid fa-wrench"></i></span><span class="font-display font-bold text-xl">Parça<span class="text-brand">Teklif</span></span></a><nav class="hidden md:flex gap-6 text-sm font-semibold"><a href="#create" class="hover:text-brand">İlan Ver</a><a href="#pool" class="hover:text-brand">İlan Havuzu</a><a href="#how" class="hover:text-brand">Nasıl Çalışır?</a></nav><button onclick="scrollToId('create')" class="bg-ink text-white px-4 py-2 rounded-xl text-sm font-semibold">Ücretsiz Başla <i class="fa-solid fa-arrow-right ml-1"></i></button></div></header>
<main id="top"><section class="grid-bg"><div class="max-w-6xl mx-auto px-4 py-16 md:py-24 grid md:grid-cols-[1.1fr_.9fr] gap-12 items-center"><div><div class="inline-flex items-center gap-2 bg-mint text-emerald-800 px-3 py-1.5 rounded-full text-xs font-bold mb-5"><span class="w-2 h-2 rounded-full bg-emerald-500"></span> Türkiye'nin parça teklif ağı</div><h1 class="font-display text-5xl md:text-7xl font-bold leading-[.98] tracking-tight">Parçanı ara.<br><span class="text-brand">Teklifleri topla.</span></h1><p class="mt-6 text-lg text-slate-600 max-w-lg">İhtiyacın olan yedek parçayı tarif et, Türkiye'nin dört bir yanındaki çıkmacı ve sanayi esnafından teklifleri tek yerde karşılaştır.</p><div class="mt-8 flex flex-wrap gap-3"><button onclick="scrollToId('create')" class="bg-brand text-white px-5 py-3 rounded-xl font-bold shadow-lg shadow-orange-200">İlanını Oluştur <i class="fa-solid fa-plus ml-1"></i></button><button onclick="scrollToId('pool')" class="bg-white border border-orange-100 px-5 py-3 rounded-xl font-bold">İlanları Keşfet</button></div><div class="mt-8 flex gap-6 text-sm text-slate-500"><span><b class="text-ink text-lg">81</b> ilde</span><span><b class="text-ink text-lg">10 dk</b> içinde teklifler</span><span><b class="text-ink text-lg">%100</b> ücretsiz</span></div></div><div class="relative"><div class="absolute -inset-4 bg-orange-200/40 rounded-[2rem] rotate-3"></div><div class="relative bg-ink rounded-[2rem] p-6 md:p-8 text-white shadow-2xl"><div class="flex justify-between items-center mb-8"><span class="text-sm text-slate-300">Canlı teklif akışı</span><span class="text-xs bg-emerald-400/20 text-emerald-300 px-2 py-1 rounded-full">● Aktif</span></div><div class="bg-white/10 rounded-2xl p-4 mb-3"><div class="flex justify-between text-xs text-slate-300"><span>Volkswagen Golf · 2018</span><span>İstanbul</span></div><div class="font-bold mt-2">Sağ ön far aranıyor</div><div class="flex gap-2 mt-3"><span class="chip bg-white/10 border-white/10 text-slate-200">Far</span><span class="chip bg-white/10 border-white/10 text-slate-200">Beyaz</span></div></div><div class="bg-brand rounded-2xl p-4 ml-8 shadow-lg"><div class="flex justify-between text-xs text-orange-100"><span>Yeni teklif</span><span>Az önce</span></div><div class="font-bold mt-2">Mehmet Usta · İvedik</div><div class="text-2xl font-display font-bold mt-1">₺4.250 <span class="text-xs font-normal text-orange-100">gizli teklif</span></div></div><div class="mt-7 flex items-center gap-3 text-sm text-slate-300"><i class="fa-solid fa-shield-halved text-emerald-300"></i> Telefon doğrulamalı güvenli ilanlar</div></div></div></div></section>
<section id="create" class="max-w-6xl mx-auto px-4 py-16"><div class="flex justify-between items-end mb-6"><div><p class="text-brand font-bold text-sm uppercase tracking-widest">01 / Alıcı</p><h2 class="font-display text-3xl md:text-4xl font-bold mt-1">İhtiyacını anlat</h2><p class="text-slate-500 mt-2">İlanın esnaf ağına anında ulaşsın.</p></div><span class="hidden sm:block text-sm text-slate-400"><i class="fa-solid fa-lock mr-1"></i> Ücretsiz ve güvenli</span></div><div class="grid lg:grid-cols-[1.4fr_.6fr] gap-6"><form id="listingForm" class="bg-white border border-orange-100 rounded-3xl p-5 md:p-8 shadow-sm"><div class="flex items-center gap-2 mb-6"><span class="bg-brand text-white w-7 h-7 rounded-full grid place-items-center text-sm font-bold">1</span><h3 class="font-bold">Araç bilgileri</h3></div><div class="grid sm:grid-cols-2 gap-4"><label class="text-sm font-semibold">Marka<select id="brand" class="field mt-1" required><option value="">Marka seçin</option></select></label><label class="text-sm font-semibold">Model<select id="model" class="field mt-1" required disabled><option value="">Önce marka seçin</option></select></label><label class="text-sm font-semibold">Model yılı<select id="year" class="field mt-1" required><option value="">Yıl seçin</option></select></label><label class="text-sm font-semibold">Motor / paket<input id="trim" class="field mt-1" placeholder="Örn. 1.6 TDI Comfortline" required></label><label class="text-sm font-semibold sm:col-span-2">Araç rengi<select id="color" class="field mt-1" required><option value="">Renk seçin</option></select></label></div><div class="border-t border-orange-100 my-7"></div><div class="flex items-center gap-2 mb-6"><span class="bg-brand text-white w-7 h-7 rounded-full grid place-items-center text-sm font-bold">2</span><h3 class="font-bold">Parça ve konum</h3></div><div class="grid sm:grid-cols-2 gap-4"><label class="text-sm font-semibold">Parça kategorisi<select id="category" class="field mt-1" required><option value="">Kategori seçin</option></select></label><label class="text-sm font-semibold">İl<select id="province" class="field mt-1" required><option value="">İl seçin</option></select></label><label class="text-sm font-semibold">İlçe<select id="district" class="field mt-1" required disabled><option value="">Önce il seçin</option></select></label><label class="text-sm font-semibold sm:col-span-2">Açıklama<textarea id="description" class="field mt-1 min-h-24" placeholder="Aradığınız parçanın durumu, OEM kodu veya notlarınız..." required></textarea></label></div><div class="border-t border-orange-100 my-7"></div><div class="flex items-center gap-2 mb-6"><span class="bg-brand text-white w-7 h-7 rounded-full grid place-items-center text-sm font-bold">3</span><h3 class="font-bold">Görsel ve doğrulama</h3></div><div class="grid sm:grid-cols-2 gap-4"><div><label class="text-sm font-semibold">Görsel yükle <span class="text-brand">AI ile doldur</span><input id="image" type="file" accept="image/*" class="field mt-1" /></label><div id="aiStatus" class="text-xs text-slate-500 mt-2"><i class="fa-solid fa-wand-magic-sparkles mr-1"></i> Dosya adındaki ipuçlarından demo analiz yapılır.</div></div><div><label class="text-sm font-semibold">Cep telefonu<input id="phone" class="field mt-1" placeholder="05__ ___ __ __" required></label><button type="button" onclick="verifyPhone()" class="text-xs text-brand font-bold mt-2">SMS doğrulama kodu gönder</button><div id="phoneStatus" class="text-xs mt-1"></div></div></div><button class="w-full bg-ink hover:bg-slate-800 text-white rounded-xl py-3.5 mt-7 font-bold" type="submit">İlanı Yayınla <i class="fa-solid fa-paper-plane ml-2"></i></button></form><aside class="space-y-4"><div class="bg-mint rounded-3xl p-6"><i class="fa-solid fa-wand-magic-sparkles text-2xl text-emerald-700"></i><h3 class="font-display text-xl font-bold mt-4">AI ile daha hızlı</h3><p class="text-sm text-emerald-900/70 mt-2">Parçanın fotoğrafını yükle. Demo AI; araç, renk ve parça kategorisini otomatik doldursun.</p></div><div class="bg-white border border-orange-100 rounded-3xl p-6"><h3 class="font-bold">Neden telefon doğrulama?</h3><p class="text-sm text-slate-500 mt-2">Esnafların doğru alıcıya ulaşmasını ve ilanların güvenilir kalmasını sağlıyoruz.</p><div class="mt-4 flex gap-2 text-xs"><span class="chip"><i class="fa-solid fa-check text-emerald-500 mr-1"></i> Spam yok</span><span class="chip"><i class="fa-solid fa-check text-emerald-500 mr-1"></i> Ücretsiz</span></div></div></aside></div></section>
<section id="pool" class="bg-[#f5eee7] py-16"><div class="max-w-6xl mx-auto px-4"><div class="flex flex-col md:flex-row justify-between md:items-end gap-5 mb-7"><div><p class="text-brand font-bold text-sm uppercase tracking-widest">02 / Satıcı</p><h2 class="font-display text-3xl md:text-4xl font-bold mt-1">İlan havuzu</h2><p class="text-slate-500 mt-2">İhtiyaca uygun parçayı bul, teklifini bırak.</p></div><label class="flex items-center gap-3 bg-white rounded-2xl p-3 border border-orange-100 cursor-pointer"><span class="text-sm font-bold"><i class="fa-solid fa-store mr-2 text-brand"></i>Esnaf Modu</span><span class="relative"><input id="premiumToggle" type="checkbox" class="sr-only" onchange="togglePremium()"><span class="block w-12 h-7 bg-slate-300 rounded-full"></span><span id="toggleDot" class="absolute top-1 left-1 w-5 h-5 bg-white rounded-full transition"></span></span><span id="premiumLabel" class="text-xs text-slate-500">Ücretsiz</span></label></div><div id="premiumBanner" class="hidden bg-ink text-white rounded-2xl px-5 py-4 mb-5 text-sm"><i class="fa-solid fa-crown text-yellow-300 mr-2"></i><b>Premium mod aktif.</b> Telefon ve doğrudan iletişim butonları açıldı.</div><div id="listingGrid" class="grid lg:grid-cols-2 gap-4"></div></div></section>
<section id="how" class="max-w-6xl mx-auto px-4 py-16"><div class="text-center max-w-xl mx-auto"><p class="text-brand font-bold text-sm uppercase tracking-widest">03 / Nasıl çalışır?</p><h2 class="font-display text-3xl md:text-4xl font-bold mt-2">Aradığın parça, üç adım uzakta.</h2></div><div class="grid md:grid-cols-3 gap-5 mt-10"><div class="p-6 border border-orange-100 rounded-3xl bg-white"><span class="text-3xl font-display font-bold text-brand">01</span><h3 class="font-bold mt-5">İlanını bırak</h3><p class="text-sm text-slate-500 mt-2">Aracını ve aradığın parçayı seç, konumunu ekle.</p></div><div class="p-6 border border-orange-100 rounded-3xl bg-white"><span class="text-3xl font-display font-bold text-brand">02</span><h3 class="font-bold mt-5">Teklifleri topla</h3><p class="text-sm text-slate-500 mt-2">Çıkmacılar ve esnaf sana gizli fiyat tekliflerini iletsin.</p></div><div class="p-6 border border-orange-100 rounded-3xl bg-white"><span class="text-3xl font-display font-bold text-brand">03</span><h3 class="font-bold mt-5">En iyisini seç</h3><p class="text-sm text-slate-500 mt-2">Premium esnaflarla doğrudan iletişime geç, parçanı al.</p></div></div></section></main><footer class="bg-ink text-slate-300 py-8"><div class="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row justify-between gap-3 text-sm"><span>© 2026 ParçaTeklif MVP</span><span>Alıcılar için ücretsiz · Esnaflar için daha çok erişim</span></div></footer><div id="toast" class="fixed bottom-5 left-1/2 -translate-x-1/2 hidden z-50 bg-ink text-white px-5 py-3 rounded-xl shadow-xl text-sm"></div>
<script>
let config={}, locations=[], premium=false;
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
function scrollToId(id){$(id).scrollIntoView({behavior:'smooth'})} function toast(msg){const t=$('toast');t.textContent=msg;t.classList.remove('hidden');setTimeout(()=>t.classList.add('hidden'),3200)}
async function init(){config=await (await fetch('/api/config')).json();Object.keys(config.vehicles).forEach(x=>$('brand').insertAdjacentHTML('beforeend',`<option>${esc(x)}</option>`));config.colors.forEach(x=>$('color').insertAdjacentHTML('beforeend',`<option>${esc(x)}</option>`));config.categories.forEach(x=>$('category').insertAdjacentHTML('beforeend',`<option>${esc(x)}</option>`));for(let y=new Date().getFullYear();y>=1990;y--)$('year').insertAdjacentHTML('beforeend',`<option>${y}</option>`);try{locations=(await (await fetch('/api/locations')).json()).provinces;locations.forEach(p=>$('province').insertAdjacentHTML('beforeend',`<option>${esc(p.name)}</option>`))}catch(e){};loadListings()}
$('brand').onchange=()=>{$('model').disabled=!$('brand').value;$('model').innerHTML='<option value="">Model seçin</option>';(config.vehicles[$('brand').value]||[]).forEach(x=>$('model').insertAdjacentHTML('beforeend',`<option>${esc(x)}</option>`))};$('province').onchange=()=>{const p=locations.find(x=>x.name===$('province').value);$('district').disabled=!p;$('district').innerHTML='<option value="">İlçe seçin</option>';(p?.districts||[]).forEach(x=>$('district').insertAdjacentHTML('beforeend',`<option>${esc(x)}</option>`))};
$('image').onchange=async e=>{if(!e.target.files[0])return;$('aiStatus').innerHTML='<i class="fa-solid fa-spinner fa-spin mr-1"></i> Görsel analiz ediliyor...';const f=new FormData();f.append('file',e.target.files[0]);const d=await (await fetch('/api/ai-vision',{method:'POST',body:f})).json();const r=d.result;$('brand').value=r.brand;$('brand').dispatchEvent(new Event('change'));setTimeout(()=>{$('model').value=r.model},0);$('color').value=r.color;$('category').value=r.category;$('description').value=r.description;$('aiStatus').innerHTML='<span class="text-emerald-600"><i class="fa-solid fa-circle-check mr-1"></i> AI analizi tamamlandı (%94 güven)</span>'};
async function verifyPhone(){const f=new FormData();f.append('phone',$('phone').value);const d=await (await fetch('/api/verify-phone',{method:'POST',body:f})).json();$('phoneStatus').className='text-xs mt-1 '+(d.ok?'text-emerald-600':'text-red-500');$('phoneStatus').textContent=d.message}
$('listingForm').onsubmit=async e=>{e.preventDefault();const payload={brand:$('brand').value,model:$('model').value,year:$('year').value,trim:$('trim').value,color:$('color').value,category:$('category').value,province:$('province').value,district:$('district').value,description:$('description').value,phone:$('phone').value};const d=await (await fetch('/api/listings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})).json();if(!d.ok)return toast(d.message);toast('İlanın yayınlandı! Esnaflar teklif vermeye başladı.');e.target.reset();$('model').disabled=true;$('district').disabled=true;loadListings();scrollToId('pool')};
function togglePremium(){premium=$('premiumToggle').checked;$('premiumLabel').textContent=premium?'Premium':'Ücretsiz';$('toggleDot').style.transform=premium?'translateX(20px)':'translateX(0)';$('toggleDot').previousElementSibling.style.background=premium?'#10b981':'';$('premiumBanner').classList.toggle('hidden',!premium);renderListings(window.listings||[])}
async function loadListings(){window.listings=(await (await fetch('/api/listings')).json()).listings;renderListings(window.listings)}
function renderListings(items){$('listingGrid').innerHTML=items.map(x=>`<article class="bg-white rounded-3xl border border-orange-100 p-5 shadow-sm"><div class="flex justify-between gap-3"><div><div class="flex gap-2 flex-wrap"><span class="chip text-brand font-bold">${esc(x.category)}</span><span class="chip"><i class="fa-solid fa-location-dot mr-1 text-slate-400"></i>${esc(x.province)} / ${esc(x.district)}</span></div><h3 class="font-display text-xl font-bold mt-4">${esc(x.brand)} ${esc(x.model)} <span class="text-slate-400 font-sans text-sm">· ${esc(x.year)}</span></h3><p class="text-sm text-slate-500 mt-1">${esc(x.trim)} · ${esc(x.color)}</p></div><span class="text-xs text-slate-400 whitespace-nowrap">${esc(x.created_at)}</span></div><p class="text-sm text-slate-600 mt-4 bg-[#fffaf5] p-3 rounded-xl">${esc(x.description)}</p><div class="border-t border-orange-100 mt-4 pt-4 flex justify-between items-center"><div class="text-sm"><i class="fa-solid fa-phone text-brand mr-2"></i><span class="${premium?'':'locked'}">${esc(x.phone)}</span></div><div class="flex gap-2"><button onclick="openOffer('${x.id}')" class="bg-brand text-white rounded-lg px-3 py-2 text-xs font-bold">Teklif Ver</button><button onclick="contact('${x.phone}')" class="${premium?'':'opacity-50'} border border-orange-100 rounded-lg px-3 py-2 text-xs font-bold" ${premium?'':'disabled'}><i class="fa-brands fa-whatsapp mr-1"></i> ${premium?'WhatsApp':'Kilitli'}</button></div></div><div class="mt-3 text-xs text-slate-400"><i class="fa-solid fa-comments mr-1"></i>${x.offers} teklif · ${premium?'Premium iletişim açık':'Sadece Premium aboneler doğrudan iletişim kurabilir'}</div></article>`).join('')}
function contact(phone){if(premium)window.location.href='tel:'+phone.replace(/\D/g,'')};function openOffer(id){const amount=prompt('Gizli teklif tutarı (TL):');if(!amount)return;const note=prompt('Kısa notunuz:','Parça temiz ve gönderime hazır.');if(!note)return;const name=prompt('Esnaf / işletme adınız:','Usta Parça');if(!name)return;fetch('/api/offers',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({listing_id:id,seller_name:name,amount,note,premium})}).then(r=>r.json()).then(d=>{toast(d.ok?'Teklifiniz gizli olarak iletildi.':'Teklif gönderilemedi.');loadListings()})}
init();
</script></body></html>'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
