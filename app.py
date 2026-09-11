import os, re, uuid, hashlib, secrets, json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Boolean, DateTime, ForeignKey, Text, Float, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker
from jose import jwt, JWTError

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./parca_iste.db")
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET ortam değişkeni zorunludur.")
JWT_ALG = "HS256"
TOKEN_DAYS = 30
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(180), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="buyer")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    plan_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    brand: Mapped[str] = mapped_column(String(80)); model: Mapped[str] = mapped_column(String(120))
    body: Mapped[Optional[str]] = mapped_column(String(100)); year: Mapped[int] = mapped_column(Integer)
    fuel: Mapped[Optional[str]] = mapped_column(String(40)); engine: Mapped[Optional[str]] = mapped_column(String(80))
    power: Mapped[Optional[str]] = mapped_column(String(40)); transmission: Mapped[Optional[str]] = mapped_column(String(40))
    trim: Mapped[Optional[str]] = mapped_column(String(100)); drivetrain: Mapped[Optional[str]] = mapped_column(String(40))
    color: Mapped[Optional[str]] = mapped_column(String(40)); category: Mapped[str] = mapped_column(String(100))
    specs_json: Mapped[str] = mapped_column(Text, default="{}")
    description: Mapped[str] = mapped_column(Text)
    province: Mapped[str] = mapped_column(String(80)); district: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user: Mapped[User] = relationship()

class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    price: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    receiver_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    read: Mapped[bool] = mapped_column(Boolean, default=False)

class Otp(Base):
    __tablename__ = "otps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)

Base.metadata.create_all(engine)

app = FastAPI(title="Parça İste Pro", version="2.0.0")

CAR_DATA = {
 "Renault":["Clio","Megane","Symbol","Fluence","Talisman","Captur","Kadjar","Kangoo","Toros","9","12"],
 "Fiat":["Egea","Linea","Albea","Doblo","Punto","Fiorino","Panda","Tipo","Palio","Şahin"],
 "Volkswagen":["Golf","Passat","Polo","Jetta","Bora","Caddy","Tiguan","Transporter","Scirocco","Vento"],
 "Ford":["Focus","Fiesta","Mondeo","Connect","Courier","Kuga","Ranger","Transit","B-Max","Puma"],
 "Opel":["Astra","Corsa","Vectra","Insignia","Combo","Mokka","Meriva","Zafira","Grandland X"],
 "Toyota":["Corolla","Yaris","Auris","Hilux","C-HR","RAV4","Avensis","Camry"],
 "Hyundai":["i20","i10","Accent Era","Accent Blue","Elantra","Tucson","Bayon","Kona","ix35"],
 "Peugeot":["301","308","208","3008","2008","508","Partner","407"],
 "Citroën":["C-Elysée","C3","C4","Berlingo","C5","C2","C4 Cactus"],
 "Honda":["Civic","City","CR-V","Jazz","Accord"], "Nissan":["Micra","Qashqai","Juke","Almera","X-Trail"],
 "Chevrolet":["Aveo","Cruze","Lacetti","Captiva","Spark"], "Škoda":["Octavia","Fabia","Superb","Rapid","Yeti","Karoq"],
 "Seat":["Ibiza","Leon","Toledo","Córdoba","Altea"], "Mercedes-Benz":["C-Serisi","E-Serisi","A-Serisi","Vito","Sprinter","CLA","GLA"],
 "BMW":["3 Serisi","5 Serisi","1 Serisi","X1","X3","X5"], "Audi":["A3","A4","A6","Q3","Q5","A1"],
 "Dacia":["Duster","Sandero","Logan","Dokker","Lodgy"], "Kia":["Rio","Ceed","Sportage","Picanto","Cerato","Sorento"],
 "Suzuki":["Swift","Vitara","Baleno","S-Cross","Grand Vitara"]}
COLORS=["Beyaz","Siyah","Gri","Gümüş","Kırmızı","Mavi","Lacivert","Yeşil","Kahverengi","Bej","Sarı","Turuncu","Mor","Bordo","Füme"]
CATEGORIES=["Jant / Lastik","Motor / Mekanik","Fren Sistemi","Egzoz Sistemi","Body Kit / Spoiler / Difüzör","Tampon","Far / Stop","Ses Sistemi / Multimedya","Kaplama / Folyo","İç Mekan","Dış Mekan","Performans / Chip Tuning","Süspansiyon","Karbon / Krom","Alarm / Park Sensörü","Diğer"]
YEARS=list(range(datetime.now().year+1,1989,-1))
FUEL=["Benzin","Dizel","Hibrit","Plug-in Hibrit","Elektrik","LPG"]
TRANS=["Manuel","Otomatik","CVT","DSG / DCT","Yarı Otomatik"]
DRIVE=["Önden Çekiş","Arkadan İtiş","4x4 / AWD"]

class Auth(BaseModel):
    name: str = Field(min_length=2,max_length=100); phone: str; password: str = Field(min_length=8,max_length=128); email: Optional[str]=None; role: str="buyer"
class Login(BaseModel): phone: str; password: str
class OtpReq(BaseModel): phone: str
class OtpVerify(BaseModel): phone: str; code: str
class ListingIn(BaseModel):
    brand:str; model:str; body:Optional[str]=None; year:int; fuel:Optional[str]=None; engine:Optional[str]=None; power:Optional[str]=None; transmission:Optional[str]=None; trim:Optional[str]=None; drivetrain:Optional[str]=None; color:Optional[str]=None
    category:str; specs:dict={}; description:str=Field(min_length=10,max_length=3000); province:str; district:str
class OfferIn(BaseModel): price:float=Field(gt=0); message:str=""
class MsgIn(BaseModel): body:str=Field(min_length=1,max_length=3000)

# security helpers
def norm_phone(v:str)->str:
    d=re.sub(r"\D","",v or "")
    if d.startswith("90") and len(d)==12: d="0"+d[2:]
    if len(d)==10 and d.startswith("5"): d="0"+d
    if not re.fullmatch(r"05\d{9}",d): raise HTTPException(400,"Geçersiz telefon numarası.")
    return d

def hash_pw(p:str)->str:
    salt=secrets.token_bytes(16); return salt.hex()+":"+hashlib.pbkdf2_hmac("sha256",p.encode(),salt,210000).hex()
def check_pw(p:str,h:str)->bool:
    try:
        s,d=h.split(":",1); return secrets.compare_digest(hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(s),210000).hex(),d)
    except: return False

def token(user:User):
    return jwt.encode({"sub":str(user.id),"exp":datetime.now(timezone.utc)+timedelta(days=TOKEN_DAYS)},JWT_SECRET,algorithm=JWT_ALG)
def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
def current_user(authorization:Optional[str]=Header(None), db:Session=Depends(db)):
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(401,"Giriş yapmalısın.")
    try: uid=int(jwt.decode(authorization[7:],JWT_SECRET,algorithms=[JWT_ALG])["sub"])
    except (JWTError,ValueError,KeyError): raise HTTPException(401,"Oturum geçersiz veya süresi dolmuş.")
    u=db.get(User,uid)
    if not u: raise HTTPException(401,"Kullanıcı bulunamadı.")
    return u

def premium(u:User)->bool: return u.plan!="free" and u.plan_until and u.plan_until>datetime.now(timezone.utc)

def otp_hash(code): return hashlib.sha256(code.encode()).hexdigest()

def send_sms(phone, code):
    # Production: configure NETGSM_* or another provider. Never return OTP to client.
    if not os.getenv("NETGSM_USERCODE"):
        raise HTTPException(503,"SMS sağlayıcısı yapılandırılmamış. NETGSM ortam değişkenlerini tanımlayın.")
    import requests
    msg=f"Parça İste doğrulama kodunuz: {code}"
    r=requests.get("https://api.netgsm.com.tr/sms/send/get",params={"usercode":os.getenv("NETGSM_USERCODE"),"password":os.getenv("NETGSM_PASSWORD"),"gsmno":phone,"message":msg,"msgheader":os.getenv("NETGSM_MSGHEADER","PARCAISTE")},timeout=10)
    if r.status_code>=400: raise HTTPException(502,"SMS gönderilemedi.")

@app.get("/health")
def health(): return {"status":"ok","database":"persistent"}

@app.get("/api/meta")
def meta(): return {"brands":CAR_DATA,"colors":COLORS,"categories":CATEGORIES,"years":YEARS,"fuel":FUEL,"transmission":TRANS,"drivetrain":DRIVE,"plans":{"free":{"offers_per_month":5},"pro":{"offers_per_month":1000},"business":{"offers_per_month":10000}}}

@app.post("/api/auth/register")
def register(p:Auth,db:Session=Depends(db)):
    phone=norm_phone(p.phone)
    if db.scalar(select(User).where(User.phone==phone)): raise HTTPException(409,"Bu telefon zaten kayıtlı.")
    email=p.email.lower() if p.email else None
    if email and db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Bu e-posta zaten kayıtlı.")
    u=User(name=p.name,phone=phone,email=email,password_hash=hash_pw(p.password),role=p.role if p.role in ("buyer","seller") else "buyer")
    db.add(u); db.commit(); db.refresh(u)
    return {"access_token":token(u),"user":{"id":u.id,"name":u.name,"phone":u.phone,"role":u.role,"plan":u.plan}}

@app.post("/api/auth/login")
def login(p:Login,db:Session=Depends(db)):
    u=db.scalar(select(User).where(User.phone==norm_phone(p.phone)))
    if not u or not check_pw(p.password,u.password_hash): raise HTTPException(401,"Telefon veya şifre hatalı.")
    return {"access_token":token(u),"user":{"id":u.id,"name":u.name,"phone":u.phone,"role":u.role,"plan":u.plan}}

@app.get("/api/me")
def me(u:User=Depends(current_user)): return {"id":u.id,"name":u.name,"phone":u.phone,"email":u.email,"role":u.role,"plan":u.plan,"plan_until":u.plan_until}

@app.post("/api/otp/send")
def otp_send(p:OtpReq,db:Session=Depends(db)):
    phone=norm_phone(p.phone); code=f"{secrets.randbelow(1000000):06d}"
    db.add(Otp(phone=phone,code_hash=otp_hash(code),expires_at=datetime.now(timezone.utc)+timedelta(minutes=5))); db.commit()
    send_sms(phone,code); return {"success":True,"message":"Doğrulama kodu gönderildi."}

@app.post("/api/otp/verify")
def otp_verify(p:OtpVerify,db:Session=Depends(db)):
    phone=norm_phone(p.phone); row=db.scalar(select(Otp).where(Otp.phone==phone).order_by(Otp.id.desc()))
    if not row or row.expires_at<datetime.now(timezone.utc) or row.attempts>=5 or not secrets.compare_digest(row.code_hash,otp_hash(p.code)):
        if row: row.attempts+=1; db.commit()
        raise HTTPException(400,"Doğrulama kodu geçersiz veya süresi dolmuş.")
    u=db.scalar(select(User).where(User.phone==phone))
    if u: u.verified=True; db.commit()
    return {"verified":True}

@app.post("/api/listings")
def create_listing(p:ListingIn,u:User=Depends(current_user),db:Session=Depends(db)):
    if not u.verified: raise HTTPException(403,"İlan vermek için telefonunu doğrula.")
    if p.brand not in CAR_DATA or p.model not in CAR_DATA[p.brand]: raise HTTPException(400,"Geçersiz araç seçimi.")
    if p.category not in CATEGORIES: raise HTTPException(400,"Geçersiz kategori.")
    x=Listing(user_id=u.id,brand=p.brand,model=p.model,body=p.body,year=p.year,fuel=p.fuel,engine=p.engine,power=p.power,transmission=p.transmission,trim=p.trim,drivetrain=p.drivetrain,color=p.color,category=p.category,specs_json=json.dumps(p.specs,ensure_ascii=False),description=p.description,province=p.province,district=p.district)
    db.add(x); db.commit(); db.refresh(x); return {"id":x.id,"status":x.status}

def listing_json(x,db,viewer:Optional[User]):
    owner=db.get(User,x.user_id); return {"id":x.id,"brand":x.brand,"model":x.model,"body":x.body,"year":x.year,"fuel":x.fuel,"engine":x.engine,"power":x.power,"transmission":x.transmission,"trim":x.trim,"drivetrain":x.drivetrain,"color":x.color,"category":x.category,"specs":json.loads(x.specs_json or "{}"),"description":x.description,"province":x.province,"district":x.district,"status":x.status,"created_at":x.created_at,"owner_name":owner.name,"owner_phone":owner.phone if viewer and (viewer.id==x.user_id or premium(viewer)) else None}

@app.get("/api/listings")
def listings(province:Optional[str]=None,brand:Optional[str]=None,category:Optional[str]=None,db:Session=Depends(db),authorization:Optional[str]=Header(None)):
    viewer=None
    if authorization and authorization.startswith("Bearer "):
        try: viewer=current_user(authorization,db)
        except: viewer=None
    q=select(Listing).where(Listing.status=="active").order_by(Listing.created_at.desc())
    if province:q=q.where(Listing.province==province)
    if brand:q=q.where(Listing.brand==brand)
    if category:q=q.where(Listing.category==category)
    return [listing_json(x,db,viewer) for x in db.scalars(q).all()]

@app.get("/api/listings/{lid}")
def listing(lid:int,db:Session=Depends(db),u:User=Depends(current_user)): 
    x=db.get(Listing,lid)
    if not x: raise HTTPException(404,"İlan bulunamadı.")
    return listing_json(x,db,u)

@app.post("/api/listings/{lid}/offers")
def offer(lid:int,p:OfferIn,u:User=Depends(current_user),db:Session=Depends(db)):
    x=db.get(Listing,lid)
    if not x or x.status!="active": raise HTTPException(404,"Aktif ilan bulunamadı.")
    if u.id==x.user_id: raise HTTPException(400,"Kendi ilanına teklif veremezsin.")
    if u.role!="seller": raise HTTPException(403,"Teklif vermek için satıcı hesabı kullanmalısın.")
    month_start=datetime.now(timezone.utc)-timedelta(days=30)
    count=db.scalar(select(Offer).where(Offer.seller_id==u.id,Offer.created_at>=month_start).count()) if False else len(db.scalars(select(Offer).where(Offer.seller_id==u.id,Offer.created_at>=month_start)).all())
    limit=5 if not premium(u) else 1000
    if count>=limit: raise HTTPException(402,"Aylık teklif limitine ulaştın. Premium plana geç.")
    o=Offer(listing_id=lid,seller_id=u.id,price=p.price,message=p.message); db.add(o); db.commit(); db.refresh(o)
    return {"id":o.id,"success":True}

@app.get("/api/my-listings")
def my_listings(u:User=Depends(current_user),db:Session=Depends(db)):
    out=[]
    for x in db.scalars(select(Listing).where(Listing.user_id==u.id).order_by(Listing.created_at.desc())).all():
        offers=[]
        for o in db.scalars(select(Offer).where(Offer.listing_id==x.id).order_by(Offer.price.asc())).all():
            s=db.get(User,o.seller_id); offers.append({"id":o.id,"seller_name":s.name,"price":o.price,"message":o.message,"phone":s.phone if premium(u) else None})
        out.append({**listing_json(x,db,u),"offers":offers})
    return out

@app.post("/api/listings/{lid}/messages")
def send_message(lid:int,p:MsgIn,u:User=Depends(current_user),db:Session=Depends(db)):
    x=db.get(Listing,lid)
    if not x: raise HTTPException(404,"İlan bulunamadı.")
    if not premium(u): raise HTTPException(402,"Mesajlaşma Premium özelliğidir.")
    offers=db.scalars(select(Offer).where(Offer.listing_id==lid)).all()
    if u.id==x.user_id: raise HTTPException(400,"Alıcı mesaj için satıcı teklifinden başlamalı.")
    receiver=x.user_id
    m=Message(listing_id=lid,sender_id=u.id,receiver_id=receiver,body=p.body); db.add(m); db.commit(); db.refresh(m); return {"id":m.id}

@app.get("/api/listings/{lid}/messages")
def messages(lid:int,u:User=Depends(current_user),db:Session=Depends(db)):
    x=db.get(Listing,lid)
    if not x: raise HTTPException(404,"İlan bulunamadı.")
    if not premium(u): raise HTTPException(402,"Mesajlaşma Premium özelliğidir.")
    rows=db.scalars(select(Message).where(Message.listing_id==lid).order_by(Message.created_at.asc())).all()
    return [{"id":m.id,"sender_id":m.sender_id,"body":m.body,"created_at":m.created_at} for m in rows if m.sender_id==u.id or m.receiver_id==u.id]

@app.post("/api/uploads")
async def upload(file:UploadFile=File(...),u:User=Depends(current_user)):
    if not (file.content_type or "").startswith("image/"): raise HTTPException(400,"Sadece görsel yüklenebilir.")
    data=await file.read()
    if len(data)>10*1024*1024: raise HTTPException(400,"Maksimum 10MB.")
    ext=os.path.splitext(file.filename or "")[1].lower()[:8] or ".jpg"; name=f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR,name),"wb") as f:f.write(data)
    return {"filename":name}

HTML='''<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Parça İste</title><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-slate-50 text-slate-900"><header class="bg-slate-950 text-white"><div class="max-w-6xl mx-auto px-4 py-5 flex justify-between items-center"><b class="text-xl">Parça İste</b><nav class="flex gap-2"><button onclick="openAuth('login')" class="px-4 py-2 rounded-lg bg-white/10">Giriş</button><button onclick="openAuth('register')" class="px-4 py-2 rounded-lg bg-emerald-500">Kayıt Ol</button></nav></div></header><main class="max-w-6xl mx-auto px-4 py-10"><section class="grid md:grid-cols-2 gap-8 items-center"><div><p class="text-emerald-600 font-semibold">Tersine parça pazarı</p><h1 class="text-4xl md:text-6xl font-black mt-2">Parçayı sen ara, satıcılar teklif versin.</h1><p class="mt-5 text-slate-600 text-lg">Aracını ve ihtiyacını seç. Talebin uygun satıcılara ulaşsın.</p><div class="flex gap-3 mt-7"><button onclick="needAuth('buyer')" class="px-5 py-3 rounded-xl bg-slate-950 text-white">Parça Arıyorum</button><button onclick="needAuth('seller')" class="px-5 py-3 rounded-xl border">Satıcıyım</button></div></div><div class="bg-white rounded-3xl p-7 shadow-sm border"><h2 class="font-bold text-2xl">Neden?</h2><div class="grid gap-4 mt-5"><div>✓ Kalıcı kullanıcı hesabı</div><div>✓ Gerçek telefon doğrulaması</div><div>✓ Teklif karşılaştırma</div><div>✓ Premium mesajlaşma ve iletişim</div><div>✓ Jant/lastik özel ölçüleri</div></div></div></section><section id="app" class="mt-12 hidden"></section></main><div id="modal" class="fixed inset-0 bg-black/50 hidden items-center justify-center p-4"><div class="bg-white rounded-2xl p-6 w-full max-w-md"><div class="flex justify-between"><h3 id="modalTitle" class="font-bold text-xl"></h3><button onclick="closeAuth()">✕</button></div><div id="modalBody" class="mt-5"></div></div></div><div id="toast" class="fixed bottom-5 right-5 hidden bg-slate-950 text-white px-4 py-3 rounded-xl"></div><script>
let token=localStorage.getItem('token'),meta={};
const $=id=>document.getElementById(id); const toast=m=>{let t=$('toast');t.textContent=m;t.classList.remove('hidden');setTimeout(()=>t.classList.add('hidden'),2500)};
async function api(url,opt={}){opt.headers={...(opt.headers||{}),...(token?{Authorization:'Bearer '+token}:{})};if(opt.body&&typeof opt.body==='object'){opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(opt.body)}let r=await fetch(url,opt),d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||'İşlem başarısız');return d}
async function boot(){meta=await fetch('/api/meta').then(r=>r.json());}
function openAuth(mode){$('modal').classList.remove('hidden');$('modal').classList.add('flex');$('modalTitle').textContent=mode==='login'?'Giriş Yap':'Hesap Oluştur';$('modalBody').innerHTML=`${mode==='register'?'<input id="aname" placeholder="Ad Soyad" class="w-full border p-3 rounded-lg mb-3">':''}<input id="aphone" placeholder="0532 111 22 33" class="w-full border p-3 rounded-lg mb-3"><input id="apass" type="password" placeholder="En az 8 karakter" class="w-full border p-3 rounded-lg mb-3">${mode==='register'?'<select id="arole" class="w-full border p-3 rounded-lg mb-3"><option value="buyer">Alıcı</option><option value="seller">Satıcı</option></select>':''}<button onclick="auth('${mode}')" class="w-full bg-slate-950 text-white p-3 rounded-lg">Devam Et</button>`}
function closeAuth(){$('modal').classList.add('hidden')}
async function auth(mode){try{let d=await api('/api/auth/'+(mode==='login'?'login':'register'),{method:'POST',body:{name:mode==='register'?$('aname').value:'Kullanıcı',phone:$('aphone').value,password:$('apass').value,role:mode==='register'?$('arole').value:'buyer'}});token=d.access_token;localStorage.setItem('token',token);closeAuth();toast('Giriş başarılı');showApp()}catch(e){toast(e.message)}}
async function needAuth(role){if(!token){openAuth('login');return}showApp(role)}
function showApp(role='buyer'){$('app').classList.remove('hidden');$('app').innerHTML=role==='seller'?sellerView():buyerView();if(role==='seller')loadListings();}
function buyerView(){let opts=o=>Object.entries(o).map(([k,v])=>`<option value="${k}">${k}</option>`).join('');return `<div class="bg-white border rounded-2xl p-6"><h2 class="text-2xl font-bold">Parça Talebi Oluştur</h2><div class="grid md:grid-cols-2 gap-3 mt-5"><select id="brand" onchange="models()" class="border p-3 rounded-lg"><option value="">Marka</option>${Object.keys(meta.brands).map(x=>`<option>${x}</option>`).join('')}</select><select id="model" class="border p-3 rounded-lg"><option value="">Model</option></select><select id="year" class="border p-3 rounded-lg"><option>Model yılı</option>${meta.years.map(x=>`<option>${x}</option>`).join('')}</select><select id="fuel" class="border p-3 rounded-lg"><option>Yakıt</option>${meta.fuel.map(x=>`<option>${x}</option>`).join('')}</select><input id="engine" placeholder="Motor" class="border p-3 rounded-lg"><input id="power" placeholder="Motor gücü" class="border p-3 rounded-lg"><select id="trans" class="border p-3 rounded-lg"><option>Şanzıman</option>${meta.transmission.map(x=>`<option>${x}</option>`).join('')}</select><input id="trim" placeholder="Paket / donanım" class="border p-3 rounded-lg"><select id="drive" class="border p-3 rounded-lg"><option>Çekiş</option>${meta.drivetrain.map(x=>`<option>${x}</option>`).join('')}</select><select id="color" class="border p-3 rounded-lg"><option>Renk</option>${meta.colors.map(x=>`<option>${x}</option>`).join('')}</select><select id="cat" onchange="partFields()" class="border p-3 rounded-lg"><option value="">Parça kategorisi</option>${meta.categories.map(x=>`<option>${x}</option>`).join('')}</select><input id="province" placeholder="İl" class="border p-3 rounded-lg"><input id="district" placeholder="İlçe" class="border p-3 rounded-lg"></div><div id="partfields" class="mt-3"></div><textarea id="desc" rows="5" placeholder="İhtiyacını ayrıntılı yaz..." class="w-full border p-3 rounded-lg mt-3"></textarea><button onclick="createListing()" class="mt-4 px-5 py-3 rounded-xl bg-emerald-600 text-white">Talebi Yayınla</button></div><div class="mt-5"><button onclick="myListings()" class="px-4 py-2 border rounded-lg">İlanlarım ve Teklifler</button></div>`}
function models(){let b=$('brand').value;$('model').innerHTML='<option value="">Model</option>'+((meta.brands[b]||[]).map(x=>`<option>${x}</option>`).join(''))}
function partFields(){if($('cat').value!=='Jant / Lastik'){$('partfields').innerHTML='';return}$('partfields').innerHTML='<div class="grid md:grid-cols-4 gap-3 bg-slate-50 p-4 rounded-xl"><input id="rim" placeholder="Jant çapı (17\")" class="border p-3 rounded-lg"><input id="rimw" placeholder="Jant genişliği (8J)" class="border p-3 rounded-lg"><input id="et" placeholder="ET" class="border p-3 rounded-lg"><input id="pcd" placeholder="PCD (5x112)" class="border p-3 rounded-lg"><input id="hub" placeholder="Göbek" class="border p-3 rounded-lg"><input id="tire" placeholder="Lastik (225/45 R17)" class="border p-3 rounded-lg"><input id="season" placeholder="Mevsim" class="border p-3 rounded-lg"><input id="qty" placeholder="Adet / set" class="border p-3 rounded-lg"></div>'}
async function createListing(){try{let specs={};['rim','rimw','et','pcd','hub','tire','season','qty'].forEach(k=>{if($(k))specs[k]=$(k).value});let d=await api('/api/listings',{method:'POST',body:{brand:$('brand').value,model:$('model').value,year:Number($('year').value),fuel:$('fuel').value,engine:$('engine').value,power:$('power').value,transmission:$('trans').value,trim:$('trim').value,drivetrain:$('drive').value,color:$('color').value,category:$('cat').value,specs,description:$('desc').value,province:$('province').value,district:$('district').value}});toast('İlan yayınlandı #'+d.id)}catch(e){toast(e.message)}}
function sellerView(){return `<div class="bg-white border rounded-2xl p-6"><div class="flex justify-between items-center"><div><h2 class="text-2xl font-bold">Talep Havuzu</h2><p class="text-slate-500">Uygun taleplere teklif ver.</p></div><button onclick="showPlans()" class="px-4 py-2 rounded-lg bg-amber-400">Premium</button></div><div id="listings" class="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6"></div></div>`}
async function loadListings(){let data=await api('/api/listings');$('listings').innerHTML=data.map(x=>`<article class="border rounded-xl p-4"><b>${x.brand} ${x.model} · ${x.year}</b><p class="text-sm text-slate-500">${x.category} · ${x.province}/${x.district}</p><p class="mt-2">${x.description}</p><button onclick="makeOffer(${x.id})" class="mt-3 w-full bg-slate-950 text-white p-2 rounded-lg">Teklif Ver</button></article>`).join('')||'<p>Henüz aktif talep yok.</p>'}
async function makeOffer(id){let price=prompt('Teklif fiyatı (TL)');if(!price)return;let message=prompt('Mesaj (opsiyonel)')||'';try{await api('/api/listings/'+id+'/offers',{method:'POST',body:{price:Number(price),message}});toast('Teklif gönderildi')}catch(e){toast(e.message)}}
async function myListings(){try{let d=await api('/api/my-listings');$('app').innerHTML='<div class="bg-white border rounded-2xl p-6"><h2 class="text-2xl font-bold">İlanlarım</h2>'+d.map(x=>`<div class="border rounded-xl p-4 mt-4"><b>${x.brand} ${x.model}</b><p>${x.category} · ${x.offers.length} teklif</p>${x.offers.map(o=>`<div class="bg-slate-50 p-3 mt-2 rounded-lg"><b>${o.seller_name}</b> — ₺${o.price.toLocaleString('tr-TR')}<p>${o.message||''}</p>${o.phone?'<small>'+o.phone+'</small>':''}</div>`).join('')}</div>`).join('')+'</div>'}catch(e){toast(e.message)}}
function showPlans(){alert('PRO: aylık 1000 teklif + Premium mesajlaşma + iletişim bilgileri. Ödeme altyapısı için iyzico/sağlayıcı anahtarları sunucu ortamına tanımlanmalıdır.')}boot();</script></body></html>'''

@app.get("/",response_class=HTMLResponse)
def home(): return HTML

if __name__=="__main__":
 import uvicorn
 uvicorn.run(app,host="0.0.0.0",port=int(os.getenv("PORT",8000)))
