# -*- coding: utf-8 -*-
"""
PARÇA İSTE — Tersine İlan / İstek Pazarı (PRO v5)
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
- Veri katmanı: Üretimde DATABASE_URL ile PostgreSQL, lokal geliştirmede SQLite kullanılır. Kullanıcı, oturum, ilan, teklif, favori, mesaj ve bildirim verileri kalıcıdır.
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
import hashlib
import sqlite3
import base64
import hmac
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field, field_validator
from typing import Dict, List

# ==========================================================================
# 1) SABİT VERİLER — Marka / Model / Renk / Parça Kategorisi
# ==========================================================================
# Not: Türkiye'de en yaygın 20 marka ve her markanın en popüler modelleri
# sert kodludur (hardcoded). Bu liste, aksesuar/modifiye parçasının hangi
# araca uygun olduğunu belirlemek için kullanılır.

CAR_DATA: Dict[str, List[str]] = {
    "Renault": [
        "Clio", "Megane", "Symbol", "Fluence", "Talisman",
        "Captur", "Kadjar", "Kangoo", "Austral", "Arkana",
        "Espace", "Rafale", "Zoe"
    ],
    "Fiat": [
        "Egea", "Linea", "Albea", "Doblo", "Punto", "Fiorino",
        "Panda", "Tipo", "Palio", "500", "500X", "500L"
    ],
    "Volkswagen": [
        "Golf", "Passat", "Polo", "Jetta", "Bora", "Caddy",
        "Tiguan", "T-Roc", "Taigo", "Touareg", "Transporter",
        "Arteon", "ID.3", "ID.4", "ID.5", "ID.7"
    ],
    "Ford": [
        "Focus", "Fiesta", "Mondeo", "Connect", "Courier",
        "Kuga", "Ranger", "Transit", "Puma", "Mustang",
        "Explorer", "Tourneo Custom"
    ],
    "Opel": [
        "Astra", "Corsa", "Vectra", "Insignia", "Combo",
        "Mokka", "Meriva", "Zafira", "Grandland", "Crossland"
    ],
    "Toyota": [
        "Corolla", "Yaris", "Auris", "Hilux", "C-HR", "RAV4",
        "Avensis", "Camry", "Land Cruiser", "Prius", "Aygo"
    ],
    "Hyundai": [
        "i10", "i20", "i30", "Accent", "Accent Blue",
        "Elantra", "Tucson", "Kona", "Bayon", "Santa Fe",
        "IONIQ", "IONIQ 5", "IONIQ 6"
    ],
    "Peugeot": [
        "106", "206", "207", "208", "301", "307", "308",
        "3008", "2008", "407", "508", "5008", "Partner",
        "Rifter", "Expert"
    ],
    "Citroën": [
        "C1", "C2", "C3", "C4", "C5", "C3 Aircross",
        "C4 Cactus", "C4 X", "C5 Aircross", "Berlingo",
        "Jumper", "Jumpy"
    ],
    "Honda": [
        "Civic", "City", "CR-V", "HR-V", "Jazz", "Accord",
        "CR-Z", "e:Ny1"
    ],
    "Nissan": [
        "Micra", "Almera", "Juke", "Qashqai", "X-Trail",
        "Navara", "Note", "Primera", "Leaf"
    ],
    "Chevrolet": [
        "Aveo", "Cruze", "Lacetti", "Captiva", "Spark",
        "Epica", "Kalos", "Malibu"
    ],
    "Škoda": [
        "Fabia", "Scala", "Octavia", "Superb", "Rapid",
        "Yeti", "Kamiq", "Karoq", "Kodiaq", "Enyaq"
    ],
    "SEAT": [
        "Ibiza", "Leon", "Toledo", "Cordoba", "Altea",
        "Arona", "Ateca", "Tarraco"
    ],
    "Mercedes-Benz": [
        "A-Serisi", "B-Serisi", "C-Serisi", "E-Serisi",
        "S-Serisi", "CLA", "GLA", "GLB", "GLC", "GLE",
        "GLS", "Vito", "V-Class", "Sprinter"
    ],
    "BMW": [
        "1 Serisi", "2 Serisi", "3 Serisi", "4 Serisi",
        "5 Serisi", "6 Serisi", "7 Serisi",
        "X1", "X2", "X3", "X4", "X5", "X6", "X7",
        "i4", "iX", "i5", "i7"
    ],
    "Audi": [
        "A1", "A3", "A4", "A5", "A6", "A7", "A8",
        "Q2", "Q3", "Q5", "Q7", "Q8", "e-tron"
    ],
    "Dacia": [
        "Sandero", "Sandero Stepway", "Logan", "Duster",
        "Lodgy", "Dokker", "Jogger", "Spring"
    ],
    "Kia": [
        "Picanto", "Rio", "Ceed", "Stonic", "Sportage",
        "Sorento", "Niro", "EV6", "EV9"
    ],
    "Suzuki": [
        "Swift", "Vitara", "S-Cross", "Jimny", "Baleno",
        "Ignis", "Across"
    ],
    "Tesla": [
        "Model 3", "Model Y", "Model S", "Model X"
    ],
    "Volvo": [
        "S60", "S90", "V40", "V60", "V90",
        "XC40", "XC60", "XC90"
    ],
    "Mazda": [
        "Mazda 2", "Mazda 3", "Mazda 6",
        "CX-3", "CX-30", "CX-5", "CX-60"
    ],
    "Mitsubishi": [
        "Colt", "Lancer", "ASX", "Outlander", "L200"
    ],
    "Subaru": [
        "Impreza", "Forester", "XV", "Outback", "BRZ"
    ],
    "Jeep": [
        "Renegade", "Compass", "Cherokee", "Grand Cherokee",
        "Wrangler", "Avenger"
    ],
    "Alfa Romeo": [
        "Giulietta", "Giulia", "Stelvio", "Tonale", "MiTo"
    ],
    "Land Rover": [
        "Defender", "Discovery", "Discovery Sport",
        "Range Rover", "Range Rover Sport", "Evoque"
    ],
}
# ==========================================================================
# ARAÇ MOTOR / PAKET / DONANIM VERİLERİ
# ==========================================================================

VEHICLE_SPECS: Dict[str, Dict[str, Dict[str, List[str]]]] = {

    "Volkswagen": {
        "Golf": {
            "2016": [
                "1.2 TSI Trendline",
                "1.2 TSI Comfortline",
                "1.4 TSI Comfortline",
                "1.6 TDI Trendline",
                "1.6 TDI Comfortline",
                "1.6 TDI Highline",
                "2.0 TDI GTD",
            ],
            "2017": [
                "1.0 TSI Trendline",
                "1.0 TSI Comfortline",
                "1.4 TSI Comfortline",
                "1.6 TDI Trendline",
                "1.6 TDI Comfortline",
                "1.6 TDI Highline",
                "2.0 TDI GTD",
            ],
            "2018": [
                "1.0 TSI Trendline",
                "1.0 TSI Comfortline",
                "1.5 TSI Comfortline",
                "1.6 TDI Comfortline",
                "1.6 TDI Highline",
                "2.0 TDI GTD",
            ],
        },

        "Passat": {
            "2016": [
                "1.4 TSI Trendline",
                "1.4 TSI Comfortline",
                "1.6 TDI Trendline",
                "1.6 TDI Comfortline",
                "2.0 TDI Comfortline",
                "2.0 TDI Highline",
            ],
            "2017": [
                "1.4 TSI Comfortline",
                "1.6 TDI Trendline",
                "1.6 TDI Comfortline",
                "2.0 TDI Comfortline",
                "2.0 TDI Highline",
            ],
            "2018": [
                "1.4 TSI Comfortline",
                "1.5 TSI Comfortline",
                "1.6 TDI Comfortline",
                "2.0 TDI Highline",
            ],
        },
    },

    "Renault": {
        "Clio": {
            "2019": [
                "0.9 TCe Joy",
                "0.9 TCe Touch",
                "0.9 TCe Icon",
                "1.5 dCi Joy",
                "1.5 dCi Touch",
                "1.5 dCi Icon",
            ],
            "2020": [
                "1.0 SCe Joy",
                "1.0 TCe Joy",
                "1.0 TCe Touch",
                "1.0 TCe Icon",
                "1.5 Blue dCi Joy",
                "1.5 Blue dCi Touch",
            ],
        },

        "Megane": {
            "2019": [
                "1.3 TCe Joy",
                "1.3 TCe Touch",
                "1.3 TCe Icon",
                "1.5 dCi Joy",
                "1.5 dCi Touch",
                "1.5 dCi Icon",
            ],
            "2020": [
                "1.3 TCe Joy",
                "1.3 TCe Touch",
                "1.3 TCe Icon",
                "1.5 Blue dCi Joy",
                "1.5 Blue dCi Touch",
            ],
        },
    },

    "Fiat": {
        "Egea": {
            "2016": [
                "1.4 Fire Easy",
                "1.4 Fire Urban",
                "1.3 Multijet Easy",
                "1.3 Multijet Urban",
                "1.6 Multijet Lounge",
            ],
            "2017": [
                "1.4 Fire Easy",
                "1.4 Fire Urban",
                "1.3 Multijet Easy",
                "1.3 Multijet Urban",
                "1.6 Multijet Lounge",
            ],
            "2018": [
                "1.4 Fire Easy",
                "1.4 Fire Urban",
                "1.3 Multijet Easy",
                "1.6 Multijet Urban",
                "1.6 Multijet Lounge",
            ],
            "2019": [
                "1.4 Fire Easy",
                "1.4 Fire Urban",
                "1.3 Multijet Urban",
                "1.6 Multijet Lounge",
            ],
            "2020": [
                "1.4 Fire Easy",
                "1.4 Fire Urban",
                "1.3 Multijet Urban",
                "1.6 Multijet Lounge",
            ],
        },
    },

    "BMW": {
        "3 Serisi": {
            "2018": [
                "318i Sport Line",
                "318i Luxury Line",
                "320i Sport Line",
                "320i Luxury Line",
                "320d Sport Line",
                "320d Luxury Line",
            ],
            "2019": [
                "318i Sport Line",
                "320i Sport Line",
                "320i Luxury Line",
                "320d Sport Line",
                "320d Luxury Line",
                "330i M Sport",
            ],
        },
    },

    "Mercedes-Benz": {
        "C-Serisi": {
            "2018": [
                "C180 Style",
                "C180 Exclusive",
                "C200 AMG",
                "C200d AMG",
                "C220d AMG",
            ],
            "2019": [
                "C180 AMG",
                "C200 AMG",
                "C200d AMG",
                "C220d AMG",
            ],
        },
    },

    "Toyota": {
        "Corolla": {
            "2018": [
                "1.33 Life",
                "1.6 Life",
                "1.6 Touch",
                "1.6 Advance",
                "1.6 Premium",
            ],
            "2019": [
                "1.6 Vision",
                "1.6 Dream",
                "1.6 Flame",
                "1.6 Passion",
                "1.8 Hybrid Dream",
                "1.8 Hybrid Flame",
            ],
        },
    },
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

app = FastAPI(title="Parça İste — Tersine İlan Pazarı", version="4.0.0")


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



def listing_from_db(row):
    if not row: return None
    d=dict(row)
    d["ai_filled"] = bool(d.get("ai_filled"))
    d["offers"] = []
    return d

def load_listing(listing_id):
    con=db(); row=execute(con,"SELECT * FROM listings WHERE id=?",(listing_id,)).fetchone()
    if not row:
        con.close(); return None
    item=listing_from_db(row)
    offers=execute(con,"SELECT * FROM offers WHERE listing_id=? ORDER BY price ASC",(listing_id,)).fetchall()
    item["offers"]=[{**dict(o),"seller_phone_display":format_phone(dict(o)["seller_phone"])} for o in offers]
    con.close(); return item

@app.get("/api/listings")
def list_listings(is_premium: bool=False, province: Optional[str]=None, brand: Optional[str]=None, category: Optional[str]=None, status: str="active"):
    con=db(); sql="SELECT * FROM listings WHERE 1=1"; params=[]
    if status: sql += " AND status=?"; params.append(status)
    if province: sql += " AND province=?"; params.append(province)
    if brand: sql += " AND brand=?"; params.append(brand)
    if category: sql += " AND part_category=?"; params.append(category)
    sql += " ORDER BY created_at DESC"
    rows=execute(con,sql,params).fetchall(); con.close()
    return [_public_listing(load_listing(dict(r)["id"]),is_premium) for r in rows]

@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: str, is_premium: bool=False):
    listing=load_listing(listing_id)
    if not listing: raise HTTPException(404,"İlan bulunamadı.")
    out=_public_listing(listing,is_premium); offers=sorted(listing.get("offers",[]),key=lambda o:o["price"])
    out["offers"]=offers if is_premium else [{**o,"seller_phone":mask_phone(o["seller_phone"])} for o in offers]
    return out

@app.post("/api/listings", status_code=201)
def create_listing(payload: ListingCreateRequest, request: Request):
    try: phone=normalize_phone(payload.phone)
    except ValueError as exc: raise HTTPException(400,str(exc))
    if phone not in VERIFIED_PHONES: raise HTTPException(403,"Telefon numarası doğrulanmamış. Önce SMS kodunu doğrulayın.")
    if payload.model not in CAR_DATA.get(payload.brand,[]): raise HTTPException(400,"Model, seçilen markaya ait değil.")
    owner=require_user(request)
    listing_id=new_id(); created=now_iso()
    con=db(); execute(con,"INSERT INTO listings(id,owner_id,brand,model,year,engine_package,color,part_category,description,province,province_id,district,phone,ai_filled,image_filename,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(listing_id,owner["id"],payload.brand,payload.model,payload.year,(payload.engine_package or "").strip(),payload.color,payload.part_category,payload.description.strip(),payload.province,payload.province_id,payload.district,phone,int(payload.ai_filled),payload.image_filename,"active",created)); con.commit(); con.close()
    return _public_listing(load_listing(listing_id),True)|{"phone_display":format_phone(phone)}

@app.post("/api/listings/{listing_id}/offers", status_code=201)
def create_offer(listing_id: str,payload: OfferCreateRequest,request: Request):
    listing=load_listing(listing_id)
    if not listing: raise HTTPException(404,"İlan bulunamadı.")
    if listing["status"]!="active": raise HTTPException(400,"Bu ilan artık aktif değil.")
    seller_user=require_user(request)
    if seller_user["role"]!="seller": raise HTTPException(403,"Teklif verebilmek için Satıcı/Esnaf hesabı kullanmalısın.")
    try: seller_phone=normalize_phone(payload.seller_phone)
    except ValueError as exc: raise HTTPException(400,str(exc))
    offer={"id":new_id(),"listing_id":listing_id,"seller_user_id":seller_user["id"],"seller_name":payload.seller_name.strip(),"seller_phone":seller_phone,"seller_phone_display":format_phone(seller_phone),"price":round(payload.price,2),"message":(payload.message or "").strip(),"created_at":now_iso()}
    con=db(); execute(con,"INSERT INTO offers(id,listing_id,seller_user_id,seller_name,seller_phone,price,message,created_at) VALUES(?,?,?,?,?,?,?,?)",(offer["id"],listing_id,seller_user["id"],offer["seller_name"],seller_phone,offer["price"],offer["message"],offer["created_at"]))
    owner_id=listing.get("owner_id")
    if owner_id: execute(con,"INSERT INTO notifications(id,user_id,type,title,body,link,created_at) VALUES(?,?,?,?,?,?,?)",(uuid.uuid4().hex,owner_id,"offer","Yeni teklif",f"{seller_user['name']} {offer['price']:,.0f}₺ teklif verdi.".replace(",","."),f"/listing/{listing_id}",now_iso()))
    con.commit(); con.close(); return offer

@app.patch("/api/listings/{listing_id}/close")
def close_listing(listing_id:str,payload:OtpSendRequest,request:Request):
    listing=load_listing(listing_id)
    if not listing: raise HTTPException(404,"İlan bulunamadı.")
    user=require_user(request)
    if listing.get("owner_id")!=user["id"]: raise HTTPException(403,"Bu ilanı kapatma yetkiniz yok.")
    con=db(); execute(con,"UPDATE listings SET status=? WHERE id=?",("closed",listing_id)); con.commit(); con.close(); return {"success":True}

@app.get("/api/my-listings")
def my_listings(request:Request,phone:str=""):
    user=require_user(request); con=db(); rows=execute(con,"SELECT id FROM listings WHERE owner_id=? ORDER BY created_at DESC",(user["id"],)).fetchall(); con.close()
    result=[]
    for r in rows:
        x=load_listing(dict(r)["id"]); x["phone_display"]=format_phone(x["phone"]); x["offer_count"]=len(x["offers"]); result.append(x)
    return result

# ==========================================================================
# 7) DEMO / CANLI SIMULASYON VERISI
# ==========================================================================
DEMO_ACTIVITY = [
    {"name":"Mert K.", "city":"Bursa", "action":"17 inç jant talebi oluşturdu", "icon":"fa-bullhorn"},
    {"name":"OtoMax Garage", "city":"İstanbul", "action":"Volkswagen Golf için teklif gönderdi", "icon":"fa-hand-holding-dollar"},
    {"name":"Ayşe D.", "city":"Ankara", "action":"LED far talebi yayınladı", "icon":"fa-wand-magic-sparkles"},
    {"name":"Pro Modifiye", "city":"İzmir", "action":"Body kit talebine teklif verdi", "icon":"fa-screwdriver-wrench"},
    {"name":"Can T.", "city":"Kocaeli", "action":"Ses sistemi talebi oluşturdu", "icon":"fa-volume-high"},
]

@app.get("/api/demo-feed")
def demo_feed() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    items = []
    for i, item in enumerate(DEMO_ACTIVITY):
        row = dict(item)
        row["seconds_ago"] = (i + 1) * 17
        row["time"] = (now.timestamp() - row["seconds_ago"])
        items.append(row)
    return {"items": items, "online": random.randint(38, 67), "today_listings": random.randint(84, 126), "today_offers": random.randint(173, 248)}

# ============================================================================
# 8) KALICI HESAP + MARKETPLACE VERİ KATMANI
# ============================================================================
# Üretim mantığı: kullanıcı oturumu HttpOnly cookie ile tutulur. SQLite,
# DATABASE_PATH ile değiştirilebilir. Render'da kalıcılık için bu yolu bir
# Persistent Disk'e bağlamak önerilir; DATABASE_URL varsa ileride Postgres'e
# geçirilmesi kolay olacak şekilde tablolar ayrıştırılmıştır.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "parca_iste.db"))
SESSION_COOKIE = "parca_iste_session"
SESSION_TTL_DAYS = 30

# Production: Render PostgreSQL desteklenir. DATABASE_URL yoksa yerel geliştirmede SQLite kullanılır.
# Böylece aynı kod hem lokal hem Render üzerinde çalışır.
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))


def db():
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        url = DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        con = psycopg.connect(url, row_factory=dict_row)
        return con
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def qmark(sql: str) -> str:
    # PostgreSQL psycopg %s, SQLite ?
    return sql.replace("?", "%s") if USE_POSTGRES else sql


def execute(con, sql, params=()):
    return con.execute(qmark(sql), params)


def init_db():
    con = db()
    if USE_POSTGRES:
        ddl = """
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'buyer',
          phone TEXT DEFAULT '', city TEXT DEFAULT '', bio TEXT DEFAULT '',
          avatar TEXT DEFAULT '', verified INTEGER DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS favorites (user_id TEXT NOT NULL, listing_id TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(user_id,listing_id));
        CREATE TABLE IF NOT EXISTS saved_searches (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,name TEXT NOT NULL,query TEXT DEFAULT '',province TEXT DEFAULT '',brand TEXT DEFAULT '',category TEXT DEFAULT '',notify INTEGER DEFAULT 1,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notifications (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,type TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,link TEXT DEFAULT '',read INTEGER DEFAULT 0,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY,listing_id TEXT NOT NULL,sender_id TEXT NOT NULL,receiver_id TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,read INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY,business_name TEXT DEFAULT '',city TEXT DEFAULT '',phone TEXT DEFAULT '',description TEXT DEFAULT '',rating REAL DEFAULT 0,review_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS listings (id TEXT PRIMARY KEY,owner_id TEXT,brand TEXT NOT NULL,model TEXT NOT NULL,year INTEGER,engine_package TEXT DEFAULT '',color TEXT,part_category TEXT,description TEXT,province TEXT,province_id INTEGER,district TEXT,phone TEXT,ai_filled INTEGER DEFAULT 0,image_filename TEXT,status TEXT DEFAULT 'active',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS offers (id TEXT PRIMARY KEY,listing_id TEXT NOT NULL,seller_user_id TEXT NOT NULL,seller_name TEXT,seller_phone TEXT,price DOUBLE PRECISION,message TEXT DEFAULT '',created_at TEXT NOT NULL);
        """
        for stmt in ddl.split(';'):
            if stmt.strip(): execute(con, stmt)
    else:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'buyer',phone TEXT DEFAULT '',city TEXT DEFAULT '',bio TEXT DEFAULT '',avatar TEXT DEFAULT '',verified INTEGER DEFAULT 0,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS favorites (user_id TEXT NOT NULL,listing_id TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(user_id,listing_id));
        CREATE TABLE IF NOT EXISTS saved_searches (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,name TEXT NOT NULL,query TEXT DEFAULT '',province TEXT DEFAULT '',brand TEXT DEFAULT '',category TEXT DEFAULT '',notify INTEGER DEFAULT 1,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notifications (id TEXT PRIMARY KEY,user_id TEXT NOT NULL,type TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,link TEXT DEFAULT '',read INTEGER DEFAULT 0,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY,listing_id TEXT NOT NULL,sender_id TEXT NOT NULL,receiver_id TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,read INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY,business_name TEXT DEFAULT '',city TEXT DEFAULT '',phone TEXT DEFAULT '',description TEXT DEFAULT '',rating REAL DEFAULT 0,review_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS listings (id TEXT PRIMARY KEY,owner_id TEXT,brand TEXT NOT NULL,model TEXT NOT NULL,year INTEGER,engine_package TEXT DEFAULT '',color TEXT,part_category TEXT,description TEXT,province TEXT,province_id INTEGER,district TEXT,phone TEXT,ai_filled INTEGER DEFAULT 0,image_filename TEXT,status TEXT DEFAULT 'active',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS offers (id TEXT PRIMARY KEY,listing_id TEXT NOT NULL,seller_user_id TEXT NOT NULL,seller_name TEXT,seller_phone TEXT,price REAL,message TEXT DEFAULT '',created_at TEXT NOT NULL);
        """)
    con.commit(); con.close()

init_db()

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240000)
    return "pbkdf2$240000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()

def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2$"):
        try:
            _, rounds, salt_b64, hash_b64 = stored.split("$", 3)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False
    # v5 eski hesaplarla geriye dönük uyumluluk
    return hmac.compare_digest(stored, hashlib.sha256(password.encode("utf-8")).hexdigest())

def safe_user(row):
    if not row: return None
    return {"id":row["id"],"name":row["name"],"email":row["email"],"role":row["role"],
            "phone":row["phone"],"city":row["city"],"bio":row["bio"],"avatar":row["avatar"],
            "verified":bool(row["verified"]),"created_at":row["created_at"]}

def create_session(user_id: str):
    token=secrets.token_urlsafe(48)
    exp=(datetime.now(timezone.utc)).timestamp()+SESSION_TTL_DAYS*86400
    expires=datetime.fromtimestamp(exp,tz=timezone.utc).isoformat()
    con=db(); execute(con, "INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",(token,user_id,expires)); con.commit(); con.close()
    return token, expires

def current_user_from_token(token: Optional[str]):
    if not token: return None
    con=db(); row=execute(con, "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires_at>?",(token,datetime.now(timezone.utc).isoformat())).fetchone(); con.close()
    return safe_user(row)

def current_user(request: Request):
    return current_user_from_token(request.cookies.get(SESSION_COOKIE))

def require_user(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(status_code=401, detail="Bu işlem için giriş yapmalısın.")
    return user

class AuthBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str
    password: str = Field(min_length=8, max_length=128)
    role: str = "buyer"
class LoginBody(BaseModel):
    email: str
    password: str
class ProfileBody(BaseModel):
    name: str = Field(min_length=2,max_length=80)
    phone: str = ""
    city: str = ""
    bio: str = Field(default="",max_length=500)
    business_name: str = Field(default="",max_length=120)
class SaveSearchBody(BaseModel):
    name: str = Field(min_length=2,max_length=80)
    query: str = ""; province: str = ""; brand: str = ""; category: str = ""; notify: bool = True
class MessageBody(BaseModel):
    body: str = Field(min_length=1,max_length=1000)

@app.post("/api/auth/register")
def register_user(body: AuthBody, request: Request):
    email=body.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$",email): raise HTTPException(400,"Geçerli bir e-posta adresi gir.")
    role=body.role if body.role in ("buyer","seller") else "buyer"
    con=db()
    if execute(con, "SELECT 1 FROM users WHERE email=?",(email,)).fetchone(): con.close(); raise HTTPException(409,"Bu e-posta ile zaten bir hesap var.")
    uid=uuid.uuid4().hex
    now=now_iso()
    execute(con, "INSERT INTO users(id,name,email,password_hash,role,created_at) VALUES(?,?,?,?,?,?)",(uid,body.name.strip(),email,hash_password(body.password),role,now))
    execute(con, "INSERT INTO profiles(user_id,city) VALUES(?,?)",(uid,"")); con.commit(); con.close()
    token,exp=create_session(uid)
    user=current_user_from_token(token)
    resp=JSONResponse({"success":True,"user":user})
    resp.set_cookie(SESSION_COOKIE,token,max_age=SESSION_TTL_DAYS*86400,httponly=True,samesite="lax",secure=(os.environ.get("COOKIE_SECURE", "").strip() == "1" if os.environ.get("COOKIE_SECURE", "").strip() else request.url.scheme == "https"),path="/")
    return resp

@app.post("/api/auth/login")
def login_user(body: LoginBody, request: Request):
    email=body.email.strip().lower(); con=db(); row=execute(con, "SELECT * FROM users WHERE email=?",(email,)).fetchone(); con.close()
    if not row or not verify_password(body.password, row["password_hash"]): raise HTTPException(401,"E-posta veya şifre hatalı.")
    token,exp=create_session(row["id"]); user=safe_user(row)
    resp=JSONResponse({"success":True,"user":user}); resp.set_cookie(SESSION_COOKIE,token,max_age=SESSION_TTL_DAYS*86400,httponly=True,samesite="lax",secure=(os.environ.get("COOKIE_SECURE", "").strip() == "1" if os.environ.get("COOKIE_SECURE", "").strip() else request.url.scheme == "https"),path="/"); return resp

@app.post("/api/auth/logout")
def logout_user(request: Request):
    token=request.cookies.get(SESSION_COOKIE); con=db()
    if token: execute(con, "DELETE FROM sessions WHERE token=?",(token,)); con.commit()
    con.close(); resp=JSONResponse({"success":True}); resp.delete_cookie(SESSION_COOKIE,path="/"); return resp

@app.get("/api/auth/me")
def auth_me(request: Request):
    user=current_user(request)
    if not user: raise HTTPException(401,"Oturum bulunamadı.")
    return user

@app.get("/api/account/summary")
def account_summary(request: Request):
    user=require_user(request); con=db(); uid=user["id"]
    fav=execute(con, "SELECT COUNT(*) c FROM favorites WHERE user_id=?",(uid,)).fetchone()["c"]
    saved=execute(con, "SELECT COUNT(*) c FROM saved_searches WHERE user_id=?",(uid,)).fetchone()["c"]
    unread=execute(con, "SELECT COUNT(*) c FROM notifications WHERE user_id=? AND read=0",(uid,)).fetchone()["c"]
    msgs=execute(con, "SELECT COUNT(*) c FROM messages WHERE receiver_id=? AND read=0",(uid,)).fetchone()["c"]
    con.close(); return {"favorites":fav,"saved_searches":saved,"unread_notifications":unread,"unread_messages":msgs}

@app.put("/api/account/profile")
def update_profile(body: ProfileBody, request: Request):
    user=require_user(request); phone=""
    if body.phone:
        try: phone=normalize_phone(body.phone)
        except ValueError as e: raise HTTPException(400,str(e))
    con=db(); execute(con, "UPDATE users SET name=?,phone=?,city=?,bio=? WHERE id=?",(body.name.strip(),phone,body.city.strip(),body.bio.strip(),user["id"]))
    execute(con, "UPDATE profiles SET business_name=?,city=?,phone=?,description=? WHERE user_id=?",(body.business_name.strip(),body.city.strip(),phone,body.bio.strip(),user["id"]))
    con.commit(); row=execute(con, "SELECT * FROM users WHERE id=?",(user["id"],)).fetchone(); con.close(); return safe_user(row)

@app.post("/api/favorites/{listing_id}")
def add_favorite(listing_id:str,request: Request):
    user=require_user(request)
    if not load_listing(listing_id): raise HTTPException(404,"İlan bulunamadı.")
    con=db(); exists=execute(con,"SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?",(user["id"],listing_id)).fetchone();
    if not exists: execute(con,"INSERT INTO favorites(user_id,listing_id,created_at) VALUES(?,?,?)",(user["id"],listing_id,now_iso())); con.commit(); con.close(); return {"success":True}
@app.delete("/api/favorites/{listing_id}")
def remove_favorite(listing_id:str,request: Request):
    user=require_user(request); con=db(); execute(con, "DELETE FROM favorites WHERE user_id=? AND listing_id=?",(user["id"],listing_id)); con.commit(); con.close(); return {"success":True}
@app.get("/api/favorites")
def favorites(request: Request):
    user=require_user(request); con=db(); rows=execute(con, "SELECT listing_id FROM favorites WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall(); con.close()
    return [_public_listing(load_listing(dict(x)["listing_id"]),False) for x in rows if load_listing(dict(x)["listing_id"])]

@app.post("/api/saved-searches")
def save_search(body:SaveSearchBody,request: Request):
    user=require_user(request); con=db(); sid=uuid.uuid4().hex; execute(con, "INSERT INTO saved_searches(id,user_id,name,query,province,brand,category,notify,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(sid,user["id"],body.name,body.query,body.province,body.brand,body.category,int(body.notify),now_iso())); con.commit(); con.close(); return {"id":sid,"success":True}
@app.get("/api/saved-searches")
def saved_searches(request: Request):
    user=require_user(request); con=db(); rows=execute(con, "SELECT * FROM saved_searches WHERE user_id=? ORDER BY created_at DESC",(user["id"],)).fetchall(); con.close(); return [dict(r) for r in rows]
@app.delete("/api/saved-searches/{sid}")
def delete_saved_search(sid:str,request: Request):
    user=require_user(request); con=db(); execute(con, "DELETE FROM saved_searches WHERE id=? AND user_id=?",(sid,user["id"])); con.commit(); con.close(); return {"success":True}

@app.get("/api/notifications")
def notifications(request: Request):
    user=require_user(request); con=db(); rows=execute(con, "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",(user["id"],)).fetchall(); con.close(); return [dict(r) for r in rows]
@app.post("/api/notifications/read")
def notifications_read(request: Request):
    user=require_user(request); con=db(); execute(con, "UPDATE notifications SET read=1 WHERE user_id=?",(user["id"],)); con.commit(); con.close(); return {"success":True}

@app.get("/api/messages")
def conversations(request: Request):
    user=require_user(request); con=db(); rows=execute(con, "SELECT * FROM messages WHERE sender_id=? OR receiver_id=? ORDER BY created_at DESC",(user["id"],user["id"])).fetchall(); con.close(); return [dict(r) for r in rows]
@app.get("/api/listings/{listing_id}/messages")
def listing_messages(listing_id:str,request: Request):
    user=require_user(request); con=db(); rows=execute(con, "SELECT * FROM messages WHERE listing_id=? AND (sender_id=? OR receiver_id=?) ORDER BY created_at",(listing_id,user["id"],user["id"])).fetchall(); con.close(); return [dict(r) for r in rows]
@app.post("/api/listings/{listing_id}/messages")
def send_message(listing_id:str,body:MessageBody,request: Request):
    user=require_user(request); listing=load_listing(listing_id)
    if not listing: raise HTTPException(404,"İlan bulunamadı.")
    con=db(); owner=execute(con, "SELECT id FROM users WHERE id=? LIMIT 1",(listing.get("owner_id"),)).fetchone()
    if not owner: con.close(); raise HTTPException(400,"İlan sahibinin hesabı bulunamadı.")
    receiver=owner["id"]
    if receiver==user["id"]: con.close(); raise HTTPException(400,"Kendi ilanına mesaj gönderemezsin.")
    mid=uuid.uuid4().hex; execute(con, "INSERT INTO messages(id,listing_id,sender_id,receiver_id,body,created_at) VALUES(?,?,?,?,?,?)",(mid,listing_id,user["id"],receiver,body.body.strip(),now_iso()))
    execute(con, "INSERT INTO notifications(id,user_id,type,title,body,link,created_at) VALUES(?,?,?,?,?,?,?)",(uuid.uuid4().hex,receiver,"message","Yeni mesaj",f"{user['name']} sana bir mesaj gönderdi.",f"/listing/{listing_id}",now_iso())); con.commit(); con.close(); return {"success":True,"id":mid}

# ==========================================================================
# 8) ANA SAYFA — GERÇEK İSTATİSTİKLER / SON TALEPLER
# ==========================================================================
@app.get("/api/home-stats")
def home_stats() -> Dict[str, Any]:
    con = db()
    users = execute(con, "SELECT COUNT(*) c FROM users").fetchone()["c"]
    sellers = execute(con, "SELECT COUNT(*) c FROM users WHERE role=?", ("seller",)).fetchone()["c"]
    listings = execute(con, "SELECT COUNT(*) c FROM listings WHERE status=?", ("active",)).fetchone()["c"]
    offers = execute(con, "SELECT COUNT(*) c FROM offers").fetchone()["c"]
    con.close()
    return {"users": users, "sellers": sellers, "active_listings": listings, "offers": offers}

@app.get("/api/recent-listings")
def recent_listings(limit: int = 6) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 12))
    con = db()
    rows = execute(con, "SELECT * FROM listings WHERE status=? ORDER BY created_at DESC LIMIT ?", ("active", limit)).fetchall()
    con.close()
    return [_public_listing(load_listing(dict(r)["id"]), False) for r in rows]

# ==========================================================================
# 8) FRONTEND — Tek parça HTML / Tailwind CSS / Vanilla JS
# ==========================================================================

@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Parça İste | Araç Parçası İçin Teklif Pazarı</title>
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
  .demo-glow{box-shadow:0 18px 60px rgba(27,29,33,.14)}
  .live-dot{width:8px;height:8px;border-radius:9999px;background:#1F8A5F;box-shadow:0 0 0 5px rgba(31,138,95,.12);animation:pulseDot 1.8s infinite}
  @keyframes pulseDot{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(.72);opacity:.6}}
  .ticker-item{animation:slideIn .35s ease both}
  @keyframes slideIn{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:translateY(0)}}
  .feature-card{transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease}
  .feature-card:hover{transform:translateY(-3px);box-shadow:0 14px 35px rgba(27,29,33,.08);border-color:rgba(242,167,27,.45)}
  .sim-cursor{display:inline-block;width:7px;height:1em;background:var(--accent);vertical-align:-2px;animation:blink .8s infinite}@keyframes blink{50%{opacity:0}}
  .mega-search{box-shadow:0 25px 80px rgba(27,29,33,.18),0 3px 0 rgba(242,167,27,.25)}
  .mega-search:focus-within{border-color:rgba(242,167,27,.8);transform:translateY(-2px)}
  .search-chip{transition:.18s ease}.search-chip:hover{transform:translateY(-1px);background:#1B1D21;color:#fff}
  .pulse-ring{animation:ring 2s infinite}@keyframes ring{0%{box-shadow:0 0 0 0 rgba(242,167,27,.35)}70%{box-shadow:0 0 0 12px rgba(242,167,27,0)}100%{box-shadow:0 0 0 0 rgba(242,167,27,0)}}
  .trust-card{transition:.2s ease}.trust-card:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(0,0,0,.06)}
  .sim-progress{height:3px;background:rgba(255,255,255,.12);overflow:hidden;border-radius:99px}.sim-progress>span{display:block;height:100%;width:0;background:var(--accent);transition:width .2s linear}

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
    <nav class="hidden lg:flex items-center gap-1">
      <button onclick="showView('home')" data-nav="home" class="nav-btn">Ana Sayfa</button>
      <button onclick="showView('buyer')" data-nav="buyer" class="nav-btn">İlan Ver</button>
      <button onclick="showView('seller')" data-nav="seller" class="nav-btn">Teklif Havuzu</button>
      <button onclick="showView('mylistings')" data-nav="mylistings" class="nav-btn">İlanlarım</button>
    </nav>
    <div id="auth-desktop" class="hidden sm:flex items-center gap-2 ml-auto lg:ml-2">
      <button onclick="openAuth('login')" class="px-3 py-2 rounded-lg text-sm font-semibold text-white/90 hover:bg-white/10"><i class="fa-solid fa-right-to-bracket mr-1"></i>Giriş Yap</button>
      <button onclick="openAuth('register')" class="px-4 py-2 rounded-lg bg-accent text-ink text-sm font-bold hover:bg-accentdark hover:text-white"><i class="fa-solid fa-user-plus mr-1"></i>Kayıt Ol</button>
    </div>
    <div id="user-desktop" class="hidden sm:flex items-center gap-2 ml-auto lg:ml-2">
      <button onclick="toggleAccountMenu()" class="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/10">
        <span id="header-avatar" class="w-8 h-8 rounded-full bg-accent text-ink flex items-center justify-center font-bold">P</span>
        <span id="header-user-name" class="max-w-[130px] truncate text-sm font-semibold">Hesabım</span><i class="fa-solid fa-chevron-down text-xs"></i>
      </button>
    </div>
    <button onclick="toggleMobileNav()" class="sm:hidden text-xl w-9 h-9 flex items-center justify-center" aria-label="Menü">
      <i class="fa-solid fa-bars"></i>
    </button>
  </div>
  <div id="mobile-nav" class="hidden sm:hidden flex flex-col gap-1 px-4 pb-3 border-t border-white/10 pt-2">
    <button onclick="showView('home')" data-nav="home" class="nav-btn text-left">Ana Sayfa</button>
    <button onclick="showView('buyer')" data-nav="buyer" class="nav-btn text-left">İlan Ver</button>
    <button onclick="showView('seller')" data-nav="seller" class="nav-btn text-left">Teklif Havuzu</button>
    <button onclick="showView('mylistings')" data-nav="mylistings" class="nav-btn text-left">İlanlarım</button>
    <div id="mobile-auth-buttons" class="grid grid-cols-2 gap-2 pt-2"><button onclick="openAuth('login')" class="py-2 rounded-lg bg-white/10 text-white text-sm font-semibold">Giriş Yap</button><button onclick="openAuth('register')" class="py-2 rounded-lg bg-accent text-ink text-sm font-bold">Kayıt Ol</button></div><div id="mobile-user" class="hidden pt-2"><button onclick="showAccountPanel()" class="w-full py-2 rounded-lg bg-white/10 text-white text-sm font-semibold">Hesabım</button></div>
  </div>
</header>

<div id="account-menu" class="hidden fixed top-20 right-4 z-50 w-80 bg-white rounded-2xl border border-black/10 shadow-2xl p-3">
  <div class="flex items-center gap-3 p-3 border-b border-black/10"><span id="menu-avatar" class="w-11 h-11 rounded-full bg-accent flex items-center justify-center font-bold">P</span><div class="min-w-0"><div id="menu-name" class="font-bold truncate">Hesabım</div><div id="menu-email" class="text-xs text-steel truncate"></div></div></div>
  <div class="grid grid-cols-2 gap-2 p-3"><button onclick="openAccountSection('listings')" class="p-3 rounded-xl bg-paper text-left text-sm"><i class="fa-solid fa-bullhorn"></i><br>İlanlarım</button><button onclick="openAccountSection('favorites')" class="p-3 rounded-xl bg-paper text-left text-sm"><i class="fa-solid fa-heart"></i><br>Favorilerim</button><button onclick="openAccountSection('saved')" class="p-3 rounded-xl bg-paper text-left text-sm"><i class="fa-solid fa-bookmark"></i><br>Kayıtlı Aramalar</button><button onclick="openAccountSection('messages')" class="p-3 rounded-xl bg-paper text-left text-sm"><i class="fa-solid fa-comments"></i><br>Mesajlar</button></div>
  <button onclick="openAccountSection('profile')" class="w-full text-left px-3 py-2 rounded-lg hover:bg-paper text-sm"><i class="fa-solid fa-user-gear mr-2"></i>Hesap ve Profil</button>
  <button onclick="logoutUser()" class="w-full text-left px-3 py-2 rounded-lg hover:bg-danger/10 text-danger text-sm"><i class="fa-solid fa-right-from-bracket mr-2"></i>Güvenli Çıkış</button>
</div>

<main>
<!-- ============================= ANA SAYFA ============================= -->
<section id="view-home">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 pt-8 sm:pt-12 pb-10">
    <div class="text-center hero-fade">
      <div class="inline-flex items-center gap-2 text-xs font-semibold text-accentdark bg-accent/15 px-3 py-1.5 rounded-full mb-4"><span class="live-dot"></span> CANLI PAZAR · ŞU ANDA AKIYOR</div>
      <h1 class="font-display font-bold text-4xl sm:text-6xl lg:text-7xl leading-[.98] tracking-tight">Aradığını yaz.<br><span class="text-accentdark">Teklifler sana gelsin.</span></h1>
      <p class="text-steel max-w-2xl mx-auto mt-5 text-base sm:text-lg">Parça İste, klasik ilan sitelerinin tersine çalışır: ihtiyacını yayınlarsın; aksesuarcılar ve modifiye ustaları sana fiyat verir.</p>
    </div>

    <div class="max-w-5xl mx-auto mt-8 hero-fade d2">
      <div class="mega-search bg-white rounded-[28px] border-2 border-ink/10 p-2 sm:p-3 transition-all">
        <div class="flex items-center gap-2 sm:gap-3">
          <div class="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-ink text-accent flex items-center justify-center shrink-0 pulse-ring"><i class="fa-solid fa-magnifying-glass text-xl sm:text-2xl"></i></div>
          <div class="min-w-0 flex-1 text-left">
            <div class="text-[10px] sm:text-xs font-bold text-accentdark uppercase tracking-widest">CANLI AKIŞ · PARÇA İSTE'Yİ DENE</div>
            <div id="live-story" class="font-display font-bold text-base sm:text-xl truncate">“2018 Golf için LED far arıyorum…”</div>
            <div class="sim-progress mt-2"><span id="story-progress"></span></div>
          </div>
          <button onclick="startLiveSimulation(true)" class="hidden sm:flex items-center gap-2 px-5 py-4 rounded-2xl bg-accent text-ink font-bold hover:bg-accentdark hover:text-white transition"><i class="fa-solid fa-play"></i> Canlı Akışı Oynat</button>
          <button onclick="startLiveSimulation(true)" class="sm:hidden w-12 h-12 rounded-2xl bg-accent text-ink font-bold"><i class="fa-solid fa-play"></i></button>
        </div>
        <div class="flex gap-2 overflow-x-auto pt-3 pb-1">
          <button onclick="runSearchDemo('Golf LED far')" class="search-chip shrink-0 text-xs border border-black/10 rounded-full px-3 py-2">Golf LED far</button>
          <button onclick="runSearchDemo('Clio body kit')" class="search-chip shrink-0 text-xs border border-black/10 rounded-full px-3 py-2">Clio body kit</button>
          <button onclick="runSearchDemo('Egea 17 jant')" class="search-chip shrink-0 text-xs border border-black/10 rounded-full px-3 py-2">Egea 17 jant</button>
          <button onclick="showView('seller')" class="search-chip shrink-0 text-xs border border-black/10 rounded-full px-3 py-2">Teklifleri gör</button>
        </div>
      </div>
      <div class="flex flex-wrap justify-center gap-4 mt-4 text-xs text-steel"><span><i class="fa-solid fa-keyboard mr-1"></i> Klavye sesiyle yazılır</span><span><i class="fa-solid fa-wand-magic-sparkles mr-1"></i> AI ile doldur</span><span><i class="fa-solid fa-bolt mr-1"></i> Teklifler sana gelsin</span><span><i class="fa-solid fa-shield-halved mr-1"></i> Doğrulanmış kullanıcı</span></div>
    </div>

    <div class="max-w-5xl mx-auto mt-8 grid lg:grid-cols-5 gap-5 items-stretch">
      <div class="lg:col-span-3 bg-ink text-white rounded-3xl p-5 sm:p-7 demo-glow overflow-hidden relative">
        <div class="absolute -right-20 -top-20 w-56 h-56 rounded-full bg-accent/20 blur-3xl"></div>
        <div class="relative">
          <div class="flex items-center justify-between mb-5"><div><div class="text-xs text-white/50">CANLI SİMÜLASYON</div><h2 class="font-display font-bold text-xl sm:text-2xl">Alıcı → Satıcı → Anlaşma</h2></div><span class="inline-flex items-center gap-2 text-xs bg-white/10 px-3 py-1.5 rounded-full"><span class="live-dot"></span> CANLI</span></div>
          <div id="simulation-stage" class="bg-black/20 border border-white/10 rounded-2xl p-4 min-h-[245px]">
            <div class="flex gap-3 items-start"><div class="w-9 h-9 rounded-xl bg-accent text-ink flex items-center justify-center"><i class="fa-solid fa-user"></i></div><div><div class="text-xs text-white/50">ALICI</div><div id="sim-text" class="font-mono text-sm sm:text-base leading-7">“2018 Golf 1.6 TDI için LED far arıyorum…”</div><div class="mt-3 flex gap-2 flex-wrap"><span class="text-[11px] bg-white/10 rounded-full px-2 py-1">Volkswagen Golf</span><span class="text-[11px] bg-white/10 rounded-full px-2 py-1">LED Far</span><span class="text-[11px] bg-white/10 rounded-full px-2 py-1">Bursa</span></div></div></div>
            <div id="sim-events" class="mt-5 space-y-2 text-xs"></div>
          </div>
          <div class="mt-4 flex gap-2"><button onclick="startLiveSimulation(true)" class="flex-1 py-3 rounded-xl bg-accent text-ink font-bold">Tekrar Oynat</button><button onclick="showView('buyer')" class="flex-1 py-3 rounded-xl bg-white/10 font-semibold">Gerçek İlan Oluştur</button></div>
        </div>
      </div>
      <div class="lg:col-span-2 space-y-3">
        <div class="bg-white border border-black/10 rounded-2xl p-5"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl bg-accent/15 text-accentdark flex items-center justify-center"><i class="fa-solid fa-bullhorn"></i></div><div><b>1 · İlanını oluştur</b><p class="text-xs text-steel mt-1">Araç + parça + konum + fotoğraf.</p></div></div></div>
        <div class="bg-white border border-black/10 rounded-2xl p-5"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl bg-success/10 text-success flex items-center justify-center"><i class="fa-solid fa-hand-holding-dollar"></i></div><div><b>2 · Ustalar teklif versin</b><p class="text-xs text-steel mt-1">Fiyat, mesaj ve işletme bilgisi gelir.</p></div></div></div>
        <div class="bg-white border border-black/10 rounded-2xl p-5"><div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl bg-ink/5 text-ink flex items-center justify-center"><i class="fa-solid fa-scale-balanced"></i></div><div><b>3 · Karşılaştır ve seç</b><p class="text-xs text-steel mt-1">Teklifleri gör, satıcıyla iletişime geç.</p></div></div></div>
        <div class="bg-accent rounded-2xl p-5"><div class="text-xs font-bold uppercase tracking-widest text-ink/60">Hemen başla</div><div class="font-display font-bold text-xl mt-1">İlk talebin ücretsiz.</div><button onclick="openAuth('register')" class="mt-3 w-full py-3 rounded-xl bg-ink text-white font-bold">Ücretsiz Kayıt Ol</button></div>
      </div>
    </div>

    <div class="grid grid-cols-3 gap-3 max-w-5xl mx-auto mt-6"><div class="bg-white border border-black/10 rounded-2xl p-4 text-center"><div class="font-display font-bold text-2xl" data-home-stat="active_listings">—</div><div class="text-xs text-steel">aktif talep</div></div><div class="bg-white border border-black/10 rounded-2xl p-4 text-center"><div class="font-display font-bold text-2xl" data-home-stat="offers">—</div><div class="text-xs text-steel">toplam teklif</div></div><div class="bg-white border border-black/10 rounded-2xl p-4 text-center"><div class="font-display font-bold text-2xl" data-home-stat="users">—</div><div class="text-xs text-steel">kayıtlı kullanıcı</div></div></div>
  </div>

  <div class="max-w-6xl mx-auto px-4 sm:px-6 pb-10">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3 mb-4">
      <div><p class="text-xs font-bold text-accentdark tracking-widest">GERÇEK TALEP AKIŞI</p><h2 class="font-display font-bold text-2xl mt-1">Yeni yayınlanan talepler</h2><p class="text-sm text-steel mt-1">Kullanıcılar ihtiyacını yayınlıyor, esnaflar teklif veriyor.</p></div>
      <button onclick="showView('seller')" class="text-sm font-semibold text-ink hover:text-accentdark">Tüm teklif havuzunu gör <i class="fa-solid fa-arrow-right ml-1"></i></button>
    </div>
    <div id="recent-listings" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div class="col-span-full bg-white border border-black/10 rounded-2xl p-8 text-center text-steel"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Canlı talepler yükleniyor…</div>
    </div>
  </div>
  </div>


  <div class="max-w-5xl mx-auto px-4 sm:px-6 pb-8">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div class="trust-card bg-white border border-black/10 rounded-2xl p-4"><i class="fa-solid fa-car-side text-accentdark"></i><div class="font-display font-bold mt-2">Araç Parçaları</div><div class="text-xs text-steel mt-1">Jant · far · body kit</div></div>
      <div class="trust-card bg-white border border-black/10 rounded-2xl p-4"><i class="fa-solid fa-store text-success"></i><div class="font-display font-bold mt-2">Esnaf Ağı</div><div class="text-xs text-steel mt-1">Yerel teklif verenler</div></div>
      <div class="trust-card bg-white border border-black/10 rounded-2xl p-4"><i class="fa-solid fa-comments text-ink"></i><div class="font-display font-bold mt-2">Teklif Karşılaştır</div><div class="text-xs text-steel mt-1">Fiyat + mesaj + işletme</div></div>
      <div class="trust-card bg-white border border-black/10 rounded-2xl p-4"><i class="fa-solid fa-heart text-danger"></i><div class="font-display font-bold mt-2">Favoriler</div><div class="text-xs text-steel mt-1">Takip etmek istediğin talepler</div></div>
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

  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-10">
    <div class="text-center mb-7">
      <p class="text-xs font-semibold text-accentdark tracking-widest">NEDEN PARÇA İSTE?</p>
      <h2 class="font-display font-bold text-2xl sm:text-3xl mt-1">Aramak yerine talep oluştur.</h2>
      <p class="text-sm text-steel mt-2">Uygulamanın nasıl çalıştığını birkaç saniyede keşfet.</p>
    </div>
    <div class="grid md:grid-cols-3 gap-4">
      <div class="feature-card bg-white border border-black/10 rounded-2xl p-5"><div class="w-11 h-11 rounded-xl bg-accent/15 text-accentdark flex items-center justify-center mb-4"><i class="fa-solid fa-bolt"></i></div><h3 class="font-display font-semibold text-lg">Dakikalar içinde talep</h3><p class="text-sm text-steel mt-2">5 adımlı akış, AI destekli görsel analizi ve telefon doğrulamasıyla profesyonel ilanını hızlıca hazırla.</p></div>
      <div class="feature-card bg-white border border-black/10 rounded-2xl p-5"><div class="w-11 h-11 rounded-xl bg-success/10 text-success flex items-center justify-center mb-4"><i class="fa-solid fa-chart-line"></i></div><h3 class="font-display font-semibold text-lg">Teklifler sana gelsin</h3><p class="text-sm text-steel mt-2">Satıcılar talebini görür, fiyat ve mesaj gönderir. Sen gelen teklifleri tek ekrandan karşılaştırırsın.</p></div>
      <div class="feature-card bg-white border border-black/10 rounded-2xl p-5"><div class="w-11 h-11 rounded-xl bg-ink/5 text-ink flex items-center justify-center mb-4"><i class="fa-solid fa-lock"></i></div><h3 class="font-display font-semibold text-lg">Gizlilik kontrollü</h3><p class="text-sm text-steel mt-2">Telefon bilgisi ücretsiz satıcı modunda maskeli kalır; Premium simülasyonunda iletişim özellikleri açılır.</p></div>
    </div>
    <div class="mt-6 bg-gradient-to-r from-ink to-[#30343a] text-white rounded-2xl p-6 sm:p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
      <div><span class="inline-flex text-[11px] font-semibold bg-accent text-ink px-2.5 py-1 rounded-full mb-2">ESNAF REKLAMI</span><h3 class="font-display font-bold text-xl">Daha fazla müşteriye ulaş.</h3><p class="text-sm text-white/65 mt-1 max-w-xl">Talep havuzuna gir, uygun araçları filtrele ve saniyeler içinde teklif gönder. Premium akışını canlı simülasyonla test et.</p></div>
      <button onclick="showView('seller')" class="shrink-0 px-5 py-3 rounded-lg bg-accent text-ink font-semibold hover:bg-accentdark hover:text-white">Esnaf Panelini Aç <i class="fa-solid fa-arrow-right ml-1"></i></button>
    </div>
  </div>
</section>

<!-- ============================= HESABIM ============================= -->
<section id="view-account" class="hidden">
 <div class="max-w-6xl mx-auto px-4 sm:px-6 py-8">
  <div class="flex flex-col md:flex-row gap-5">
   <aside class="md:w-64 bg-white rounded-2xl border border-black/10 p-3 h-fit"><div class="p-4 bg-ink text-white rounded-xl"><div id="account-avatar" class="w-12 h-12 rounded-full bg-accent text-ink flex items-center justify-center text-xl font-bold">P</div><div id="account-name" class="font-bold mt-3">Hesabım</div><div id="account-role" class="text-xs text-white/60 mt-1">Bireysel</div></div><div class="space-y-1 mt-3"><button onclick="openAccountSection('listings')" class="account-tab w-full text-left p-3 rounded-lg">İlanlarım</button><button onclick="openAccountSection('favorites')" class="account-tab w-full text-left p-3 rounded-lg">Favorilerim</button><button onclick="openAccountSection('saved')" class="account-tab w-full text-left p-3 rounded-lg">Kayıtlı Aramalar</button><button onclick="openAccountSection('messages')" class="account-tab w-full text-left p-3 rounded-lg">Mesajlar</button><button onclick="openAccountSection('notifications')" class="account-tab w-full text-left p-3 rounded-lg">Bildirimler</button><button onclick="openAccountSection('profile')" class="account-tab w-full text-left p-3 rounded-lg">Profil ve Güvenlik</button></div></aside>
   <div class="flex-1"><div class="bg-white rounded-2xl border border-black/10 p-5"><div class="flex items-center justify-between"><div><h1 id="account-section-title" class="font-display text-2xl font-bold">İlanlarım</h1><p class="text-sm text-steel">Tüm hesap işlemlerin tek yerde.</p></div><button onclick="showView('buyer')" class="px-4 py-2 rounded-xl bg-accent font-bold">+ İlan Ver</button></div><div id="account-content" class="mt-6"></div></div></div>
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

<div id="auth-modal" class="hidden fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm p-4 items-center justify-center">
  <div class="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden">
    <div class="p-6 border-b border-black/10 flex items-center justify-between"><div><div class="text-xs font-bold text-accentdark uppercase tracking-widest">PARÇA İSTE</div><h3 id="auth-title" class="font-display font-bold text-2xl mt-1">Giriş Yap</h3></div><button onclick="closeAuth()" class="w-9 h-9 rounded-full bg-paper"><i class="fa-solid fa-xmark"></i></button></div>
    <form id="auth-form" class="p-6 space-y-4" onsubmit="submitAuth(event)">
      <div id="auth-name-wrap" class="hidden"><label class="text-sm font-semibold">Ad Soyad</label><input id="auth-name" class="mt-1 w-full border border-black/15 rounded-xl px-4 py-3" placeholder="Adınız Soyadınız"></div>
      <div><label class="text-sm font-semibold">E-posta</label><input id="auth-email" type="email" required class="mt-1 w-full border border-black/15 rounded-xl px-4 py-3" placeholder="ornek@mail.com"></div>
      <div><label class="text-sm font-semibold">Şifre</label><input id="auth-password" type="password" minlength="8" required class="mt-1 w-full border border-black/15 rounded-xl px-4 py-3" placeholder="En az 6 karakter"></div>
      <div id="auth-role-wrap" class="hidden"><label class="text-sm font-semibold">Hesap tipi</label><select id="auth-role" class="mt-1 w-full border border-black/15 rounded-xl px-4 py-3"><option value="buyer">Alıcı / Bireysel</option><option value="seller">Esnaf / Satıcı</option></select></div>
      <button id="auth-submit" class="w-full py-3 rounded-xl bg-ink text-white font-bold">Giriş Yap</button>
      <p id="auth-switch" class="text-center text-sm text-steel">Hesabın yok mu? <button type="button" onclick="openAuth('register')" class="font-bold text-accentdark">Kayıt ol</button></p>
      <p id="auth-msg" class="text-sm text-center hidden"></p>
    </form>
  </div>
</div>
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
// ANA SAYFA CANLI DEMO
// ==========================================================================
async function loadDemoFeed() {
  try {
    const res = await fetch('/api/demo-feed');
    if (!res.ok) return;
    const data = await res.json();
    document.getElementById('demo-online').textContent = `${data.online} kişi çevrimiçi`;
    document.getElementById('demo-listings').textContent = data.today_listings;
    document.getElementById('demo-offers').textContent = data.today_offers;
    document.getElementById('demo-feed').innerHTML = data.items.slice(0, 4).map((x, i) => `
      <div class="ticker-item flex items-center gap-3 rounded-lg bg-paper px-3 py-2.5" style="animation-delay:${i * 70}ms">
        <div class="w-8 h-8 rounded-lg bg-white flex items-center justify-center text-accentdark"><i class="fa-solid ${escapeHtml(x.icon)}"></i></div>
        <div class="min-w-0 flex-1"><p class="text-xs font-semibold truncate">${escapeHtml(x.name)} · ${escapeHtml(x.city)}</p><p class="text-[11px] text-steel truncate">${escapeHtml(x.action)}</p></div>
        <span class="text-[10px] text-steel whitespace-nowrap">${x.seconds_ago} sn</span>
      </div>`).join('');
  } catch (e) {}
}

// ==========================================================================
// NAV / VIEW SWITCH
// ==========================================================================
function showView(name) {
  if (['buyer','seller','mylistings','account'].includes(name) && !currentUser) { openAuth('login'); return; }
  ['home', 'buyer', 'seller', 'mylistings', 'account'].forEach(v => {
    document.getElementById('view-' + v).classList.toggle('hidden', v !== name);
  });
  document.querySelectorAll('[data-nav]').forEach(b => {
    b.classList.toggle('nav-btn-active', b.dataset.nav === name);
  });
  document.getElementById('mobile-nav').classList.add('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (name === 'seller') refreshListings();
  if (name === 'account') { if (!currentUser) { openAuth('login'); return; } showAccountSection('listings'); }
}
function toggleMobileNav() {
  document.getElementById('mobile-nav').classList.toggle('hidden');
}

async function loadHomeData(){
  try{
    const [statsRes, recentRes] = await Promise.all([fetch('/api/home-stats'), fetch('/api/recent-listings?limit=6')]);
    const stats = await statsRes.json();
    const recent = await recentRes.json();
    document.querySelectorAll('[data-home-stat]').forEach(el=>{ const key=el.dataset.homeStat; if(key==='active_listings') el.textContent=Number(stats.active_listings||0).toLocaleString('tr-TR'); if(key==='offers') el.textContent=Number(stats.offers||0).toLocaleString('tr-TR'); if(key==='users') el.textContent=Number(stats.users||0).toLocaleString('tr-TR'); });
    const box=document.getElementById('recent-listings'); if(!box) return;
    if(!recent.length){ box.innerHTML='<div class="col-span-full bg-white border border-black/10 rounded-2xl p-8 text-center text-steel">Henüz aktif talep yok. İlk talebi sen oluştur.</div>'; return; }
    box.innerHTML=recent.map(x=>`<article class="bg-white border border-black/10 rounded-2xl p-5 hover:-translate-y-1 hover:shadow-xl transition-all">
      <div class="flex items-center justify-between gap-2"><span class="text-[11px] font-bold px-2 py-1 rounded-full bg-accent/15 text-accentdark">${escapeHtml(x.part_category)}</span><span class="text-[11px] text-steel">${timeAgo(x.created_at)}</span></div>
      <h3 class="font-display font-bold text-lg mt-3">${escapeHtml(x.brand)} ${escapeHtml(x.model)} <span class="text-steel font-normal text-sm">· ${x.year}</span></h3>
      <p class="text-xs text-steel mt-1"><i class="fa-solid fa-location-dot mr-1"></i>${escapeHtml(x.province)} / ${escapeHtml(x.district)}</p>
      <p class="text-sm text-steel mt-3">${escapeHtml(x.description)}</p>
      <div class="flex items-center justify-between mt-4 pt-3 border-t border-black/10"><span class="text-xs font-semibold"><i class="fa-solid fa-hand-holding-dollar text-success mr-1"></i>${x.offer_count||0} teklif</span><button onclick="showView('seller')" class="text-xs font-bold text-ink">Teklif ver <i class="fa-solid fa-arrow-right ml-1"></i></button></div>
    </article>`).join('');
  }catch(e){ console.warn('home data',e); }
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
    phone: currentUser?.phone || wizard.phone, brand: wizard.brand, model: wizard.model,
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
// ANA SAYFA CANLI SİMÜLASYONU + KLAVYE SESİ
// ==========================================================================
let simTimer = null;
let audioCtx = null;
const simScript = [
  {role:'buyer', text:'“2018 Volkswagen Golf için LED far arıyorum…”'},
  {role:'buyer', text:'Araç: Golf · 2018 · 1.6 TDI · Bursa'},
  {role:'buyer', text:'Parça: LED / Xenon far seti · Bütçe: tekliflere açık'},
  {role:'system', text:'İlan yayınlandı ✓ · Yakındaki ustalara bildiriliyor…'},
  {role:'seller', text:'Yılmaz Oto Aksesuar → 4.750₺ teklif verdi'},
  {role:'seller', text:'Bursa Modifiye Garage → 4.350₺ + montaj teklif etti'},
  {role:'buyer', text:'Teklifler karşılaştırılıyor… En uygun teklif seçildi ✓'},
  {role:'system', text:'İletişim açıldı · Alıcı ve satıcı artık görüşebilir.'}
];
function keySound(){
  try{
    audioCtx=audioCtx||new (window.AudioContext||window.webkitAudioContext)();
    const o=audioCtx.createOscillator(), g=audioCtx.createGain(); o.type='square'; o.frequency.value=90+Math.random()*35; g.gain.value=.018; o.connect(g);g.connect(audioCtx.destination);o.start();o.stop(audioCtx.currentTime+.025);
  }catch(e){}
}
function startLiveSimulation(manual=false){
  if(manual) try{keySound()}catch(e){}
  clearInterval(simTimer); let i=0; const textEl=document.getElementById('sim-text'), events=document.getElementById('sim-events'); if(!textEl||!events)return; events.innerHTML='';
  const run=()=>{ if(i>=simScript.length){ clearInterval(simTimer); const bar=document.getElementById('story-progress'); if(bar)bar.style.width='100%'; return; } const item=simScript[i++]; const bar=document.getElementById('story-progress'); if(bar)bar.style.width=((i/simScript.length)*100)+'%'; let pos=0; textEl.innerHTML='<span></span><i class="sim-cursor"></i>'; const span=textEl.querySelector('span'); const typer=setInterval(()=>{ if(pos<item.text.length){span.textContent+=item.text[pos++]; if(pos%2===0) keySound();}else{clearInterval(typer); const icon=item.role==='seller'?'fa-store':item.role==='system'?'fa-bolt':'fa-user'; const box=document.createElement('div'); box.className='ticker-item flex gap-2 items-center text-white/80 bg-white/5 rounded-lg px-3 py-2'; box.innerHTML=`<i class="fa-solid ${icon} text-accent w-4"></i><span>${item.text}</span>`; events.prepend(box); setTimeout(()=>{box.style.opacity='.75'},200); } },22); }; run(); simTimer=setInterval(run,2700);
}
const liveMessages=['“Golf için LED far arıyorum” → 3 teklif geldi','“Clio body kit” talebi yayınlandı → Bursa ustalarına gidiyor','“Egea jant seti” → 2. teklif 18.500₺','Bir esnaf yeni talep havuzuna katıldı','Bir alıcı gelen 4 teklif arasından seçim yaptı'];
let liveIndex=0;
function rotateLiveStory(){const el=document.getElementById('live-story'); if(!el)return; el.style.opacity=0; setTimeout(()=>{el.textContent=liveMessages[liveIndex++%liveMessages.length];el.style.opacity=1},180)}
let storyTimer=null;
function runSearchDemo(query){
  const el=document.getElementById('live-story'); if(!el)return;
  clearInterval(storyTimer); el.textContent=''; let i=0; const bar=document.getElementById('story-progress');
  const type=()=>{ if(i<query.length){el.textContent+=query[i++]; keySound(); if(bar)bar.style.width=(i/query.length*100)+'%'; } else { clearInterval(storyTimer); if(bar)bar.style.width='100%'; setTimeout(()=>{startLiveSimulation(true)},500); } };
  storyTimer=setInterval(type,55); type();
}


// ============================================================================
// KAYIT / GİRİŞ / HESABIM — gerçek oturum (HttpOnly cookie)
// ============================================================================
let authMode='login';
let currentUser=null;
function openAuth(mode){authMode=mode; const modal=document.getElementById('auth-modal'); modal.classList.remove('hidden');modal.classList.add('flex'); document.getElementById('auth-name-wrap').classList.toggle('hidden',mode!=='register');document.getElementById('auth-role-wrap').classList.toggle('hidden',mode!=='register');document.getElementById('auth-title').textContent=mode==='login'?'Giriş Yap':'Ücretsiz Hesap Oluştur';document.getElementById('auth-submit').textContent=mode==='login'?'Giriş Yap':'Hesap Oluştur';document.getElementById('auth-switch').innerHTML=mode==='login'?`Hesabın yok mu? <button type="button" onclick="openAuth('register')" class="font-bold text-accentdark">Kayıt ol</button>`:`Zaten hesabın var mı? <button type="button" onclick="openAuth('login')" class="font-bold text-accentdark">Giriş yap</button>`;document.getElementById('auth-msg').classList.add('hidden');}
function closeAuth(){const m=document.getElementById('auth-modal');m.classList.add('hidden');m.classList.remove('flex')}
async function submitAuth(e){e.preventDefault();const msg=document.getElementById('auth-msg'),btn=document.getElementById('auth-submit');msg.classList.add('hidden');btn.disabled=true;btn.textContent='İşleniyor…';try{let url=authMode==='register'?'/api/auth/register':'/api/auth/login';let body=authMode==='register'?{name:document.getElementById('auth-name').value,email:document.getElementById('auth-email').value,password:document.getElementById('auth-password').value,role:document.getElementById('auth-role').value}:{email:document.getElementById('auth-email').value,password:document.getElementById('auth-password').value};const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw new Error(data.detail||'İşlem başarısız');currentUser=data.user;closeAuth();applyLoggedInUI();showToast(authMode==='login'?`Hoş geldin ${currentUser.name}. Oturumun açık.`:`Hesabın oluşturuldu. Oturumun açık.`);showView('account');}catch(err){msg.textContent=err.message;msg.className='text-sm text-center text-danger';msg.classList.remove('hidden')}finally{btn.disabled=false;btn.textContent=authMode==='login'?'Giriş Yap':'Hesap Oluştur'}}
async function restoreSession(){try{const res=await fetch('/api/auth/me',{credentials:'same-origin'});if(res.ok){currentUser=await res.json();applyLoggedInUI()}else{currentUser=null;applyLoggedOutUI()}}catch(e){applyLoggedOutUI()}}
function applyLoggedInUI(){if(!currentUser)return;document.getElementById('auth-desktop')?.classList.add('hidden');document.getElementById('user-desktop')?.classList.remove('hidden');document.getElementById('mobile-auth-buttons')?.classList.add('hidden');document.getElementById('mobile-user')?.classList.remove('hidden');const initials=(currentUser.name||'P').trim().split(/\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase();['header-avatar','menu-avatar','account-avatar'].forEach(id=>{const e=document.getElementById(id);if(e)e.textContent=initials});['header-user-name','menu-name','account-name'].forEach(id=>{const e=document.getElementById(id);if(e)e.textContent=currentUser.name});const em=document.getElementById('menu-email');if(em)em.textContent=currentUser.email;const role=document.getElementById('account-role');if(role)role.textContent=currentUser.role==='seller'?'Esnaf / Satıcı':'Alıcı / Bireysel'}
function applyLoggedOutUI(){document.getElementById('auth-desktop')?.classList.remove('hidden');document.getElementById('user-desktop')?.classList.add('hidden');document.getElementById('mobile-auth-buttons')?.classList.remove('hidden');document.getElementById('mobile-user')?.classList.add('hidden')}
function toggleAccountMenu(){document.getElementById('account-menu').classList.toggle('hidden')}
function showAccountPanel(){showView('account');document.getElementById('mobile-nav').classList.add('hidden')}
async function logoutUser(){await fetch('/api/auth/logout',{method:'POST',credentials:'same-origin'});currentUser=null;applyLoggedOutUI();document.getElementById('account-menu').classList.add('hidden');showView('home');showToast('Güvenli çıkış yapıldı.')}
async function openAccountSection(section){document.getElementById('account-menu').classList.add('hidden');if(!currentUser){openAuth('login');return}showView('account');showAccountSection(section)}
async function showAccountSection(section){if(!currentUser)return;const titles={listings:'İlanlarım',favorites:'Favorilerim',saved:'Kayıtlı Aramalar',messages:'Mesajlar',notifications:'Bildirimler',profile:'Profil ve Güvenlik'};document.getElementById('account-section-title').textContent=titles[section]||'Hesabım';const box=document.getElementById('account-content');box.innerHTML='<div class="py-10 text-center text-steel"><i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor…</div>';try{if(section==='listings'){const r=await fetch('/api/my-listings');const d=await r.json();box.innerHTML=d.length?d.map(x=>`<div class="border border-black/10 rounded-xl p-4 mb-3"><div class="flex justify-between gap-3"><b>${escapeHtml(x.brand)} ${escapeHtml(x.model)} · ${x.year}</b><span class="text-xs px-2 py-1 rounded bg-success/10 text-success">${x.status==='active'?'Aktif':'Kapalı'}</span></div><p class="text-sm text-steel mt-1">${escapeHtml(x.part_category)} · ${escapeHtml(x.province)}/${escapeHtml(x.district)}</p><p class="text-sm mt-2">${escapeHtml(x.description)}</p><div class="mt-3 text-sm font-semibold text-accentdark">${x.offer_count} teklif</div></div>`).join(''):'<div class="py-10 text-center text-steel">Henüz ilan yok. <button onclick="showView(\'buyer\')" class="text-accentdark font-bold">İlk ilanını ver.</button></div>'}
else if(section==='favorites'){const r=await fetch('/api/favorites');const d=await r.json();box.innerHTML=d.length?d.map(x=>`<div class="border border-black/10 rounded-xl p-4 mb-3"><b>${escapeHtml(x.brand)} ${escapeHtml(x.model)} · ${x.year}</b><p class="text-sm text-steel">${escapeHtml(x.part_category)} · ${escapeHtml(x.province)}/${escapeHtml(x.district)}</p></div>`).join(''):'<div class="py-10 text-center text-steel">Henüz favorin yok.</div>'}
else if(section==='saved'){const r=await fetch('/api/saved-searches');const d=await r.json();box.innerHTML=`<button onclick="quickSaveSearch()" class="mb-4 px-4 py-2 rounded-xl bg-accent font-bold">+ Aramayı Kaydet</button>`+(d.length?d.map(x=>`<div class="border border-black/10 rounded-xl p-4 mb-3 flex justify-between"><div><b>${escapeHtml(x.name)}</b><p class="text-xs text-steel">${escapeHtml(x.query||'Tüm talepler')} ${x.notify?'· Bildirim açık':''}</p></div><button onclick="deleteSavedSearch('${x.id}')" class="text-danger">Sil</button></div>`).join(''):'<div class="py-6 text-steel">Kayıtlı arama yok.</div>')}
else if(section==='messages'){const r=await fetch('/api/messages');const d=await r.json();box.innerHTML=d.length?d.map(x=>`<div class="border border-black/10 rounded-xl p-4 mb-3"><div class="text-xs text-steel">${new Date(x.created_at).toLocaleString('tr-TR')}</div><p class="mt-1">${escapeHtml(x.body)}</p></div>`).join(''):'<div class="py-10 text-center text-steel">Henüz mesajın yok.</div>'}
else if(section==='notifications'){const r=await fetch('/api/notifications');const d=await r.json();box.innerHTML=d.length?d.map(x=>`<div class="border border-black/10 rounded-xl p-4 mb-3 ${x.read?'':'bg-accent/10'}"><b>${escapeHtml(x.title)}</b><p class="text-sm mt-1">${escapeHtml(x.body)}</p></div>`).join(''):'<div class="py-10 text-center text-steel">Yeni bildirim yok.</div>';fetch('/api/notifications/read',{method:'POST'})}
else if(section==='profile'){box.innerHTML=`<form onsubmit="saveProfile(event)" class="space-y-4"><div><label class="text-sm font-semibold">Ad Soyad</label><input id="profile-name" value="${escapeHtml(currentUser.name)}" class="mt-1 w-full border rounded-xl px-4 py-3"></div><div><label class="text-sm font-semibold">Telefon</label><input id="profile-phone" value="${escapeHtml(currentUser.phone||'')}" class="mt-1 w-full border rounded-xl px-4 py-3" placeholder="0532 111 22 33"></div><div><label class="text-sm font-semibold">Şehir</label><input id="profile-city" value="${escapeHtml(currentUser.city||'')}" class="mt-1 w-full border rounded-xl px-4 py-3"></div><div><label class="text-sm font-semibold">Hakkımda</label><textarea id="profile-bio" class="mt-1 w-full border rounded-xl px-4 py-3" rows="4">${escapeHtml(currentUser.bio||'')}</textarea></div><button class="px-5 py-3 rounded-xl bg-ink text-white font-bold">Bilgileri Kaydet</button></form>`}}
catch(e){box.innerHTML='<div class="text-danger py-8">Bilgiler yüklenemedi.</div>'}}
async function saveProfile(e){e.preventDefault();const r=await fetch('/api/account/profile',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:document.getElementById('profile-name').value,phone:document.getElementById('profile-phone').value,city:document.getElementById('profile-city').value,bio:document.getElementById('profile-bio').value})});const d=await r.json();if(!r.ok){showToast(d.detail||'Kaydedilemedi',true);return}currentUser=d;applyLoggedInUI();showToast('Profil güncellendi.')}
async function quickSaveSearch(){const name=prompt('Arama adı','Golf LED far');if(!name)return;await fetch('/api/saved-searches',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,query:name,notify:true})});showAccountSection('saved')}
async function deleteSavedSearch(id){await fetch('/api/saved-searches/'+id,{method:'DELETE'});showAccountSection('saved')}
// ==========================================================================
// INIT
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  boot();
  restoreSession();
  loadHomeData();
  loadDemoFeed();
  startLiveSimulation(false);
  rotateLiveStory();
  setInterval(loadDemoFeed, 12000);
  setInterval(loadHomeData, 30000);
  setInterval(rotateLiveStory, 3200);
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
