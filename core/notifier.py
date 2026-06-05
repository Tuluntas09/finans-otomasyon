"""
E-posta bildirim sistemi — SMTP (Gmail App Password destekli).

Kullanım:
    from core.notifier import send_alert_email, is_configured

    if is_configured():
        send_alert_email(alerts)

.env'e şunları ekle:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=senin@gmail.com
    SMTP_PASS=xxxx xxxx xxxx xxxx   # Gmail: Hesap → Güvenlik → Uygulama şifreleri
    ALERT_EMAIL=hedef@gmail.com     # boşsa SMTP_USER'a gönderilir
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

log = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Yapılandırma kontrolü
# ------------------------------------------------------------------ #
def is_configured() -> bool:
    """SMTP ayarları .env'e girilmişse True döner."""
    import config.settings as s
    return bool(s.SMTP_HOST and s.SMTP_USER and s.SMTP_PASS)


def _recipient() -> str:
    import config.settings as s
    return s.ALERT_EMAIL or s.SMTP_USER or ""


# ------------------------------------------------------------------ #
# HTML e-posta şablonu
# ------------------------------------------------------------------ #
_SEVERITY_COLORS = {
    "critical": "#f4554a",
    "warning":  "#d4a83e",
    "info":     "#3b9eff",
}

_KIND_LABELS = {
    "score_jump":     "Skor Değişimi",
    "verdict_change": "Karar Değişikliği",
    "news_spike":     "Haber Sinyali",
}


def _build_html(alerts: list[dict[str, Any]], summary: dict[str, Any] | None = None) -> str:
    """Uyarı listesinden HTML e-posta içeriği oluşturur."""
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    # Özet satırı
    if summary:
        ok    = summary.get("ok", 0)
        total = summary.get("total", 0)
        news  = summary.get("news_added", 0)
        summary_html = (
            f"<p style='color:#a4adc1;font-size:13px;margin:0 0 20px;'>"
            f"Snapshot: <b style='color:#e6e9f2'>{ok}/{total}</b> sembol başarılı "
            f"· <b style='color:#e6e9f2'>{news}</b> yeni haber indekslendi.</p>"
        )
    else:
        summary_html = ""

    # Uyarı satırları
    rows_html = ""
    for a in alerts:
        sev   = (a.get("severity") or "info").lower()
        color = _SEVERITY_COLORS.get(sev, _SEVERITY_COLORS["info"])
        kind  = _KIND_LABELS.get(a.get("kind") or "", a.get("kind") or "Uyarı")
        ts    = (a.get("created_at") or "")[:16].replace("T", " ")
        rows_html += f"""
        <tr>
          <td style='padding:10px 14px; border-bottom:1px solid #1e2333; vertical-align:top;'>
            <span style='font-family:monospace; font-size:13px; font-weight:700;
                         color:#e6e9f2;'>{a.get('symbol','?')}</span>
          </td>
          <td style='padding:10px 14px; border-bottom:1px solid #1e2333;'>
            <span style='display:inline-block; font-size:10px; font-weight:700;
                         padding:2px 7px; border-radius:4px;
                         background:{color}22; color:{color};
                         letter-spacing:.05em; text-transform:uppercase;'>{kind}</span>
          </td>
          <td style='padding:10px 14px; border-bottom:1px solid #1e2333;
                     font-size:12.5px; color:#a4adc1;'>{a.get('message','')}</td>
          <td style='padding:10px 14px; border-bottom:1px solid #1e2333;
                     font-family:monospace; font-size:11px; color:#525b73;
                     white-space:nowrap;'>{ts}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Finans Otomasyonu — Uyarılar</title>
</head>
<body style='margin:0; padding:0; background:#070a12; font-family:"IBM Plex Sans",
             -apple-system, sans-serif; color:#a4adc1;'>
<table width='100%' cellpadding='0' cellspacing='0' style='background:#070a12;'>
  <tr><td align='center' style='padding:32px 16px;'>
    <table width='600' cellpadding='0' cellspacing='0'
           style='background:#0f1320; border:1px solid #1e2333;
                  border-radius:12px; overflow:hidden;'>

      <!-- HEADER -->
      <tr>
        <td style='padding:20px 24px; background:linear-gradient(180deg,#141828,#0f1320);
                   border-bottom:1px solid #1e2333;'>
          <p style='margin:0; font-size:11px; font-family:monospace;
                    color:#3b9eff; letter-spacing:.12em; text-transform:uppercase;
                    font-weight:700;'>📊 FİNANS OTOMASYONU</p>
          <h1 style='margin:6px 0 0; font-size:20px; font-weight:700;
                     color:#e6e9f2; letter-spacing:-.015em;'>
            {len(alerts)} Yeni Uyarı</h1>
          <p style='margin:4px 0 0; font-size:11.5px; color:#525b73;
                    font-family:monospace;'>{now}</p>
        </td>
      </tr>

      <!-- ÖZET -->
      <tr><td style='padding:18px 24px 0;'>{summary_html}</td></tr>

      <!-- TABLO -->
      <tr>
        <td style='padding:0 24px 16px;'>
          <table width='100%' cellpadding='0' cellspacing='0'
                 style='border:1px solid #1e2333; border-radius:8px; overflow:hidden;'>
            <thead>
              <tr style='background:#0a0d16;'>
                <th style='padding:8px 14px; font-family:monospace; font-size:9.5px;
                           color:#525b73; text-transform:uppercase; letter-spacing:.06em;
                           text-align:left; font-weight:600;'>Sembol</th>
                <th style='padding:8px 14px; font-family:monospace; font-size:9.5px;
                           color:#525b73; text-transform:uppercase; letter-spacing:.06em;
                           text-align:left; font-weight:600;'>Tür</th>
                <th style='padding:8px 14px; font-family:monospace; font-size:9.5px;
                           color:#525b73; text-transform:uppercase; letter-spacing:.06em;
                           text-align:left; font-weight:600;'>Mesaj</th>
                <th style='padding:8px 14px; font-family:monospace; font-size:9.5px;
                           color:#525b73; text-transform:uppercase; letter-spacing:.06em;
                           text-align:left; font-weight:600;'>Zaman</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </td>
      </tr>

      <!-- FOOTER -->
      <tr>
        <td style='padding:16px 24px; border-top:1px solid #1e2333;
                   font-size:10.5px; color:#525b73; font-family:monospace;'>
          ⚠ Kural tabanlı sinyal · Yatırım tavsiyesi DEĞİLDİR.<br>
          Bu e-postayı almak istemiyorsanız .env'den ALERT_EMAIL satırını kaldırın.
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


# ------------------------------------------------------------------ #
# Gönderici
# ------------------------------------------------------------------ #
def send_alert_email(
    alerts: list[dict[str, Any]],
    summary: dict[str, Any] | None = None,
) -> bool:
    """
    Uyarıları HTML e-posta olarak gönderir.
    Başarılıysa True, hata/devre dışıysa False döner.

    Parametreler
    ----------
    alerts  : db.recent_alerts() veya _maybe_alert() çıktısı gibi dict listesi
    summary : run_snapshot() özeti (isteğe bağlı — e-postaya ek bilgi ekler)
    """
    if not alerts:
        return False
    if not is_configured():
        log.debug("SMTP yapılandırılmamış — e-posta gönderilmiyor")
        return False

    import config.settings as s
    recipient = _recipient()
    if not recipient:
        log.warning("ALERT_EMAIL veya SMTP_USER tanımlı değil")
        return False

    subject = f"[Finans Otomasyonu] {len(alerts)} uyarı — {datetime.now(timezone.utc).strftime('%d %b %Y')}"
    html_body = _build_html(alerts, summary)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = s.SMTP_USER
    msg["To"]      = recipient
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(s.SMTP_HOST, s.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(s.SMTP_USER, s.SMTP_PASS)
            server.sendmail(s.SMTP_USER, recipient, msg.as_string())
        log.info("E-posta gönderildi → %s (%d uyarı)", recipient, len(alerts))
        return True
    except smtplib.SMTPAuthenticationError:
        log.error("SMTP kimlik doğrulama hatası — Gmail için Uygulama Şifresi gerekli")
    except smtplib.SMTPException as e:
        log.error("SMTP hatası: %s", e)
    except Exception as e:
        log.error("E-posta gönderilemedi: %s", e)
    return False


def send_test_email() -> tuple[bool, str]:
    """
    Test e-postası gönder. Ayarlar sayfasındaki butondan çağrılır.
    (başarı, mesaj) tuple'ı döndürür.
    """
    if not is_configured():
        return False, "SMTP yapılandırılmamış. .env'e SMTP_HOST/USER/PASS ekle."

    fake_alerts = [
        {
            "symbol":     "TEST",
            "kind":       "score_jump",
            "severity":   "info",
            "message":    "Bu bir test bildirimidir. Sistem doğru çalışıyor.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    ok = send_alert_email(fake_alerts, summary=None)
    if ok:
        return True, f"Test e-postası gönderildi → {_recipient()}"
    return False, "Gönderim başarısız. Logları kontrol et."
