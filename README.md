# 📊 Finans Otomasyonu — Hisse & Emtia

> Finnhub API üzerinden çalışan, **6 boyutta puanlama + haber sentiment + yatırım önerisi** üreten otomatik dashboard.

- **Stack:** Python 3.11 · Streamlit · SQLite · Plotly · VADER · GitHub Actions
- **Watchlist (varsayılan):** AAPL · MSFT · GOOGL · AMZN · NVDA · META · TSLA · GLD · SLV · USO · UNG · DBA
- **Otomasyon:** Her sabah 09:00 Türkiye saati otomatik veri toplama
- **Önemli:** Bu uygulama eğitim amaçlıdır, **yatırım tavsiyesi değildir**.

---

## 🎯 Ne yapar?

1. **Snapshot toplar** — Finnhub'tan fiyat, temel oranlar, analist tavsiyeleri, haberler.
2. **Analiz eder:**
   - **Hisseler** → 6 boyut: Değerleme · Kârlılık · Büyüme · Finansal Sağlık · Teknik · Analist+Haber.
   - **Emtia ETF'leri** → 4 boyut: Teknik · Haber · Oynaklık · Uzun vadeli trend.
3. **Haberleri puanlar** — VADER ile sentiment + anahtar kelime kategori (earnings, M&A, regülasyon, ...).
4. **Yatırım önerir** — Analiz + skor trendi + sentiment + momentum birleşik skor.
5. **Geçmiş tutar** — Her snapshot SQLite'a yazılır; fiyat/skor grafikleri.
6. **Alert üretir** — Skor 10+ puan sıçradığında ya da AL→SAT geçişlerinde.

---

## 🚀 Kurulum (yerel)

```powershell
# 1. Sanal ortam
cd C:\Users\user\finans-otomasyon
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. .env oluştur
copy .env.example .env
# Sonra .env içindeki FINNHUB_API_KEY=... satırını kendi anahtarınla doldur.

# 3. İlk veri toplaması
python -m jobs.daily_snapshot

# 4. Dashboard
streamlit run streamlit_app.py
```

Tarayıcı `http://localhost:8501` adresinde açılır.

> Finnhub ücretsiz anahtarı: https://finnhub.io/register

---

## ⏰ Günlük 09:00 otomasyonu

Üç yol var; senin için **GitHub Actions** kuruldu.

### A) GitHub Actions (cloud — bilgisayar kapalı olsa da çalışır)

1. Bu projeyi GitHub'a push'la.
2. Repo → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `FINNHUB_API_KEY`
   - Value: senin Finnhub anahtarın
3. Hazır. `.github/workflows/daily-snapshot.yml` her sabah 06:00 UTC (= 09:00 TR) çalışır,
   `data/finans.db` dosyasını günceller ve repo'ya commit'ler.
4. Streamlit Cloud'a deploy edersen, yeni veri otomatik dashboard'a yansır.

Manuel tetikleme: Actions sekmesi → "Daily Snapshot" → **Run workflow**.

### B) Windows Task Scheduler (yerel — bilgisayar açık olmalı)

1. Win+R → `taskschd.msc`
2. "Create Basic Task" → Trigger: Daily 09:00 → Action: Start a program
   - Program: `C:\Users\user\finans-otomasyon\.venv\Scripts\python.exe`
   - Arguments: `-m jobs.daily_snapshot`
   - Start in: `C:\Users\user\finans-otomasyon`

### C) Streamlit içinden manuel

Sol menüde **"🔄 Şimdi Çalıştır"** butonu — istediğin an snapshot al.

---

## 🌐 Streamlit Cloud'a deploy

1. GitHub'a push'la (yukarıdaki Actions adımı zaten gerektiriyor).
2. https://share.streamlit.io → **New app** → repo seç → `streamlit_app.py`
3. **Secrets** kısmına şunu ekle:
   ```toml
   FINNHUB_API_KEY = "senin_anahtarın"
   ```
4. Deploy.

GitHub Actions her sabah DB'yi günceller ve repo'ya commit'ler; Streamlit Cloud bunu otomatik çeker.

---

## 📁 Proje yapısı

```
finans-otomasyon/
├── streamlit_app.py            Ana giriş
├── requirements.txt
├── .env.example                .env şablonu
├── .gitignore
├── README.md
│
├── config/
│   ├── settings.py             Ağırlıklar, eşikler, env yükleme
│   └── watchlist.json          Takip edilen semboller
│
├── core/
│   ├── finnhub_client.py       API + rate-limit + retry
│   ├── database.py             SQLite şema + sorgular
│   ├── analyzer.py             6 boyut hisse / 4 boyut emtia
│   ├── news_analyzer.py        VADER sentiment + kategori
│   └── recommender.py          Yatırım önerisi motoru
│
├── ui/
│   ├── components.py           Plotly grafik + HTML kart
│   ├── dashboard.py            Genel bakış
│   ├── stock_detail.py         Tek sembol detayı
│   ├── news_page.py            Haber akışı + sentiment
│   └── portfolio.py            Yatırım önerisi
│
├── jobs/
│   └── daily_snapshot.py       9:00 cron job
│
├── data/
│   └── finans.db               SQLite (auto-create, gitignored)
│
└── .github/
    └── workflows/
        └── daily-snapshot.yml  Her sabah 06:00 UTC
```

---

## 🧠 Analiz formülü

**Hisse genel skoru** = Değerleme(%20) + Kârlılık(%20) + Büyüme(%20) + Sağlık(%15) + Teknik(%15) + (Analist %70 + Haber %30)(%10)

**Emtia genel skoru** = Teknik(%45) + Haber Sentiment(%30) + Oynaklık(%15) + Uzun Trend(%10)

**Yatırım önerisi** = Genel Skor(%50) + Skor Trendi(%20) + Sentiment(%15) + Momentum(%15)

**Karar bantları:**
- ≥75 → **GÜÇLÜ AL** 🟢
- 60–74 → **AL / BİRİKTİR** 🟢
- 45–59 → **TUT** 🟡
- 32–44 → **AZALT / SAT** 🟠
- <32 → **GÜÇLÜ SAT** 🔴

Tüm ağırlık ve eşikleri `config/settings.py` üzerinden değiştirebilirsin.

---

## 🔧 Watchlist düzenleme

UI'da **Ayarlar** sekmesi var — `SEMBOL — İSİM` satırlarıyla istediğini ekle/çıkar.
Alternatif: `config/watchlist.json` dosyasını elle düzenle.

---

## 🐛 Yaygın sorunlar

| Belirti | Çözüm |
|--------|-------|
| "FINNHUB_API_KEY tanımlı değil" | `.env` dosyası yok ya da boş. `.env.example`'ı `.env`'e kopyala, anahtarı doldur. |
| 429 / "rate-limited" | Ücretsiz plan 60/dakika. İstemci 50'de tutuyor ama yine olabilir; birkaç dakika bekle. |
| Bazı semboller skor=None | Finnhub'ın ücretsiz planında bazı temel veriler yok. Eksik boyut otomatik atlanıyor. |
| BIST hisseleri çalışmıyor | Ücretsiz planda BIST verisi sınırlı/yok. ABD piyasası tam destekli. |
| `stock/candle` 403 | Bu endpoint bazı planlarda kısıtlı. Teknik skor olmadan da analiz çalışır. |

---

## 📝 Lisans

MIT — istediğin gibi kullan, değiştir, paylaş.
