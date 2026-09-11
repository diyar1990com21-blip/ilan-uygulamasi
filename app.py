# -*- coding: utf-8 -*-
"""
PARÇA İSTE — Tersine İlan / İstek Pazarı (MVP)
================================================
Tek dosyalık FastAPI backend + gömülü HTML/Tailwind CSS frontend.

Kapsam: Bu platform araç ALIM/SATIMI için değildir. İlanlar her zaman bir
aracın ÜZERİNE takılacak PARÇA / AKSESUAR / MODİFİYE (tuning) talebidir
(ör. jant, body kit, LED far seti, egzoz, ses sistemi, kaplama/folyo,
chip tuning vb.) — motor/şanzıman gibi genel tamir-bakım parçaları
kapsam dışıdır.

Mimarî özet
-----------
- ALICI (ücretsiz): Adım adım sihirbazla "bu aracım için şu aksesuar/
  modifiye parçasını arıyorum" ilanı açar.
- SATICI (aksesuarcı / modifiye ustası / sanayi esnafı): İlan havuzunu
  görür, gizli fiyat teklifi verir. Alıcının telefon numarası ve doğrudan
  iletişim butonları sadece "Premium Abone" modunda açılır (bu MVP'de
  gerçek ödeme YOKTUR, sadece bir "Esnaf Modu Simülatörü" anahtarı ile
  arka uçtan taklit edilir).
- Veri katmanı: Bu bir MVP olduğu için veriler process belleğinde (RAM)
  tutulur. Servis yeniden başlarsa ilanlar sıfırlanır. Gerçek bir ürüne
  taşınırken burası bir veritabanına (Postgres vb.) bağlanmalıdır.
- İl/İlçe verisi: Tarayıcıyı yormamak için sunucuya hiç gömülmez; frontend
  JavaScript'i açık kaynaklı TurkiyeAPI'den (https://turkiyeapi.dev)
  dinamik olarak çeker. Bu sayede 81 il + ~970 ilçe backend'i şişirmez.
- AI Vision: Gerçek bir görüntü işleme modeli YOKTUR. İstenen davranış
  gereği, yüklenen dosyanın adına bakan basit bir similasyon fonksiyonu
  vardır (bkz. simulate_ai_vision).

Render.com dağıtımı
-------------------
Start Command:  uvicorn main:app --host 0.0.0.0 --port $PORT
(Alternatif olarak "python main.py" ile de çalışır; $PORT ortam
değişkenini otomatik okur — bkz. dosya sonundaki __main__ bloğu.)
"""

import os
import re
import random
import string
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

# ==========================================================================
# 1) SABİT VERİLER — Marka / Model / Renk / Parça Kategorisi
# ==========================================================================
# Not: Türkiye'de en yaygın 20 marka ve her markanın en popüler modelleri
# sert kodludur (hardcoded). Bu liste, aksesuar/modifiye parçasının hangi
# araca uygun olduğunu belirlemek için kullanılır.

CAR_DATA: Dict[str, List[str]] = {
    "Renault": ["Clio", "Megane", "Symbol", "Fluence", "Talisman", "Captur",
                "Kadjar", "Kangoo", "Toros", "12", "9"],
    "Fiat": ["Egea", "Linea", "Albea", "Doblo", "Punto", "Fiorino", "Panda",
             "Tipo", "Palio", "Şahin"],
    "Volkswagen": ["Golf", "Passat", "Polo", "Jetta", "Bora", "Caddy",
                   "Tiguan", "Transporter", "Scirocco", "Vento"],
    "Ford": ["Focus", "Fiesta", "Mondeo", "Connect", "Courier", "Kuga",
             "Ranger", "Transit", "B-Max", "Puma"],
    "Opel": ["Astra", "Corsa", "Vectra", "Insignia", "Combo", "Mokka",
             "Meriva", "Zafira", "Grandland X"],
    "Toyota": ["Corolla", "Yaris", "Auris", "Hilux", "C-HR", "RAV4",
               "Avensis", "Camry"],
    "Hyundai": ["i20", "i10", "Accent Era", "Accent Blue", "Elantra",
                "Tucson", "Bayon", "Kona", "ix35"],
    "Peugeot": ["301", "308", "208", "3008", "2008", "508", "Partner", "407"],
    "Citroën": ["C-Elysée", "C3", "C4", "Berlingo", "C5", "C2", "C4 Cactus"],
    "Honda": ["Civic", "City", "CR-V", "Jazz", "Accord"],
    "Nissan": ["Micra", "Qashqai", "Juke", "Almera", "X-Trail"],
    "Chevrolet": ["Aveo", "Cruze", "Lacetti", "Captiva", "Spark"],
    "Škoda": ["Octavia", "Fabia", "Superb", "Rapid", "Yeti", "Karoq"],
    "Seat": ["Ibiza", "Leon", "Toledo", "Córdoba", "Altea"],
    "Mercedes-Benz": ["C-Serisi", "E-Serisi", "A-Serisi", "Vito",
                      "Sprinter", "CLA", "GLA"],
    "BMW": ["3 Serisi", "5 Serisi", "1 Serisi", "X1", "X3", "X5"],
    "Audi": ["A3", "A4", "A6", "Q3", "Q5", "A1"],
    "Dacia": ["Duster", "Sandero", "Logan", "Dokker", "Lodgy"],
    "Kia": ["Rio", "Ceed", "Sportage", "Picanto", "Cerato", "Sorento"],
    "Suzuki": ["Swift", "Vitara", "Baleno", "S-Cross", "Grand Vitara"],
}

COLORS: List[str] = [
    "Beyaz", "Siyah", "Gri", "Gümüş", "Kırmızı", "Mavi", "Lacivert",
    "Yeşil", "Kahverengi", "Bej", "Sarı", "Turuncu", "Mor", "Bordo", "Füme",
]

PART_CATEGORIES: List[str] = [
    "Jant / Lastik",
    "Egzoz Sistemi (Sport / Modifiye)",
    "Body Kit / Spoiler / Difüzör",
    "Ön - Arka Tampon Aksesuarı",
    "Far / Stop (LED - Xenon Aksesuar)",
    "Sis Farı / Ek Aydınlatma",
    "Ses Sistemi / Multimedya",
    "Araç Kaplama / Folyo",
    "İç Mekan Aksesuarı (Döşeme, Pedal, Direksiyon)",
    "Dış Mekan Aksesuarı (Ayna Kapağı, Rüzgarlık, Çıta)",
    "Performans / Chip Tuning",
    "Spor Süspansiyon (Yükseltme / Alçaltma)",
    "Karbon / Krom Detay",
    "Alarm / Güvenlik - Park Sensörü",
    "Diğer Aksesuar / Modifiye",
]

_THIS_YEAR = datetime.now().year
YEARS: List[int] = list(range(_THIS_YEAR + 1, 1989, -1))

# ==========================================================================
# 2) AI VISION SİMÜLASYONU
# ==========================================================================
# Gerçek görüntü tanıma yoktur. İstenen davranış gereği dosya adı üzerinden
# basit bir eşleştirme yapılır. Üretimde buraya gerçek bir görüntü tanıma
# modeli (ör. bir vision API çağrısı) entegre edilebilir.

AI_RULES = [
    {
        "match": "far",
        "brand": "Volkswagen", "model": "Golf", "year": 2016, "color": "Beyaz",
        "part_category": "Far / Stop (LED - Xenon Aksesuar)",
        "description": (
            "Yapay zekâ analizi: Görselde bir far / aydınlatma aksesuarı tespit "
            "edildi. LED veya Xenon dönüşüm kiti ya da komple aksesuar far seti "
            "talebi olarak sınıflandırıldı."
        ),
    },
    {
        "match": "tampon",
        "brand": "Renault", "model": "Clio", "year": 2019, "color": "Kırmızı",
        "part_category": "Ön - Arka Tampon Aksesuarı",
        "description": (
            "Yapay zekâ analizi: Görselde bir body kit / spor tampon aksesuarı "
            "tespit edildi. Boyalı, astarlı veya renkli versiyon tercihini "
            "açıklamaya ekleyebilirsin."
        ),
    },
]

AI_DEFAULT = {
    "brand": "Fiat", "model": "Egea", "year": 2020, "color": "Gri",
    "part_category": "Diğer Aksesuar / Modifiye",
    "description": (
        "Yapay zekâ analizi: Görselde net bir aksesuar/modifiye parçası ayırt "
        "edilemedi, talep genel bir aksesuar isteği olarak sınıflandırıldı. "
        "Aşağıdaki alanları ihtiyacına göre düzenleyebilirsin."
    ),
}


def simulate_ai_vision(filename: str) -> Dict[str, Any]:
    """Yüklenen görselin dosya adına göre sahte bir AI Vision tespiti üretir."""
    name = (filename or "").lower()
    for rule in AI_RULES:
        if rule["match"] in name:
            result = {k: v for k, v in rule.items() if k != "match"}
            return result
    return dict(AI_DEFAULT)


# ==========================================================================
# 3) YARDIMCI FONKSİYONLAR
# ==========================================================================

PHONE_RE = re.compile(r"^05\d{9}$")


def normalize_phone(raw: str) -> str:
    """Kullanıcının girdiği telefonu '05XXXXXXXXX' biçimine normalize eder.

    Kabul edilen girişler: '0532 111 22 33', '532 111 22 33',
    '+90 532 111 22 33', '905321112233' vb.
    Geçersizse ValueError fırlatır.
    """
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0090"):
        digits = digits[4:]
    if digits.startswith("90") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("5"):
        digits = "0" + digits
    if not PHONE_RE.match(digits):
        raise ValueError(
            "Geçersiz telefon numarası. Örnek biçim: 0532 111 22 33"
        )
    return digits


def format_phone(digits: str) -> str:
    """'05321112233' -> '0532 111 22 33'"""
    if len(digits) != 11:
        return digits
    return f"{digits[0:4]} {digits[4:7]} {digits[7:9]} {digits[9:11]}"


def mask_phone(digits: str) -> str:
    if len(digits) != 11:
        return "•••• ••• •• ••"
    return f"{digits[0:4]} ••• •• {digits[9:11]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def gen_otp_code() -> str:
    return "".join(random.choices(string.digits, k=4))


# ==========================================================================
# 4) BELLEK-İÇİ VERİ DEPOSU (In-memory "DB")
# ==========================================================================
# MVP kapsamında kalıcı bir veritabanı yerine process belleği kullanılır.

LISTINGS: Dict[str, Dict[str, Any]] = {}
OTP_STORE: Dict[str, str] = {}          # phone(digits) -> 4 haneli kod
VERIFIED_PHONES: set = set()            # dogrulanmis telefonlar (digits)


# ==========================================================================
# 5) PYDANTIC ŞEMALARI
# ==========================================================================

class OtpSendRequest(BaseModel):
    phone: str


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str = Field(min_length=4, max_length=4)


class ListingCreateRequest(BaseModel):
    phone: str
    brand: str
    model: str
    year: int = Field(ge=1990, le=_THIS_YEAR + 1)
    engine_package: Optional[str] = ""
    color: str
    part_category: str
    description: str = Field(min_length=10, max_length=800)
    province: str
    province_id: Optional[int] = None
    district: str
    ai_filled: bool = False
    image_filename: Optional[str] = None

    @field_validator("brand")
    @classmethod
    def _brand_must_exist(cls, v: str) -> str:
        if v not in CAR_DATA:
            raise ValueError("Geçersiz marka.")
        return v

    @field_validator("color")
    @classmethod
    def _color_must_exist(cls, v: str) -> str:
        if v not in COLORS:
            raise ValueError("Geçersiz renk.")
        return v

    @field_validator("part_category")
    @classmethod
    def _category_must_exist(cls, v: str) -> str:
        if v not in PART_CATEGORIES:
            raise ValueError("Geçersiz parça kategorisi.")
        return v


class OfferCreateRequest(BaseModel):
    seller_name: str = Field(min_length=2, max_length=80)
    seller_phone: str
    price: float = Field(gt=0, le=10_000_000)
    message: Optional[str] = Field(default="", max_length=500)


# ==========================================================================
# 6) FASTAPI UYGULAMASI
# ==========================================================================

app = FastAPI(title="Parça İste — Tersine İlan Pazarı", version="1.0.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta")
def get_meta() -> Dict[str, Any]:
    """Formu doldurmak için gereken tüm sabit veriler tek seferde döner."""
    return {
        "brands": CAR_DATA,
        "colors": COLORS,
        "categories": PART_CATEGORIES,
        "years": YEARS,
    }


@app.post("/api/ai-analyze")
async def ai_analyze(file: UploadFile = File(...)) -> Dict[str, Any]:
    """'AI ile Doldur' simülasyonu: dosya adına göre araç/parça tahmini üretir."""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Dosya bulunamadı.")
    # Gerçek bir görsel yükleme senaryosunu simüle etmek için içerik okunur
    # (ancak analiz SADECE dosya adına göre yapılır; bkz. modül üstü not).
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Dosya çok büyük (maks 15MB).")
    result = simulate_ai_vision(file.filename)
    result["source_filename"] = file.filename
    return result


@app.post("/api/otp/send")
def otp_send(payload: OtpSendRequest) -> Dict[str, Any]:
    try:
        phone = normalize_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    code = gen_otp_code()
    OTP_STORE[phone] = code
    # NOT: Gerçek bir SMS sağlayıcısı (Netgsm/Twilio vb.) entegre değildir.
    # Bu yüzden demo amaçlı kod, yanıt içinde döndürülür.
    return {
        "success": True,
        "phone_display": format_phone(phone),
        "message": f"{format_phone(phone)} numarasına doğrulama kodu gönderildi (simülasyon).",
        "demo_code": code,
    }


@app.post("/api/otp/verify")
def otp_verify(payload: OtpVerifyRequest) -> Dict[str, Any]:
    try:
        phone = normalize_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    expected = OTP_STORE.get(phone)
    if not expected or expected != payload.code:
        raise HTTPException(status_code=400, detail="Kod hatalı veya süresi dolmuş.")
    VERIFIED_PHONES.add(phone)
    return {"success": True, "phone_display": format_phone(phone)}


def _public_listing(listing: Dict[str, Any], is_premium: bool) -> Dict[str, Any]:
    """İlanı satıcı tarafına döndürmeden önce premium kilidine göre süzer."""
    out = dict(listing)
    out["offer_count"] = len(listing.get("offers", []))
    out.pop("offers", None)
    if is_premium:
        out["phone_display"] = format_phone(listing["phone"])
        out["locked"] = False
    else:
        out["phone_display"] = mask_phone(listing["phone"])
        out["locked"] = True
    out.pop("phone", None)
    return out


@app.get("/api/listings")
def list_listings(
    is_premium: bool = False,
    province: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    status: str = "active",
) -> List[Dict[str, Any]]:
    items = list(LISTINGS.values())
    if status:
        items = [x for x in items if x["status"] == status]
    if province:
        items = [x for x in items if x["province"] == province]
    if brand:
        items = [x for x in items if x["brand"] == brand]
    if category:
        items = [x for x in items if x["part_category"] == category]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return [_public_listing(x, is_premium) for x in items]


@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: str, is_premium: bool = False) -> Dict[str, Any]:
    listing = LISTINGS.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")
    out = _public_listing(listing, is_premium)
    offers = list(listing.get("offers", []))
    offers.sort(key=lambda o: o["price"])
    out["offers"] = offers if is_premium else [
        {**o, "seller_phone": mask_phone(o["seller_phone"])} for o in offers
    ]
    return out


@app.post("/api/listings", status_code=201)
def create_listing(payload: ListingCreateRequest) -> Dict[str, Any]:
    try:
        phone = normalize_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if phone not in VERIFIED_PHONES:
        raise HTTPException(
            status_code=403,
            detail="Telefon numarası doğrulanmamış. Önce SMS kodunu doğrulayın.",
        )
    if payload.model not in CAR_DATA.get(payload.brand, []):
        raise HTTPException(status_code=400, detail="Model, seçilen markaya ait değil.")

    listing_id = new_id()
    listing = {
        "id": listing_id,
        "brand": payload.brand,
        "model": payload.model,
        "year": payload.year,
        "engine_package": (payload.engine_package or "").strip(),
        "color": payload.color,
        "part_category": payload.part_category,
        "description": payload.description.strip(),
        "province": payload.province,
        "province_id": payload.province_id,
        "district": payload.district,
        "phone": phone,
        "ai_filled": payload.ai_filled,
        "image_filename": payload.image_filename,
        "status": "active",
        "created_at": now_iso(),
        "offers": [],
    }
    LISTINGS[listing_id] = listing
    return _public_listing(listing, is_premium=True) | {"phone_display": format_phone(phone)}


@app.post("/api/listings/{listing_id}/offers", status_code=201)
def create_offer(listing_id: str, payload: OfferCreateRequest) -> Dict[str, Any]:
    listing = LISTINGS.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")
    if listing["status"] != "active":
        raise HTTPException(status_code=400, detail="Bu ilan artık aktif değil.")
    try:
        seller_phone = normalize_phone(payload.seller_phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    offer = {
        "id": new_id(),
        "seller_name": payload.seller_name.strip(),
        "seller_phone": seller_phone,
        "seller_phone_display": format_phone(seller_phone),
        "price": round(payload.price, 2),
        "message": (payload.message or "").strip(),
        "created_at": now_iso(),
    }
    listing["offers"].append(offer)
    return offer


@app.patch("/api/listings/{listing_id}/close")
def close_listing(listing_id: str, payload: OtpSendRequest) -> Dict[str, Any]:
    """Alıcı kendi ilanını kapatır (payload.phone == ilan sahibinin telefonu)."""
    listing = LISTINGS.get(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="İlan bulunamadı.")
    try:
        phone = normalize_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if phone != listing["phone"]:
        raise HTTPException(status_code=403, detail="Bu ilanı kapatma yetkiniz yok.")
    listing["status"] = "closed"
    return {"success": True}


@app.get("/api/my-listings")
def my_listings(phone: str) -> List[Dict[str, Any]]:
    try:
        norm = normalize_phone(phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    items = [x for x in LISTINGS.values() if x["phone"] == norm]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    result = []
    for x in items:
        item = dict(x)
        item["phone_display"] = format_phone(x["phone"])
        offers = sorted(x["offers"], key=lambda o: o["price"])
        item["offers"] = offers
        item["offer_count"] = len(offers)
        result.append(item)
    return result


# ==========================================================================
# 7) FRONTEND — Tek parça HTML / Tailwind CSS / Vanilla JS
# ==========================================================================

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Parça İste — Araç Aksesuar ve Modifiye Parça Talep Pazarı</title>
<meta name="description" content="Tersine ilan pazarı: aracın için aradığın aksesuar veya modifiye parçasını ücretsiz ilan et, aksesuarcı ve modifiye ustaları sana teklif versin.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css">
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          ink: '#1B1D21',
          paper: '#EEF0F2',
          panel: '#FFFFFF',
          steel: '#5B6472',
          accent: '#F2A71B',
          accentdark: '#C97F0A',
          gold: '#B8862E',
          success: '#1F8A5F',
          danger: '#C43B3B',
        },
        fontFamily: {
          display: ['"Space Grotesk"', 'sans-serif'],
          body: ['"IBM Plex Sans"', 'sans-serif'],
        },
      }
    }
  }
</script>
<style>
  :root{
    --ink:#1B1D21; --paper:#EEF0F2; --steel:#5B6472; --accent:#F2A71B;
    --accentdark:#C97F0A; --gold:#B8862E; --success:#1F8A5F; --danger:#C43B3B;
  }
  html{ scroll-behavior:smooth; }
  body{ -webkit-font-smoothing:antialiased; }
  select, input, textarea, button { font-family:'IBM Plex Sans',sans-serif; }

  .nav-btn{ padding:0.5rem 0.9rem; border-radius:0.375rem; color:rgba(255,255,255,.78); font-weight:500; font-size:.9rem; transition:background .15s,color .15s; }
  .nav-btn:hover{ background:rgba(255,255,255,.08); color:#fff; }
  .nav-btn-active{ background:var(--accent); color:var(--ink); }

  .mode-btn{ background:#fff; color:var(--steel); }
  .mode-btn-active{ background:var(--ink) !important; color:#fff !important; }

  .step-dot{ width:2.1rem;height:2.1rem;border-radius:9999px;display:flex;align-items:center;justify-content:center;
    font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:.85rem;background:#fff;
    border:2px solid rgba(0,0,0,.12);color:var(--steel); transition:all .2s; flex-shrink:0; }
  .step-dot-active{ border-color:var(--accent); background:var(--accent); color:var(--ink); }
  .step-dot-done{ border-color:var(--success); background:var(--success); color:#fff; }
  .step-line{ flex:1; height:2px; background:rgba(0,0,0,.12); }

  .wizard-step{ animation: fadein .25s ease; }
  @keyframes fadein{ from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:translateY(0);} }
  @media (prefers-reduced-motion: reduce){ .wizard-step{ animation:none; } html{scroll-behavior:auto;} }

  .otp-input{ font-family:'Space Grotesk',monospace; letter-spacing:0.6em; text-align:center; font-size:1.4rem; }

  ::-webkit-scrollbar{ width:8px; height:8px; }
  ::-webkit-scrollbar-thumb{ background:rgba(0,0,0,.15); border-radius:4px; }

  button:focus-visible, a:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible{
    outline:2px solid var(--accent); outline-offset:2px;
  }

  .hero-fade{ animation: heroIn .6s ease both; }
  .hero-fade.d2{ animation-delay:.1s; }
  .hero-fade.d3{ animation-delay:.2s; }
  @keyframes heroIn{ from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:translateY(0);} }
  @media (prefers-reduced-motion: reduce){ .hero-fade{ animation:none; } }
</style>
</head>
<body class="font-body bg-paper text-ink">

<header class="sticky top-0 z-40 bg-ink text-white border-b-4 border-accent">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
    <button onclick="showView('home')" class="flex items-center gap-2 font-display font-bold text-lg">
      <span class="w-8 h-8 rounded-md bg-accent text-ink flex items-center justify-center">
        <i class="fa-solid fa-magnifying-glass-dollar text-sm"></i>
      </span>
      Parça İste
    </button>
    <nav class="hidden sm:flex items-center gap-1">
      <button onclick="showView('home')" data-nav="home" class="nav-btn">Ana Sayfa</button>
      <button onclick="showView('buyer')" data-nav="buyer" class="nav-btn">İlan Ver</button>
      <button onclick="showView('seller')" data-nav="seller" class="nav-btn">Satıcı Paneli</button>
      <button onclick="showView('mylistings')" data-nav="mylistings" class="nav-btn">İlanlarım</button>
    </nav>
    <button onclick="toggleMobileNav()" class="sm:hidden text-xl w-9 h-9 flex items-center justify-center" aria-label="Menü">
      <i class="fa-solid fa-bars"></i>
    </button>
  </div>
  <div id="mobile-nav" class="hidden sm:hidden flex flex-col gap-1 px-4 pb-3 border-t border-white/10 pt-2">
    <button onclick="showView('home')" data-nav="home" class="nav-btn text-left">Ana Sayfa</button>
    <button onclick="showView('buyer')" data-nav="buyer" class="nav-btn text-left">İlan Ver</button>
    <button onclick="showView('seller')" data-nav="seller" class="nav-btn text-left">Satıcı Paneli</button>
    <button onclick="showView('mylistings')" data-nav="mylistings" class="nav-btn text-left">İlanlarım</button>
  </div>
</header>

<main>
<!-- ============================= ANA SAYFA ============================= -->
<section id="view-home">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 pt-10 sm:pt-16 pb-12 grid md:grid-cols-2 gap-10 items-center">
    <div class="hero-fade">
      <p class="inline-flex items-center gap-2 text-xs font-medium text-accentdark bg-accent/15 px-3 py-1 rounded-full mb-4">
        <i class="fa-solid fa-arrows-rotate"></i> Tersine ilan pazarı
      </p>
      <h1 class="font-display font-bold text-3xl sm:text-4xl lg:text-5xl leading-tight mb-4">
        Aksesuar ve modifiye parçayı<br>sen iste, usta teklif versin.
      </h1>
      <p class="text-steel text-base sm:text-lg mb-6 max-w-md">
        Aracın için aradığın jant, body kit, LED far, ses sistemi veya herhangi bir
        aksesuar / modifiye parçasını ücretsiz ilan et. Çevrendeki aksesuarcı ve
        modifiye ustaları sana fiyat teklifi göndersin — arayan sen değil, teklif
        veren onlar olsun.
      </p>
      <div class="flex flex-col sm:flex-row gap-3">
        <button onclick="showView('buyer')" class="px-5 py-3 rounded-lg bg-accent text-ink font-semibold hover:bg-accentdark hover:text-white transition-colors">
          <i class="fa-solid fa-bullhorn mr-2"></i>Ücretsiz İlan Ver
        </button>
        <button onclick="showView('seller')" class="px-5 py-3 rounded-lg bg-ink text-white font-semibold hover:bg-ink/90 transition-colors">
          <i class="fa-solid fa-screwdriver-wrench mr-2"></i>Esnafım, Teklif Vermek İstiyorum
        </button>
      </div>
      <div class="flex gap-6 mt-8 text-sm text-steel">
        <div><span class="font-display font-bold text-ink text-lg">20</span> marka</div>
        <div><span class="font-display font-bold text-ink text-lg">81</span> il</div>
        <div><span class="font-display font-bold text-ink text-lg">0₺</span> ilan ücreti</div>
      </div>
    </div>

    <div class="hero-fade d2 bg-white border border-black/10 rounded-xl p-6">
      <p class="text-xs font-medium text-steel mb-5">Nasıl çalışır?</p>
      <div class="space-y-6">
        <div class="flex gap-4">
          <div class="w-8 h-8 rounded-full bg-ink text-white flex items-center justify-center font-display font-semibold text-sm shrink-0">1</div>
          <div>
            <p class="font-medium">Talebini ücretsiz paylaş</p>
            <p class="text-sm text-steel mt-0.5">Aracını seç, aradığın aksesuar veya modifiye parçasını anlat — istersen fotoğrafını yükle, yapay zekâ formu senin yerine doldursun.</p>
          </div>
        </div>
        <div class="flex gap-4">
          <div class="w-8 h-8 rounded-full bg-ink text-white flex items-center justify-center font-display font-semibold text-sm shrink-0">2</div>
          <div>
            <p class="font-medium">Esnaf sana teklif versin</p>
            <p class="text-sm text-steel mt-0.5">Bölgendeki aksesuarcı ve modifiye ustaları talebini görür, gizli fiyat teklifi gönderir.</p>
          </div>
        </div>
        <div class="flex gap-4">
          <div class="w-8 h-8 rounded-full bg-ink text-white flex items-center justify-center font-display font-semibold text-sm shrink-0">3</div>
          <div>
            <p class="font-medium">En iyi teklifi sen seç</p>
            <p class="text-sm text-steel mt-0.5">Gelen teklifleri "İlanlarım" sayfandan karşılaştır, uygun olanı arayıp anlaş.</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="bg-white border-y border-black/10">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 py-10 grid sm:grid-cols-2 gap-6">
      <div class="border border-black/10 rounded-lg p-5">
        <i class="fa-solid fa-bullhorn text-accentdark text-xl mb-3"></i>
        <h3 class="font-display font-semibold text-lg mb-1">Alıcılar için</h3>
        <p class="text-sm text-steel mb-4">İlan vermek tamamen ücretsizdir. Telefon doğrulaması sahte ilanları engeller, sadece gerçek talepler havuza girer.</p>
        <button onclick="showView('buyer')" class="text-sm font-medium text-ink hover:text-accentdark">İlan ver <i class="fa-solid fa-arrow-right-long ml-1"></i></button>
      </div>
      <div class="border border-black/10 rounded-lg p-5">
        <i class="fa-solid fa-screwdriver-wrench text-accentdark text-xl mb-3"></i>
        <h3 class="font-display font-semibold text-lg mb-1">Satıcılar / Esnaf için</h3>
        <p class="text-sm text-steel mb-4">Talep havuzunu ücretsiz gez, gizli teklif ver. Alıcıyla doğrudan görüşmek için Premium Abone ol.</p>
        <button onclick="showView('seller')" class="text-sm font-medium text-ink hover:text-accentdark">Talep havuzunu gör <i class="fa-solid fa-arrow-right-long ml-1"></i></button>
      </div>
    </div>
  </div>
</section>

<!-- ============================= ALICI: İLAN VER ============================= -->
<section id="view-buyer" class="hidden">
  <div class="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
    <h1 class="font-display font-bold text-2xl mb-1">Ücretsiz Aksesuar / Modifiye Talebi Oluştur</h1>
    <p class="text-steel text-sm mb-6">5 adımda ilanını yayınla, çevrendeki aksesuarcı ve modifiye ustaları sana teklif versin.</p>

    <div class="flex items-center mb-2">
      <div class="step-dot step-dot-active" data-step="1">1</div><div class="step-line"></div>
      <div class="step-dot" data-step="2">2</div><div class="step-line"></div>
      <div class="step-dot" data-step="3">3</div><div class="step-line"></div>
      <div class="step-dot" data-step="4">4</div><div class="step-line"></div>
      <div class="step-dot" data-step="5">5</div>
    </div>
    <div class="flex justify-between text-[11px] text-steel mb-6 px-1">
      <span>Görsel</span><span>Araç</span><span>Parça</span><span>Konum</span><span>Onay</span>
    </div>

    <div id="wizard-error" class="hidden bg-danger/10 text-danger text-sm rounded-lg px-4 py-3 mb-4">
      <i class="fa-solid fa-triangle-exclamation mr-1"></i><span id="wizard-error-text"></span>
    </div>

    <div id="wizard-form-wrap" class="bg-white border border-black/10 rounded-xl p-5 sm:p-6">

      <!-- STEP 1: AI GÖRSEL -->
      <div class="wizard-step" data-step="1">
        <h2 class="font-display font-semibold text-lg mb-1"><i class="fa-solid fa-camera-retro text-accentdark mr-1"></i> Görsel Yükle (AI ile Doldur)</h2>
        <p class="text-sm text-steel mb-4">Aradığın aksesuar veya modifiye parçasının bir görselini (örnek/referans fotoğraf) yükle, yapay zekâ araç ve parça bilgilerini tahmin edip formu otomatik doldursun. Bu adım isteğe bağlıdır.</p>

        <label for="ai-file-input" class="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-black/15 rounded-lg py-8 cursor-pointer hover:border-accent hover:bg-accent/5 transition-colors">
          <i class="fa-solid fa-cloud-arrow-up text-2xl text-steel"></i>
          <span class="text-sm font-medium">Görsel seç veya sürükleyip bırak</span>
          <span class="text-xs text-steel">JPG / PNG, maks 15MB</span>
        </label>
        <input type="file" id="ai-file-input" accept="image/*" class="hidden" onchange="onFileSelected(event)">
        <p id="file-chosen-name" class="hidden text-sm mt-2 text-steel"><i class="fa-solid fa-paperclip mr-1"></i></p>

        <button id="ai-analyze-btn" disabled onclick="runAiAnalyze()" class="mt-4 w-full py-3 rounded-lg bg-ink text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-ink/90 transition-colors">
          <i class="fa-solid fa-wand-magic-sparkles mr-1"></i> AI ile Doldur
        </button>

        <div id="ai-loading-box" class="hidden mt-4 flex items-center gap-2 text-sm text-steel">
          <i class="fa-solid fa-spinner fa-spin"></i> Yapay zekâ görseli inceliyor...
        </div>
        <div id="ai-result-box" class="hidden mt-4 bg-accent/10 border border-accent/30 rounded-lg p-4"></div>

        <button onclick="goToStep(2)" class="mt-4 text-sm text-steel hover:text-ink underline underline-offset-2">
          Bu adımı atla, bilgileri elle gireceğim
        </button>
      </div>

      <!-- STEP 2: ARAÇ BİLGİLERİ -->
      <div class="wizard-step hidden" data-step="2">
        <h2 class="font-display font-semibold text-lg mb-4"><i class="fa-solid fa-car text-accentdark mr-1"></i> Araç Bilgileri</h2>
        <div class="space-y-4">
          <div>
            <label class="text-sm font-medium block mb-1">Marka</label>
            <select id="brand-select" onchange="onBrandChange()" class="w-full border border-black/15 rounded-lg px-3 py-2.5 bg-white"></select>
          </div>
          <div>
            <label class="text-sm font-medium block mb-1">Model</label>
            <select id="model-select" disabled class="w-full border border-black/15 rounded-lg px-3 py-2.5 bg-white disabled:bg-black/5">
              <option value="">Önce marka seçin</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="text-sm font-medium block mb-1">Model Yılı</label>
              <select id="year-select" class="w-full border border-black/15 rounded-lg px-3 py-2.5 bg-white"></select>
            </div>
            <div>
              <label class="text-sm font-medium block mb-1">Renk</label>
              <select id="color-select" class="w-full border border-black/15 rounded-lg px-3 py-2.5 bg-white"></select>
            </div>
          </div>
          <div>
            <label class="text-sm font-medium block mb-1">Motor / Paket <span class="text-steel font-normal">(opsiyonel)</span></label>
            <input id="engine-input" type="text" placeholder="Örn: 1.6 16V Manuel / 1.4 TSI Comfortline"
              class="w-full border border-black/15 rounded-lg px-3 py-2.5">
          </div>
        </div>
        <div class="flex justify-between mt-6">
          <button onclick="prevStep()" class="px-4 py-2.5 rounded-lg text-steel font-medium hover:bg-black/5">Geri</button>
          <button onclick="nextStep()" class="px-5 py-2.5 rounded-lg bg-accent text-ink font-semibold hover:bg-accentdark hover:text-white">İleri</button>
        </div>
      </div>

      <!-- STEP 3: PARÇA & AÇIKLAMA -->
      <div class="wizard-step hidden" data-step="3">
        <h2 class="font-display font-semibold text-lg mb-4"><i class="fa-solid fa-gears text-accentdark mr-1"></i> Aksesuar / Modifiye Parça Bilgisi</h2>
        <div class="space-y-4">
          <div>
            <label class="text-sm font-medium block mb-1">Aksesuar / Modifiye Kategorisi</label>
            <select id="category-select" class="w-full border border-black/15 rounded-lg px-3 py-2.5 bg-white"></select>
          </div>
          <div>
            <label class="text-sm font-medium block mb-1">İhtiyaç Açıklaması</label>
            <textarea id="description-input" oninput="updateDescCounter()" rows="4" placeholder="Örn: 17 inç spor jant arıyorum, orijinal veya temiz çıkma olabilir / Ön tampon için body kit istiyorum."
              class="w-full border border-black/15 rounded-lg px-3 py-2.5"></textarea>
            <p id="desc-counter" class="text-xs text-steel mt-1 text-right">0 karakter</p>
          </div>
        </div>
        <div class="flex justify-between mt-6">
          <button onclick="prevStep()" class="px-4 py-2.5 rounded-lg text-steel font-medium hover:bg-black/5">Geri</button>
          <button onclick="nextStep()" class="px-5 py-2.5 rounded-lg bg-accent text-ink font-semibold hover:bg-accentdark hover:text-white">İleri</button>
        </div>
      </div>

      <!-- STEP 4: KONUM -->
      <div class="wizard-step hidden" data-step="4">
        <h2 class="font-display font-semibold text-lg mb-4"><i class="fa-solid fa-location-dot text-accentdark mr-1"></i> Konum</h2>
        <div class="space-y-4">
          <div>
            <label class="text-sm font-medium block mb-1">İl</label>
            <div class="flex gap-2">
              <select id="province-select" onchange="onProvinceChange()" class="flex-1 w-full border border-black/15 rounded-lg px-3 py-2.5 bg-white">
                <option value="">Yükleniyor...</option>
              </select>
              <button type="button" id="province-retry-btn" onclick="loadProvinces()" class="hidden px-3 py-2.5 rounded-lg bg-ink text-white text-sm whitespace-nowrap"><i class="fa-solid fa-rotate-right mr-1"></i>Tekrar Dene</button>
            </div>
          </div>
          <div>
            <label class="text-sm font-medium block mb-1">İlçe</label>
            <div class="flex gap-2">
              <select id="district-select" disabled class="flex-1 w-full border border-black/15 rounded-lg px-3 py-2.5 bg-white disabled:bg-black/5">
                <option value="">Önce il seçin</option>
              </select>
              <button type="button" id="district-retry-btn" onclick="onProvinceChange()" class="hidden px-3 py-2.5 rounded-lg bg-ink text-white text-sm whitespace-nowrap"><i class="fa-solid fa-rotate-right mr-1"></i>Tekrar Dene</button>
            </div>
          </div>
        </div>
        <div class="flex justify-between mt-6">
          <button onclick="prevStep()" class="px-4 py-2.5 rounded-lg text-steel font-medium hover:bg-black/5">Geri</button>
          <button onclick="nextStep()" class="px-5 py-2.5 rounded-lg bg-accent text-ink font-semibold hover:bg-accentdark hover:text-white">İleri</button>
        </div>
      </div>

      <!-- STEP 5: İLETİŞİM & YAYINLA -->
      <div class="wizard-step hidden" data-step="5">
        <h2 class="font-display font-semibold text-lg mb-4"><i class="fa-solid fa-phone text-accentdark mr-1"></i> İletişim ve Yayınla</h2>

        <div id="wizard-summary" class="bg-paper rounded-lg p-4 mb-5"></div>

        <label class="text-sm font-medium block mb-1">Telefon Numarası</label>
        <p class="text-xs text-steel mb-2">Sahte ilanları önlemek için telefon doğrulaması zorunludur. Numaran ilanda gizli kalır, sadece Premium Abone esnaflara açılır.</p>
        <div class="flex gap-2 mb-1">
          <input id="phone-input" type="tel" placeholder="0532 111 22 33" class="flex-1 border border-black/15 rounded-lg px-3 py-2.5">
          <button id="send-otp-btn" data-label="Doğrulama Kodu Gönder" onclick="sendOtp()" class="px-4 py-2.5 rounded-lg bg-ink text-white text-sm font-medium whitespace-nowrap hover:bg-ink/90">Doğrulama Kodu Gönder</button>
        </div>

        <div id="otp-group" class="hidden mt-3">
          <p id="otp-demo-note" class="hidden text-xs bg-accent/15 text-accentdark rounded-md px-3 py-2 mb-3"></p>
          <label class="text-sm font-medium block mb-1">Doğrulama Kodu</label>
          <div class="flex gap-2 items-center">
            <input id="otp-input" type="text" inputmode="numeric" maxlength="4" placeholder="••••" class="otp-input w-28 border border-black/15 rounded-lg px-3 py-2.5">
            <button id="verify-otp-btn" onclick="verifyOtp()" class="px-4 py-2.5 rounded-lg bg-accent text-ink text-sm font-semibold hover:bg-accentdark hover:text-white">Doğrula</button>
            <span id="otp-verified-badge" class="hidden text-success text-sm font-medium"><i class="fa-solid fa-circle-check mr-1"></i>Doğrulandı</span>
          </div>
        </div>

        <button id="publish-btn" disabled onclick="submitListing()" class="mt-6 w-full py-3 rounded-lg bg-accent text-ink font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-accentdark hover:text-white transition-colors">
          Ücretsiz İlanı Yayınla
        </button>

        <div class="flex justify-start mt-4">
          <button onclick="prevStep()" class="px-4 py-2.5 rounded-lg text-steel font-medium hover:bg-black/5">Geri</button>
        </div>
      </div>
    </div>

    <!-- YAYIN SONRASI BAŞARI EKRANI -->
    <div id="wizard-success" class="hidden bg-white border border-black/10 rounded-xl p-8 text-center">
      <i class="fa-solid fa-circle-check text-success text-4xl mb-3"></i>
      <h2 class="font-display font-bold text-xl mb-1">İlanın yayınlandı!</h2>
      <p id="success-summary" class="text-sm text-steel mb-6"></p>
      <div class="flex flex-col sm:flex-row justify-center gap-3">
        <button onclick="resetWizard()" class="px-5 py-2.5 rounded-lg bg-ink text-white font-medium hover:bg-ink/90">Yeni İlan Ver</button>
        <button onclick="showView('mylistings'); document.getElementById('my-phone-input').value = wizard.phone;" class="px-5 py-2.5 rounded-lg border border-black/15 font-medium hover:bg-black/5">İlanlarımı Gör</button>
      </div>
    </div>
  </div>
</section>

<!-- ============================= SATICI PANELİ ============================= -->
<section id="view-seller" class="hidden">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <div>
        <h1 class="font-display font-bold text-2xl mb-1">Talep Havuzu</h1>
        <p class="text-steel text-sm">Bölgendeki tüm parça taleplerini gör, gizli fiyat teklifi gönder.</p>
      </div>

      <div class="flex items-center gap-3 bg-white border border-black/10 rounded-lg p-2.5 self-start">
        <i id="mode-icon" class="fa-solid fa-lock text-steel px-1"></i>
        <div class="flex rounded-md overflow-hidden border border-black/10">
          <button id="mode-free-btn" class="mode-btn px-3 py-1.5 text-sm font-medium" onclick="setSellerMode(false)">Ücretsiz Üye</button>
          <button id="mode-premium-btn" class="mode-btn px-3 py-1.5 text-sm font-medium" onclick="setSellerMode(true)">Premium Abone</button>
        </div>
      </div>
    </div>

    <p id="mode-caption" class="text-xs text-steel mb-6 -mt-3">
      <i class="fa-solid fa-circle-info mr-1"></i>Esnaf Modu Simülatörü: gerçek bir ödeme alınmaz, sadece iletişim kilidinin nasıl çalıştığını gösterir.
    </p>

    <div class="bg-white border border-black/10 rounded-lg p-4 mb-6 grid sm:grid-cols-3 gap-3">
      <select id="filter-province" onchange="refreshListings()" class="border border-black/15 rounded-lg px-3 py-2 text-sm bg-white">
        <option value="">Tüm İller</option>
      </select>
      <select id="filter-brand" onchange="refreshListings()" class="border border-black/15 rounded-lg px-3 py-2 text-sm bg-white">
        <option value="">Tüm Markalar</option>
      </select>
      <select id="filter-category" onchange="refreshListings()" class="border border-black/15 rounded-lg px-3 py-2 text-sm bg-white">
        <option value="">Tüm Kategoriler</option>
      </select>
    </div>

    <div id="listings-grid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4"></div>
  </div>
</section>

<!-- ============================= İLANLARIM ============================= -->
<section id="view-mylistings" class="hidden">
  <div class="max-w-2xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
    <h1 class="font-display font-bold text-2xl mb-1">İlanlarım</h1>
    <p class="text-steel text-sm mb-6">Doğruladığın telefon numaranı gir, ilanlarını ve gelen teklifleri gör.</p>
    <div class="flex gap-2 mb-6">
      <input id="my-phone-input" type="tel" placeholder="0532 111 22 33" class="flex-1 border border-black/15 rounded-lg px-3 py-2.5 bg-white">
      <button onclick="fetchMyListings()" class="px-4 py-2.5 rounded-lg bg-ink text-white text-sm font-medium hover:bg-ink/90">Görüntüle</button>
    </div>
    <div id="my-listings-result"></div>
  </div>
</section>
</main>

<!-- TEKLİF MODALI -->
<div id="offer-modal" class="hidden fixed inset-0 z-50 bg-ink/60 flex items-end sm:items-center justify-center p-0 sm:p-4">
  <div class="bg-white w-full sm:max-w-md rounded-t-xl sm:rounded-xl p-5 sm:p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="font-display font-semibold text-lg">Fiyat Teklifi Gönder</h3>
      <button onclick="closeOfferModal()" class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-black/5" aria-label="Kapat"><i class="fa-solid fa-xmark"></i></button>
    </div>
    <form id="offer-form" onsubmit="submitOffer(event)" class="space-y-3">
      <div>
        <label class="text-sm font-medium block mb-1">İşletme / Ad Soyad</label>
        <input id="offer-seller-name" type="text" required class="w-full border border-black/15 rounded-lg px-3 py-2.5" placeholder="Örn: Yılmaz Oto Çıkma">
      </div>
      <div>
        <label class="text-sm font-medium block mb-1">Telefon (alıcıya iletilecek)</label>
        <input id="offer-seller-phone" type="tel" required class="w-full border border-black/15 rounded-lg px-3 py-2.5" placeholder="0532 111 22 33">
      </div>
      <div>
        <label class="text-sm font-medium block mb-1">Teklif Fiyatı (₺)</label>
        <input id="offer-price" type="number" min="1" step="0.01" required class="w-full border border-black/15 rounded-lg px-3 py-2.5" placeholder="Örn: 1500">
      </div>
      <div>
        <label class="text-sm font-medium block mb-1">Mesaj <span class="text-steel font-normal">(opsiyonel)</span></label>
        <textarea id="offer-message" rows="3" class="w-full border border-black/15 rounded-lg px-3 py-2.5" placeholder="Parça stokta, orijinal, temiz çıkma..."></textarea>
      </div>
      <button id="offer-submit-btn" type="submit" class="w-full py-3 rounded-lg bg-accent text-ink font-semibold hover:bg-accentdark hover:text-white transition-colors">
        Teklifi Gönder
      </button>
      <p class="text-xs text-steel text-center">Teklifin sadece bu ilanın sahibine görünür.</p>
    </form>
  </div>
</div>

<div id="toast" class="hidden fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white bg-ink max-w-[90vw] text-center"></div>

<footer class="bg-ink text-white/70 mt-10">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-8 text-sm">
    <p class="text-white font-display font-semibold mb-2">Parça İste</p>
    <p class="mb-1">Bu bir MVP demo uygulamasıdır. SMS doğrulama ve Premium Abonelik iletişim kilidi simülasyondur, gerçek ödeme alınmaz.</p>
    <p>İl / ilçe verileri <a href="https://turkiyeapi.dev" target="_blank" rel="noopener" class="underline hover:text-white">TurkiyeAPI</a> üzerinden anlık olarak çekilir.</p>
  </div>
</footer>

<script>
// ==========================================================================
// GLOBAL STATE
// ==========================================================================
let META = null;
let provincesData = [];
let districtsCache = {};
let sellerMode = false;
let currentStep = 1;
const TOTAL_STEPS = 5;
let myListingsPhone = '';
let currentOfferListingId = null;
let otpResendTimer = null;

let wizard = {
  image_filename: null, ai_filled: false,
  brand: '', model: '', year: '', color: '', engine_package: '',
  part_category: '', description: '',
  province: '', province_id: null, district: '',
  phone: '', phone_verified: false,
};

// ==========================================================================
// UTIL
// ==========================================================================
function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

let toastTimer = null;
function showToast(msg, isError) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'fixed bottom-4 left-1/2 -translate-x-1/2 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white max-w-[90vw] text-center ' + (isError ? 'bg-danger' : 'bg-ink');
  el.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add('hidden'), 3500);
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'az önce';
  if (mins < 60) return mins + ' dk önce';
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return hrs + ' sa önce';
  return Math.floor(hrs / 24) + ' gün önce';
}

// ==========================================================================
// NAV / VIEW SWITCH
// ==========================================================================
function showView(name) {
  ['home', 'buyer', 'seller', 'mylistings'].forEach(v => {
    document.getElementById('view-' + v).classList.toggle('hidden', v !== name);
  });
  document.querySelectorAll('[data-nav]').forEach(b => {
    b.classList.toggle('nav-btn-active', b.dataset.nav === name);
  });
  document.getElementById('mobile-nav').classList.add('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (name === 'seller') refreshListings();
}
function toggleMobileNav() {
  document.getElementById('mobile-nav').classList.toggle('hidden');
}

// ==========================================================================
// BOOT / META
// ==========================================================================
async function boot() {
  try {
    const res = await fetch('/api/meta');
    META = await res.json();
  } catch (e) {
    showToast('Form verileri yüklenemedi, sayfayı yenile.', true);
    return;
  }
  populateBrandSelect();
  populateYearSelect();
  populateColorSelect();
  populateCategorySelect();
  populateFilterSelects();
  loadProvinces();
}

function populateBrandSelect() {
  const sel = document.getElementById('brand-select');
  sel.innerHTML = '<option value="">Marka seçin</option>' +
    Object.keys(META.brands).sort().map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join('');
}
function onBrandChange() {
  const brand = document.getElementById('brand-select').value;
  wizard.brand = brand;
  wizard.model = '';
  const modelSel = document.getElementById('model-select');
  if (!brand) {
    modelSel.innerHTML = '<option value="">Önce marka seçin</option>';
    modelSel.disabled = true;
    return;
  }
  const models = META.brands[brand] || [];
  modelSel.innerHTML = '<option value="">Model seçin</option>' +
    models.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('');
  modelSel.disabled = false;
}
function populateYearSelect() {
  document.getElementById('year-select').innerHTML =
    '<option value="">Yıl seçin</option>' + META.years.map(y => `<option value="${y}">${y}</option>`).join('');
}
function populateColorSelect() {
  document.getElementById('color-select').innerHTML =
    '<option value="">Renk seçin</option>' + META.colors.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}
function populateCategorySelect() {
  document.getElementById('category-select').innerHTML =
    '<option value="">Kategori seçin</option>' + META.categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}
function populateFilterSelects() {
  document.getElementById('filter-brand').innerHTML =
    '<option value="">Tüm Markalar</option>' + Object.keys(META.brands).sort().map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join('');
  document.getElementById('filter-category').innerHTML =
    '<option value="">Tüm Kategoriler</option>' + META.categories.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
}

// ==========================================================================
// İL / İLÇE (TurkiyeAPI — https://turkiyeapi.dev)
// Dayanıklılık için: birincil (nested) uç nokta denenir, başarısız olursa
// alternatif (düz koleksiyon) uç nokta denenir. İkisi de başarısız olursa
// kullanıcıya görünür bir "Tekrar Dene" butonu gösterilir (asla sessizce
// boş kalmaz).
// ==========================================================================
async function fetchJsonSafe(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    return null;
  }
}

async function loadProvinces() {
  const provinceSel = document.getElementById('province-select');
  const retryBtn = document.getElementById('province-retry-btn');
  retryBtn.classList.add('hidden');
  provinceSel.innerHTML = '<option value="">Yükleniyor...</option>';

  let json = await fetchJsonSafe('https://api.turkiyeapi.dev/v2/provinces?fields=id,name&sort=name&limit=100');
  if (!json || !Array.isArray(json.data) || json.data.length === 0) {
    // Alternatif deneme (bazı vekil/CDN önbellekleri sorgu dizesine duyarlı olabilir)
    json = await fetchJsonSafe('https://api.turkiyeapi.dev/v2/provinces?limit=100');
  }
  provincesData = (json && Array.isArray(json.data)) ? json.data : [];

  if (provincesData.length === 0) {
    provinceSel.innerHTML = '<option value="">İl listesi yüklenemedi</option>';
    retryBtn.classList.remove('hidden');
    return;
  }
  provinceSel.innerHTML = '<option value="">İl seçin</option>' +
    provincesData.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
  document.getElementById('filter-province').innerHTML = '<option value="">Tüm İller</option>' +
    provincesData.slice().sort((a, b) => a.name.localeCompare(b.name, 'tr')).map(p => `<option value="${escapeHtml(p.name)}">${escapeHtml(p.name)}</option>`).join('');
}

function extractDistrictArray(json) {
  if (!json) return null;
  let d = json.data;
  if (Array.isArray(d)) return d;
  if (d && Array.isArray(d.districts)) return d.districts;
  return null;
}

async function onProvinceChange() {
  const provinceSel = document.getElementById('province-select');
  const provinceId = provinceSel.value;
  const districtSel = document.getElementById('district-select');
  const retryBtn = document.getElementById('district-retry-btn');
  retryBtn.classList.add('hidden');
  wizard.province = provinceId ? provinceSel.options[provinceSel.selectedIndex].text : '';
  wizard.province_id = provinceId ? Number(provinceId) : null;
  wizard.district = '';

  if (!provinceId) {
    districtSel.innerHTML = '<option value="">Önce il seçin</option>';
    districtSel.disabled = true;
    return;
  }
  districtSel.disabled = true;
  districtSel.innerHTML = '<option value="">Yükleniyor...</option>';

  if (!districtsCache[provinceId] || !districtsCache[provinceId].length) {
    // 1) Birincil: iç içe (nested) uç nokta
    let json = await fetchJsonSafe(`https://api.turkiyeapi.dev/v2/provinces/${provinceId}/districts?fields=id,name&limit=100`);
    let districts = extractDistrictArray(json);
    // 2) Yedek: düz koleksiyon uç noktası, provinceId ile filtrelenmiş
    if (!districts || !districts.length) {
      json = await fetchJsonSafe(`https://api.turkiyeapi.dev/v2/districts?provinceId=${provinceId}&fields=id,name&sort=name&limit=100`);
      districts = extractDistrictArray(json);
    }
    districtsCache[provinceId] = districts || [];
  }

  const districts = districtsCache[provinceId];
  if (!districts.length) {
    districtSel.innerHTML = '<option value="">İlçe listesi yüklenemedi</option>';
    districtSel.disabled = true;
    retryBtn.classList.remove('hidden');
    return;
  }
  districtSel.innerHTML = '<option value="">İlçe seçin</option>' +
    districts.slice().sort((a, b) => a.name.localeCompare(b.name, 'tr')).map(d => `<option value="${escapeHtml(d.name)}">${escapeHtml(d.name)}</option>`).join('');
  districtSel.disabled = false;
}
function onDistrictChange() {
  const sel = document.getElementById('district-select');
  wizard.district = sel.value;
}

// ==========================================================================
// AI VISION SİMÜLASYONU
// ==========================================================================
function onFileSelected(e) {
  const file = e.target.files[0];
  const label = document.getElementById('file-chosen-name');
  const btn = document.getElementById('ai-analyze-btn');
  if (file) {
    label.innerHTML = `<i class="fa-solid fa-paperclip mr-1"></i>${escapeHtml(file.name)}`;
    label.classList.remove('hidden');
    btn.disabled = false;
  } else {
    label.classList.add('hidden');
    btn.disabled = true;
  }
}

async function runAiAnalyze() {
  const fileInput = document.getElementById('ai-file-input');
  const file = fileInput.files[0];
  if (!file) return;
  const btn = document.getElementById('ai-analyze-btn');
  const resultBox = document.getElementById('ai-result-box');
  const loadingBox = document.getElementById('ai-loading-box');
  btn.disabled = true;
  loadingBox.classList.remove('hidden');
  resultBox.classList.add('hidden');
  const fd = new FormData();
  fd.append('file', file);
  try {
    const res = await fetch('/api/ai-analyze', { method: 'POST', body: fd });
    if (!res.ok) throw new Error('analiz başarısız');
    const data = await res.json();
    applyAiResult(data);
  } catch (e) {
    showToast('Yapay zekâ analizi başarısız oldu, bilgileri elle girebilirsin.', true);
  } finally {
    loadingBox.classList.add('hidden');
    btn.disabled = false;
  }
}

function applyAiResult(data) {
  wizard.ai_filled = true;
  wizard.image_filename = data.source_filename || null;

  document.getElementById('brand-select').value = data.brand;
  onBrandChange();
  document.getElementById('model-select').value = data.model;
  wizard.model = data.model;
  document.getElementById('year-select').value = data.year;
  wizard.year = data.year;
  document.getElementById('color-select').value = data.color;
  wizard.color = data.color;
  document.getElementById('category-select').value = data.part_category;
  wizard.part_category = data.part_category;
  document.getElementById('description-input').value = data.description;
  wizard.description = data.description;
  updateDescCounter();

  const resultBox = document.getElementById('ai-result-box');
  resultBox.innerHTML = `
    <div class="flex items-start gap-3">
      <i class="fa-solid fa-wand-magic-sparkles text-accentdark text-lg mt-0.5"></i>
      <div>
        <p class="font-medium text-sm">Yapay zekâ tespiti tamamlandı</p>
        <p class="text-sm text-steel mt-1">${escapeHtml(data.brand)} ${escapeHtml(data.model)} · ${data.year} · ${escapeHtml(data.color)} — ${escapeHtml(data.part_category)}</p>
        <p class="text-xs text-steel mt-2">Bu bilgiler 2. ve 3. adıma otomatik aktarıldı. Dilersen düzenleyebilirsin.</p>
      </div>
    </div>`;
  resultBox.classList.remove('hidden');
  showToast('AI analizi tamamlandı, form dolduruldu.');
}

// ==========================================================================
// WIZARD NAVİGASYON
// ==========================================================================
function goToStep(n) {
  if (n < 1 || n > TOTAL_STEPS) return;
  document.querySelectorAll('.wizard-step').forEach(el => {
    el.classList.toggle('hidden', Number(el.dataset.step) !== n);
  });
  document.querySelectorAll('.step-dot').forEach(el => {
    const s = Number(el.dataset.step);
    el.classList.toggle('step-dot-active', s === n);
    el.classList.toggle('step-dot-done', s < n);
  });
  currentStep = n;
  clearStepError();
  if (n === 5) renderSummary();
  const anchor = document.getElementById('view-buyer');
  window.scrollTo({ top: anchor.offsetTop - 70, behavior: 'smooth' });
}
function nextStep() {
  if (!validateStep(currentStep)) return;
  goToStep(currentStep + 1);
}
function prevStep() { goToStep(currentStep - 1); }

function validateStep(n) {
  clearStepError();
  if (n === 2) {
    wizard.brand = document.getElementById('brand-select').value;
    wizard.model = document.getElementById('model-select').value;
    wizard.year = document.getElementById('year-select').value;
    wizard.color = document.getElementById('color-select').value;
    wizard.engine_package = document.getElementById('engine-input').value.trim();
    if (!wizard.brand || !wizard.model || !wizard.year || !wizard.color) {
      showStepError('Lütfen marka, model, yıl ve renk bilgilerini seçin.');
      return false;
    }
  }
  if (n === 3) {
    wizard.part_category = document.getElementById('category-select').value;
    wizard.description = document.getElementById('description-input').value.trim();
    if (!wizard.part_category) { showStepError('Lütfen parça kategorisi seçin.'); return false; }
    if (wizard.description.length < 10) { showStepError('Açıklama en az 10 karakter olmalı.'); return false; }
  }
  if (n === 4) {
    onDistrictChange();
    if (!wizard.province || !wizard.district) { showStepError('Lütfen il ve ilçe seçin.'); return false; }
  }
  return true;
}
function showStepError(msg) {
  document.getElementById('wizard-error-text').textContent = msg;
  document.getElementById('wizard-error').classList.remove('hidden');
}
function clearStepError() {
  document.getElementById('wizard-error').classList.add('hidden');
}
function updateDescCounter() {
  const val = document.getElementById('description-input').value;
  document.getElementById('desc-counter').textContent = val.length + ' karakter';
}
function renderSummary() {
  document.getElementById('wizard-summary').innerHTML = `
    <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
      <dt class="text-steel">Araç</dt><dd class="font-medium">${escapeHtml(wizard.brand)} ${escapeHtml(wizard.model)} · ${escapeHtml(String(wizard.year))}</dd>
      <dt class="text-steel">Renk</dt><dd>${escapeHtml(wizard.color)}</dd>
      <dt class="text-steel">Motor / Paket</dt><dd>${wizard.engine_package ? escapeHtml(wizard.engine_package) : '—'}</dd>
      <dt class="text-steel">Parça</dt><dd>${escapeHtml(wizard.part_category)}</dd>
      <dt class="text-steel">Konum</dt><dd>${escapeHtml(wizard.province)} / ${escapeHtml(wizard.district)}</dd>
    </dl>
    <p class="text-sm mt-3 border-t border-black/10 pt-3">${escapeHtml(wizard.description)}</p>`;
}

// ==========================================================================
// OTP (SMS DOĞRULAMA SİMÜLASYONU)
// ==========================================================================
async function sendOtp() {
  const phone = document.getElementById('phone-input').value.trim();
  if (!phone) { showToast('Lütfen telefon numaranı gir.', true); return; }
  const btn = document.getElementById('send-otp-btn');
  btn.disabled = true;
  try {
    const res = await fetch('/api/otp/send', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone })
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.detail || 'Kod gönderilemedi.', true); btn.disabled = false; return; }
    wizard.phone = phone;
    document.getElementById('otp-group').classList.remove('hidden');
    const note = document.getElementById('otp-demo-note');
    note.textContent = `Demo modu: doğrulama kodun ${data.demo_code} (gerçek SMS gönderilmez).`;
    note.classList.remove('hidden');
    showToast('Doğrulama kodu gönderildi.');
    startOtpCooldown();
  } catch (e) {
    showToast('Kod gönderilemedi, tekrar dene.', true);
    btn.disabled = false;
  }
}
function startOtpCooldown() {
  const btn = document.getElementById('send-otp-btn');
  let seconds = 20;
  btn.disabled = true;
  clearInterval(otpResendTimer);
  const tick = () => {
    if (seconds < 0) {
      clearInterval(otpResendTimer);
      btn.disabled = false;
      btn.textContent = 'Kodu Tekrar Gönder';
      return;
    }
    btn.textContent = `Tekrar gönder (${seconds}sn)`;
    seconds--;
  };
  tick();
  otpResendTimer = setInterval(tick, 1000);
}
async function verifyOtp() {
  const phone = wizard.phone;
  const code = document.getElementById('otp-input').value.trim();
  if (code.length !== 4) { showToast('4 haneli kodu gir.', true); return; }
  try {
    const res = await fetch('/api/otp/verify', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, code })
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.detail || 'Kod hatalı.', true); return; }
    wizard.phone_verified = true;
    document.getElementById('otp-verified-badge').classList.remove('hidden');
    document.getElementById('publish-btn').disabled = false;
    document.getElementById('phone-input').disabled = true;
    document.getElementById('send-otp-btn').disabled = true;
    document.getElementById('otp-input').disabled = true;
    document.getElementById('verify-otp-btn').disabled = true;
    clearInterval(otpResendTimer);
    showToast('Telefon doğrulandı ✓');
  } catch (e) {
    showToast('Doğrulama başarısız, tekrar dene.', true);
  }
}

// ==========================================================================
// İLAN YAYINLA
// ==========================================================================
async function submitListing() {
  if (!wizard.phone_verified) { showToast('Önce telefonunu doğrula.', true); return; }
  const btn = document.getElementById('publish-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yayınlanıyor...';
  const payload = {
    phone: wizard.phone, brand: wizard.brand, model: wizard.model,
    year: Number(wizard.year), engine_package: wizard.engine_package,
    color: wizard.color, part_category: wizard.part_category,
    description: wizard.description, province: wizard.province,
    province_id: wizard.province_id, district: wizard.district,
    ai_filled: wizard.ai_filled, image_filename: wizard.image_filename,
  };
  try {
    const res = await fetch('/api/listings', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || 'İlan yayınlanamadı.', true);
      btn.disabled = false; btn.innerHTML = 'Ücretsiz İlanı Yayınla';
      return;
    }
    document.getElementById('wizard-form-wrap').classList.add('hidden');
    const box = document.getElementById('wizard-success');
    box.classList.remove('hidden');
    document.getElementById('success-summary').textContent =
      `${data.brand} ${data.model} için ilanın #${data.id} numarasıyla yayınlandı.`;
  } catch (e) {
    showToast('Bir hata oluştu, tekrar dene.', true);
    btn.disabled = false; btn.innerHTML = 'Ücretsiz İlanı Yayınla';
  }
}

function resetWizard() {
  wizard = {
    image_filename: null, ai_filled: false, brand: '', model: '', year: '',
    color: '', engine_package: '', part_category: '', description: '',
    province: '', province_id: null, district: '', phone: '', phone_verified: false,
  };
  document.getElementById('wizard-form-wrap').classList.remove('hidden');
  document.getElementById('wizard-success').classList.add('hidden');

  document.getElementById('ai-file-input').value = '';
  document.getElementById('ai-result-box').classList.add('hidden');
  document.getElementById('ai-loading-box').classList.add('hidden');
  document.getElementById('file-chosen-name').classList.add('hidden');
  document.getElementById('ai-analyze-btn').disabled = true;

  document.getElementById('brand-select').value = '';
  onBrandChange();
  document.getElementById('year-select').value = '';
  document.getElementById('color-select').value = '';
  document.getElementById('engine-input').value = '';
  document.getElementById('category-select').value = '';
  document.getElementById('description-input').value = '';
  updateDescCounter();
  document.getElementById('province-select').value = '';
  onProvinceChange();

  document.getElementById('phone-input').value = ''; document.getElementById('phone-input').disabled = false;
  document.getElementById('otp-group').classList.add('hidden');
  document.getElementById('otp-input').value = ''; document.getElementById('otp-input').disabled = false;
  document.getElementById('send-otp-btn').disabled = false; document.getElementById('send-otp-btn').textContent = 'Doğrulama Kodu Gönder';
  document.getElementById('verify-otp-btn').disabled = false;
  document.getElementById('otp-verified-badge').classList.add('hidden');
  document.getElementById('publish-btn').disabled = true; document.getElementById('publish-btn').innerHTML = 'Ücretsiz İlanı Yayınla';

  goToStep(1);
}

// ==========================================================================
// SATICI PANELİ
// ==========================================================================
function setSellerMode(premium) {
  sellerMode = premium;
  document.getElementById('mode-free-btn').classList.toggle('mode-btn-active', !premium);
  document.getElementById('mode-premium-btn').classList.toggle('mode-btn-active', premium);
  const icon = document.getElementById('mode-icon');
  icon.className = premium ? 'fa-solid fa-lock-open text-success px-1' : 'fa-solid fa-lock text-steel px-1';
  showToast(premium ? 'Demo: Premium Abone moduna geçildi — iletişim bilgileri açıldı.' : 'Demo: Ücretsiz Üye moduna geçildi.');
  refreshListings();
}

async function refreshListings() {
  const grid = document.getElementById('listings-grid');
  grid.innerHTML = '<p class="col-span-full text-center text-steel py-10"><i class="fa-solid fa-spinner fa-spin"></i> Talepler yükleniyor...</p>';
  const params = new URLSearchParams({ is_premium: sellerMode });
  const province = document.getElementById('filter-province').value;
  const brand = document.getElementById('filter-brand').value;
  const category = document.getElementById('filter-category').value;
  if (province) params.set('province', province);
  if (brand) params.set('brand', brand);
  if (category) params.set('category', category);
  try {
    const res = await fetch('/api/listings?' + params.toString());
    const items = await res.json();
    renderListings(items);
  } catch (e) {
    grid.innerHTML = '<p class="col-span-full text-center text-danger py-10">Talepler yüklenemedi.</p>';
  }
}

function renderListings(items) {
  const grid = document.getElementById('listings-grid');
  if (!items.length) {
    grid.innerHTML = `<div class="col-span-full text-center py-14 text-steel">
      <i class="fa-solid fa-inbox text-3xl mb-3"></i>
      <p>Bu filtrelerle eşleşen bir talep yok.</p>
    </div>`;
    return;
  }
  grid.innerHTML = items.map(renderListingCard).join('');
}

function renderListingCard(x) {
  let contact;
  if (x.locked) {
    contact = `
      <div class="flex items-center gap-2 text-steel bg-paper rounded-md px-3 py-2 text-xs">
        <i class="fa-solid fa-lock"></i>
        <span>${escapeHtml(x.phone_display)} — sadece Premium Aboneler görebilir</span>
      </div>
      <div class="flex gap-2 mt-2">
        <button disabled title="Premium'a geçin" class="flex-1 text-sm py-2 rounded-md bg-black/5 text-steel/60 cursor-not-allowed"><i class="fa-solid fa-phone mr-1"></i>Ara</button>
        <button disabled title="Premium'a geçin" class="flex-1 text-sm py-2 rounded-md bg-black/5 text-steel/60 cursor-not-allowed"><i class="fa-brands fa-whatsapp mr-1"></i>WhatsApp</button>
      </div>`;
  } else {
    const digits = (x.phone_display || '').replace(/\s+/g, '');
    const waDigits = '90' + digits.slice(1);
    const waText = encodeURIComponent(`Merhaba, ${x.brand} ${x.model} için verdiğiniz "${x.part_category}" talebi hakkında yazıyorum.`);
    contact = `
      <div class="flex items-center gap-2 text-success bg-success/10 rounded-md px-3 py-2 text-xs font-medium">
        <i class="fa-solid fa-circle-check"></i><span>${escapeHtml(x.phone_display)}</span>
      </div>
      <div class="flex gap-2 mt-2">
        <a href="tel:${digits}" class="flex-1 text-sm py-2 rounded-md bg-ink text-white text-center hover:bg-ink/90"><i class="fa-solid fa-phone mr-1"></i>Ara</a>
        <a href="https://wa.me/${waDigits}?text=${waText}" target="_blank" rel="noopener" class="flex-1 text-sm py-2 rounded-md bg-success text-white text-center hover:opacity-90"><i class="fa-brands fa-whatsapp mr-1"></i>WhatsApp</a>
      </div>`;
  }
  return `
  <article class="bg-white border border-black/10 ${x.locked ? 'border-l-4 border-l-black/20' : 'border-l-4 border-l-success'} rounded-lg p-4 flex flex-col">
    <div class="flex items-center justify-between mb-2">
      <span class="text-[11px] font-medium px-2 py-0.5 rounded bg-paper text-steel">${escapeHtml(x.part_category)}</span>
      <span class="text-[11px] text-steel">${timeAgo(x.created_at)}</span>
    </div>
    <h3 class="font-display font-semibold text-base leading-snug">${escapeHtml(x.brand)} ${escapeHtml(x.model)} <span class="text-steel font-normal text-sm">· ${x.year}</span></h3>
    <p class="text-xs text-steel mt-1"><i class="fa-solid fa-palette w-4"></i> ${escapeHtml(x.color)}${x.engine_package ? ' · ' + escapeHtml(x.engine_package) : ''}</p>
    <p class="text-xs text-steel mt-0.5 mb-2"><i class="fa-solid fa-location-dot w-4"></i> ${escapeHtml(x.province)} / ${escapeHtml(x.district)}</p>
    <p class="text-sm mb-3 flex-1">${escapeHtml(x.description)}</p>
    ${x.ai_filled ? '<span class="inline-flex items-center gap-1 text-[11px] text-accentdark mb-2"><i class="fa-solid fa-wand-magic-sparkles"></i> AI destekli ilan</span>' : ''}
    <p class="text-[11px] text-steel mb-2"><i class="fa-solid fa-tags"></i> ${x.offer_count} teklif verildi</p>
    <div class="border-t border-black/10 pt-3">${contact}</div>
    <button onclick="openOfferModal('${x.id}')" class="mt-3 w-full text-sm py-2 rounded-md bg-accent text-ink font-medium hover:bg-accentdark hover:text-white transition-colors"><i class="fa-solid fa-hand-holding-dollar mr-1"></i> Teklif Ver</button>
  </article>`;
}

// ==========================================================================
// TEKLİF MODALI
// ==========================================================================
function openOfferModal(id) {
  currentOfferListingId = id;
  document.getElementById('offer-form').reset();
  document.getElementById('offer-modal').classList.remove('hidden');
}
function closeOfferModal() {
  document.getElementById('offer-modal').classList.add('hidden');
  currentOfferListingId = null;
}
async function submitOffer(e) {
  e.preventDefault();
  const seller_name = document.getElementById('offer-seller-name').value.trim();
  const seller_phone = document.getElementById('offer-seller-phone').value.trim();
  const price = document.getElementById('offer-price').value;
  const message = document.getElementById('offer-message').value.trim();
  if (!seller_name || !seller_phone || !price) { showToast('Lütfen isim, telefon ve fiyat gir.', true); return; }
  const btn = document.getElementById('offer-submit-btn');
  btn.disabled = true;
  try {
    const res = await fetch(`/api/listings/${currentOfferListingId}/offers`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seller_name, seller_phone, price: Number(price), message })
    });
    const data = await res.json();
    if (!res.ok) { showToast(data.detail || 'Teklif gönderilemedi.', true); btn.disabled = false; return; }
    showToast('Teklifin gönderildi ✓');
    closeOfferModal();
    refreshListings();
  } catch (e) {
    showToast('Bir hata oluştu.', true);
  } finally {
    btn.disabled = false;
  }
}

// ==========================================================================
// İLANLARIM
// ==========================================================================
async function fetchMyListings() {
  const phone = document.getElementById('my-phone-input').value.trim();
  if (!phone) { showToast('Telefon numaranı gir.', true); return; }
  myListingsPhone = phone;
  const box = document.getElementById('my-listings-result');
  box.innerHTML = '<p class="text-center text-steel py-8"><i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor...</p>';
  try {
    const res = await fetch('/api/my-listings?phone=' + encodeURIComponent(phone));
    const data = await res.json();
    if (!res.ok) { box.innerHTML = `<p class="text-center text-danger py-8">${escapeHtml(data.detail || 'Hata')}</p>`; return; }
    renderMyListings(data);
  } catch (e) {
    box.innerHTML = '<p class="text-center text-danger py-8">Bir hata oluştu.</p>';
  }
}

function renderMyListings(items) {
  const box = document.getElementById('my-listings-result');
  if (!items.length) {
    box.innerHTML = '<p class="text-center text-steel py-8">Bu numarayla kayıtlı bir ilan bulunamadı.</p>';
    return;
  }
  box.innerHTML = items.map(x => `
    <div class="bg-white border border-black/10 rounded-lg p-4 mb-4">
      <div class="flex items-center justify-between mb-2">
        <h3 class="font-display font-semibold">${escapeHtml(x.brand)} ${escapeHtml(x.model)} · ${x.year}</h3>
        <span class="text-xs px-2 py-0.5 rounded ${x.status === 'active' ? 'bg-success/10 text-success' : 'bg-black/5 text-steel'}">${x.status === 'active' ? 'Aktif' : 'Kapalı'}</span>
      </div>
      <p class="text-sm text-steel mb-1">${escapeHtml(x.part_category)} · ${escapeHtml(x.province)}/${escapeHtml(x.district)}</p>
      <p class="text-sm mb-3">${escapeHtml(x.description)}</p>
      <p class="text-xs text-steel mb-2">${x.offer_count} teklif alındı</p>
      ${x.offers.length ? `<div class="space-y-2 mb-3">${x.offers.map(o => `
        <div class="flex items-center justify-between bg-paper rounded-md px-3 py-2 text-sm gap-3">
          <div class="min-w-0">
            <p class="font-medium truncate">${escapeHtml(o.seller_name)} <span class="text-steel font-normal">· ${escapeHtml(o.seller_phone_display)}</span></p>
            ${o.message ? `<p class="text-xs text-steel truncate">${escapeHtml(o.message)}</p>` : ''}
          </div>
          <span class="font-display font-semibold text-accentdark shrink-0">₺${Number(o.price).toLocaleString('tr-TR')}</span>
        </div>`).join('')}</div>` : '<p class="text-xs text-steel mb-3">Henüz teklif yok.</p>'}
      ${x.status === 'active' ? `<button onclick="closeMyListing('${x.id}')" class="text-xs text-danger hover:underline"><i class="fa-solid fa-xmark"></i> İlanı kapat</button>` : ''}
    </div>`).join('');
}

async function closeMyListing(id) {
  if (!confirm('Bu ilanı kapatmak istediğine emin misin?')) return;
  try {
    const res = await fetch(`/api/listings/${id}/close`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: myListingsPhone })
    });
    if (!res.ok) { showToast('Kapatılamadı.', true); return; }
    showToast('İlan kapatıldı.');
    fetchMyListings();
  } catch (e) { showToast('Bir hata oluştu.', true); }
}

// ==========================================================================
// INIT
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  boot();
  goToStep(1);
  document.getElementById('mode-free-btn').classList.add('mode-btn-active');
  document.getElementById('district-select').addEventListener('change', onDistrictChange);
});
</script>
</body>
</html>
"""


# ==========================================================================
# 8) UYGULAMA GİRİŞ NOKTASI — Render.com için dinamik PORT desteği
# ==========================================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
