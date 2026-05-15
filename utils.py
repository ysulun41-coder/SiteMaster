"""SiteMaster – Ortak Araçlar"""
from __future__ import annotations

import base64
import calendar
import datetime
import html as html_lib
import sqlite3
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

AYLAR_TR = (
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
)


def tarih_input(
    label: str,
    value: datetime.date | None = None,
    min_value: datetime.date | None = None,
    max_value: datetime.date | None = None,
    key: str | None = None,
    help: str | None = None,
) -> datetime.date:
    """
    Türkçe tarih seçici (yıl → ay adı → gün).
    st.date_input yerine kullanın; takvim İngilizce çıkmaz.
    """
    value = value or datetime.date.today()
    k = key or f"tarih_{label.replace(' ', '_').replace('*', '').strip()}"

    if min_value is None:
        min_value = datetime.date(2000, 1, 1)
    if max_value is None:
        max_value = datetime.date(2035, 12, 31)

    value = max(min_value, min(max_value, value))

    st.markdown(f"**{label}**")
    if help:
        st.caption(help)

    c_yil, c_ay, c_gun = st.columns(3)
    yillar = list(range(min_value.year, max_value.year + 1))

    with c_yil:
        yil = st.selectbox(
            "Yıl",
            options=yillar,
            index=yillar.index(value.year) if value.year in yillar else len(yillar) - 1,
            key=f"{k}_yil",
        )
    with c_ay:
        ay_i = st.selectbox(
            "Ay",
            options=list(range(12)),
            index=value.month - 1,
            format_func=lambda i: AYLAR_TR[i],
            key=f"{k}_ay",
        )

    ay = ay_i + 1
    max_gun = calendar.monthrange(yil, ay)[1]
    min_gun = 1
    if yil == min_value.year and ay == min_value.month:
        min_gun = min_value.day
    max_gun_eff = max_gun
    if yil == max_value.year and ay == max_value.month:
        max_gun_eff = min(max_gun, max_value.day)

    gunler = list(range(min_gun, max_gun_eff + 1))
    gun_sec = value.day if value.day in gunler else gunler[-1]

    with c_gun:
        gun = st.selectbox(
            "Gün",
            options=gunler,
            index=gunler.index(gun_sec),
            key=f"{k}_gun",
        )

    return datetime.date(yil, ay, gun)


def get_conn(db_yolu: str) -> sqlite3.Connection:
    """
    Thread-safe, kilitlenmeye dayanıklı SQLite bağlantısı döner.
    - check_same_thread=False : farklı thread'lerden güvenli erişim
    - timeout=15              : kilit beklemesi için 15 saniye sabır
    - WAL journal_mode        : okuma-yazma çakışmalarını en aza indirir
    - busy_timeout=15000      : PRAGMA seviyesinde ek bekleme (ms)
    """
    conn = sqlite3.connect(db_yolu, check_same_thread=False, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn

# SiteMaster markasının kendi statik logosu (asla değişmez)
_SM_LOGO = Path(__file__).parent / "logo.png"
_SM_B64_CACHE: str | None = None


def _sm_logo_b64() -> str | None:
    """SiteMaster marka logosunu (logo.png) base64 olarak döner — önbelleğe alır."""
    global _SM_B64_CACHE
    if _SM_B64_CACHE is None and _SM_LOGO.exists():
        _SM_B64_CACHE = base64.b64encode(_SM_LOGO.read_bytes()).decode()
    return _SM_B64_CACHE


def get_site_logo(master_db_yolu: str, aktif_site: str) -> str | None:
    """Aktif sitenin logosunu base64 olarak döner."""
    bilgi = get_site_bilgi(master_db_yolu, aktif_site)
    return bilgi.get("logo_b64") if bilgi else None


def get_site_bilgi(master_db_yolu: str, aktif_site: str) -> dict | None:
    """Kayıtta girilen site kurumsal bilgileri + logo."""
    try:
        with get_conn(master_db_yolu) as conn:
            row = conn.execute(
                """SELECT site_adi, adres, vergi_no, telefon, eposta, logo, il, ilce, mahalle
                   FROM siteler WHERE site_adi = ?""",
                (aktif_site,),
            ).fetchone()
        if not row:
            return None
        return {
            "site_adi": row[0] or aktif_site,
            "adres": row[1] or "",
            "vergi_no": row[2] or "",
            "telefon": row[3] or "",
            "eposta": row[4] or "",
            "logo_b64": row[5] if row[5] else None,
            "il": row[6] or "",
            "ilce": row[7] or "",
            "mahalle": row[8] or "",
        }
    except Exception:
        return None


def logo_data_uri(logo_b64: str | None) -> str | None:
    if not logo_b64:
        return None
    try:
        pad = "=" * (-len(logo_b64) % 4)
        head = base64.b64decode(logo_b64[:32] + pad)
        mime = "image/jpeg" if head[:3] == b"\xff\xd8\xff" else "image/png"
    except Exception:
        mime = "image/png"
    return f"data:{mime};base64,{logo_b64}"


def makbuz_kurum_basligi(site: dict) -> str:
    """Metin makbuzu için üst bilgi (logo hariç)."""
    satirlar = [site.get("site_adi", "").strip() or "Site"]
    adres = (site.get("adres") or "").strip()
    if not adres and site.get("mahalle"):
        adres = f"{site.get('mahalle', '')}, {site.get('ilce', '')}, {site.get('il', '')}".strip(", ")
    if adres:
        satirlar.append(f"Adres      : {adres}")
    if site.get("vergi_no"):
        satirlar.append(f"Vergi No   : {site['vergi_no']}")
    if site.get("telefon"):
        satirlar.append(f"Telefon    : {site['telefon']}")
    if site.get("eposta"):
        satirlar.append(f"E-posta    : {site['eposta']}")
    return "\n".join(satirlar)


def _site_adres_metin(site: dict) -> str:
    adres = (site.get("adres") or "").strip()
    if not adres and site.get("mahalle"):
        adres = f"{site.get('mahalle', '')}, {site.get('ilce', '')}, {site.get('il', '')}".strip(", ")
    return adres


def makbuz_metni_olustur(
    site: dict,
    *,
    baslik: str,
    islem_tarihi: str,
    govde: str,
    alt_not: str = "Bizi tercih ettiğiniz için teşekkür ederiz.",
    durum_satir: str | None = "ÖDENDİ (Tahsil Edildi)",
) -> str:
    kurum = makbuz_kurum_basligi(site)
    durum_blok = f"Durum       : {durum_satir}\n" if durum_satir else ""
    return f"""
{'=' * 49}
{kurum}
{'=' * 49}
 {baslik}
{'=' * 49}
İşlem Tarihi: {islem_tarihi}
-------------------------------------------------
{govde}
-------------------------------------------------
{durum_blok}{'=' * 49}
{alt_not}
""".strip() + "\n"


def makbuz_html_olustur(
    site: dict,
    *,
    baslik: str,
    islem_tarihi: str = "",
    detay_satirlari: list[tuple[str, str]] | None = None,
    govde_metin: str = "",
    alt_not: str = "",
    durum_metin: str = "",
    imza_html: str = "",
) -> str:
    """Logo gömülü HTML — tarayıcıda açılıp yazdırılabilir."""
    detay_satirlari = detay_satirlari or []
    e = html_lib.escape
    site_adi = e(site.get("site_adi", "Site"))
    adres = e(_site_adres_metin(site))

    logo_blk = ""
    uri = logo_data_uri(site.get("logo_b64"))
    if uri:
        logo_blk = f'<img src="{uri}" alt="Logo" class="logo" />'

    kurum_ek = []
    if site.get("vergi_no"):
        kurum_ek.append(f"<div>Vergi No: {e(site['vergi_no'])}</div>")
    if site.get("telefon"):
        kurum_ek.append(f"<div>Tel: {e(site['telefon'])}</div>")
    if site.get("eposta"):
        kurum_ek.append(f"<div>E-posta: {e(site['eposta'])}</div>")
    kurum_ek_html = "".join(kurum_ek)

    satir_html = ""
    for etiket, deger in detay_satirlari:
        satir_html += (
            f'<tr><td class="lbl">{e(etiket)}</td>'
            f'<td class="val">{e(str(deger))}</td></tr>\n'
        )

    tarih_satir = ""
    if islem_tarihi:
        tarih_satir = f'<p class="tarih">İşlem tarihi: <strong>{e(islem_tarihi)}</strong></p>'

    govde_blk = ""
    if govde_metin.strip():
        govde_satir = "<br>".join(e(ln) for ln in govde_metin.strip().splitlines())
        govde_blk = f'<div class="govde">{govde_satir}</div>'

    durum_blk = f'<p class="durum">{e(durum_metin)}</p>' if durum_metin else ""
    alt_blk = f'<p class="alt">{e(alt_not)}</p>' if alt_not else ""

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <title>{e(baslik)} — {site_adi}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #f1f5f9; color: #0f172a; padding: 24px;
    }}
    .belge {{
      max-width: 720px; margin: 0 auto; background: #fff;
      border: 1px solid #e2e8f0; border-radius: 12px;
      box-shadow: 0 4px 24px rgba(15,23,42,.08); overflow: hidden;
    }}
    .ust {{
      display: flex; gap: 20px; align-items: center;
      padding: 24px 28px; border-bottom: 2px solid #2563eb;
      background: linear-gradient(180deg, #f8fafc 0%, #fff 100%);
    }}
    .logo {{ max-height: 88px; max-width: 180px; object-fit: contain; }}
    .kurum h1 {{ font-size: 1.35rem; font-weight: 800; color: #0f172a; margin-bottom: 6px; }}
    .kurum .adres {{ font-size: 0.9rem; color: #475569; line-height: 1.5; }}
    .kurum div {{ font-size: 0.85rem; color: #64748b; margin-top: 2px; }}
    .baslik {{
      text-align: center; padding: 16px; font-size: 1.1rem;
      font-weight: 700; letter-spacing: 0.04em;
      color: #1e40af; background: #eff6ff;
    }}
    .icerik {{ padding: 24px 28px 28px; }}
    .tarih {{ font-size: 0.9rem; color: #64748b; margin-bottom: 16px; }}
    table.detay {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
    table.detay td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
    table.detay .lbl {{
      width: 38%; font-weight: 600; color: #475569; font-size: 0.88rem;
    }}
    table.detay .val {{ color: #0f172a; font-size: 0.95rem; }}
    .govde {{
      white-space: pre-wrap; font-family: inherit; font-size: 0.92rem;
      line-height: 1.55; background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 14px 16px; margin: 12px 0;
    }}
    .durum {{
      font-weight: 700; color: #15803d; margin-top: 12px; font-size: 0.95rem;
    }}
    .imza {{ margin-top: 28px; padding-top: 20px; border-top: 1px dashed #cbd5e1; }}
    .imza p {{ font-size: 0.88rem; color: #475569; margin-bottom: 20px; line-height: 1.5; }}
    .imza-row {{ display: flex; justify-content: space-between; gap: 24px; margin-top: 8px; }}
    .imza-kutu {{
      flex: 1; text-align: center; font-size: 0.8rem; color: #64748b;
    }}
    .imza-cizgi {{
      border-top: 1px solid #94a3b8; margin: 48px 12px 8px; height: 0;
    }}
    .alt {{ margin-top: 20px; font-size: 0.82rem; color: #94a3b8; text-align: center; }}
    @media print {{
      body {{ background: #fff; padding: 0; }}
      .belge {{ box-shadow: none; border: none; max-width: 100%; }}
    }}
  </style>
</head>
<body>
  <div class="belge">
    <div class="ust">
      {logo_blk}
      <div class="kurum">
        <h1>{site_adi}</h1>
        {"<p class='adres'>" + adres + "</p>" if adres else ""}
        {kurum_ek_html}
      </div>
    </div>
    <div class="baslik">{e(baslik)}</div>
    <div class="icerik">
      {tarih_satir}
      {"<table class='detay'>" + satir_html + "</table>" if satir_html else ""}
      {govde_blk}
      {durum_blk}
      {imza_html}
      {alt_blk}
    </div>
  </div>
</body>
</html>"""


def render_makbuz_karti(site: dict, makbuz_metni: str, html_onizleme: str | None = None) -> None:
    """Ekranda logo + kurum bilgisi; varsa HTML önizleme (iframe)."""
    if html_onizleme:
        # st.markdown bazı etiketleri (<pre>, <p>) düz metin gösterir; tam HTML iframe'de render edilir
        components.html(html_onizleme, height=620, scrolling=True)
    else:
        logo_col, bilgi_col = st.columns([1, 3])
        with logo_col:
            uri = logo_data_uri(site.get("logo_b64"))
            if uri:
                st.image(uri, use_container_width=True)
        with bilgi_col:
            st.markdown(f"**{site.get('site_adi', 'Site')}**")
            adres = _site_adres_metin(site)
            if adres:
                st.caption(f"📍 {adres}")
            if site.get("vergi_no"):
                st.caption(f"Vergi no: {site['vergi_no']}")
            if site.get("telefon"):
                st.caption(f"Tel: {site['telefon']}")
            if site.get("eposta"):
                st.caption(f"E-posta: {site['eposta']}")
        with st.expander("Metin özeti", expanded=False):
            st.code(makbuz_metni, language="text")


def render_makbuz_indir_butonlari(
    *,
    txt_icerik: str,
    html_icerik: str,
    dosya_oneki: str,
) -> None:
    """TXT + logolu HTML indirme butonları."""
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "📥 Metin (.txt)",
            data=txt_icerik,
            file_name=f"{dosya_oneki}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "🖨️ Yazdır / PDF (.html, logolu)",
            data=html_icerik,
            file_name=f"{dosya_oneki}.html",
            mime="text/html",
            use_container_width=True,
            help="İndirip tarayıcıda açın; Ctrl+P ile PDF veya yazıcıya gönderin. Logo bu dosyada yer alır.",
        )


def render_header(page_title: str) -> None:
    """
    Her sayfanın en üstünde logo + başlık satırı oluşturur.
      sol kolon [1] → SiteMaster'ın kendi sabit markası (logo.png)
      sağ kolon [4] → sayfa başlığı
    İçerik bu satırın altında tam genişlikte akar.
    """
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        b64 = _sm_logo_b64()
        if b64:
            st.image(f"data:image/png;base64,{b64}", width=150)
    with col_title:
        st.subheader(page_title)


def render_sidebar_header() -> None:
    """Sidebar tepesine site logosunu (DB'den) optimize boyutla gösterir."""
    b64 = st.session_state.get("logo_b64")
    if not b64:
        return
    with st.sidebar:
        st.image(f"data:image/png;base64,{b64}", use_container_width=True)
        st.divider()
