# Parça İste PRO v6 — Kalıcı Marketplace Altyapısı

Bu sürüm, PRO v5'in hesap sistemini gerçek marketplace veri modeline taşır.

## Üretim mimarisi

- **Render + FastAPI**
- **PostgreSQL:** `DATABASE_URL` tanımlıysa otomatik kullanılır.
- **SQLite:** lokal geliştirmede `DATABASE_URL` yoksa kullanılır.
- Kullanıcılar, oturumlar, ilanlar, teklifler, favoriler, kayıtlı aramalar, bildirimler ve mesajlar kalıcı veritabanındadır.
- Oturumlar HttpOnly cookie ile tutulur ve sayfa yenilendiğinde `/api/auth/me` ile geri yüklenir.
- Yeni şifreler PBKDF2-SHA256 ile hashlenir; eski PRO v5 SHA-256 hesapları geriye dönük doğrulanabilir.

## Render ayarları

### Build Command

```text
pip install -r requirements.txt
```

### Start Command

```text
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

```text
DATABASE_URL=<Render PostgreSQL bağlantı adresi>
COOKIE_SECURE=1
```

`COOKIE_SECURE=1` HTTPS üzerinde güvenli HttpOnly cookie kullanır. Lokal geliştirmede boş bırakılırsa istek şemasına göre otomatik karar verilir.

## Ana kullanıcı akışları

### Alıcı

Kayıt → giriş → telefon doğrulama → talep oluştur → ilanı kalıcı olarak kaydet → teklifler → bildirim → mesajlaşma → ilanı kapat.

### Satıcı / Esnaf

Kayıt → giriş → ilan havuzu → filtrele → teklif ver → alıcının teklif bildirimi → mesajlaşma.

## Hesabım

- İlanlarım
- Favorilerim
- Kayıtlı Aramalar
- Mesajlar
- Bildirimler
- Profil ve Güvenlik

## Önemli

OTP ve AI Vision hâlâ demo/simülasyon mantığındadır. Gerçek SMS ve gerçek görsel AI servisi bağlanmadan önce ilgili sağlayıcıların API anahtarları eklenmelidir.
