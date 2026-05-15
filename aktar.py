"""
SiteMaster – Mali Devir & Veri Aktarım Merkezi
Eski sistemden gelen sakin listesini ve finansal geçmişi (devreden borçlar,
ödenmiş geçmiş kayıtlar) SiteMaster veritabanına tek seferde aktarır.
"""

from __future__ import annotations

import datetime
import io
import sqlite3
from typing import Any

import pandas as pd
import streamlit as st
from utils import render_header, get_conn, telefon_normalize

# ─── Sabitler ────────────────────────────────────────────────────────────────

YOK = "── SÜTUN YOK / BOŞ BIRAK ──"

CIFT_ATLA     = "Yalnızca yeni kayıt ekle – mevcut daireleri atla"
CIFT_GUNCELLE = "Mevcut kaydı Excel satırıyla güncelle"

SABLON_SUTUNLAR = [
    "Blok", "Daire_No",
    "Malik_Ad", "Malik_TC", "Malik_Tel",
    "Kiraci_Ad", "Kiraci_TC", "Kiraci_Tel",
    "Plaka",
    "Devreden_Borc_TL", "Borc_Aciklama",
    "Odenmis_Gecmis_TL", "Odenmis_Aciklama",
]


# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _sutun_opts(df: pd.DataFrame) -> list[str]:
    return [YOK] + df.columns.tolist()


def _hucre(satir: pd.Series, sutun: str) -> str:
    """Metin hücresini güvenle oku; boş string döndür."""
    if sutun == YOK:
        return ""
    val = satir.get(sutun, "")
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", ""):
        return ""
    # Excel tamsayıları bazen 12.0 yazar; düzelt
    if s.endswith(".0") and s[:-2].lstrip("-").isdigit():
        s = s[:-2]
    return s


def _tutar(satir: pd.Series, sutun: str) -> float | None:
    """Sayısal tutar hücresini oku; yoksa None döndür."""
    s = _hucre(satir, sutun)
    if not s:
        return None
    # Binlik nokta ve ondalık virgül normalize (1.250,50 → 1250.50)
    s = s.replace(".", "").replace(",", ".")
    try:
        val = float(s)
        return val if val > 0 else None
    except ValueError:
        return None


def _mevcut_bloklar(db_yolu: str) -> set[str]:
    try:
        conn = get_conn(db_yolu)
        c = conn.cursor()
        c.execute("SELECT blok_adi FROM bloklar")
        return {str(r[0]).strip() for r in c.fetchall() if r[0]}
    except Exception:
        return set()
    finally:
        conn.close()


def _tel_hucre(satir: pd.Series, kolon: str) -> str:
    ham = _hucre(satir, kolon)
    if not ham:
        return ""
    ok, norm, _ = telefon_normalize(ham, zorunlu=False)
    return norm if ok else ham


def _satiri_isle(satir: pd.Series, sec: dict[str, str]) -> dict[str, Any]:
    """Excel satırını normalize edilmiş alanlara dönüştür."""
    return {
        # Sakin bilgileri
        "blok":         _hucre(satir, sec["blok"]),
        "daire_no":     _hucre(satir, sec["daire"]),
        "malik_ad":     _hucre(satir, sec["m_ad"]),
        "malik_tc":     _hucre(satir, sec["m_tc"]),
        "malik_tel":    _tel_hucre(satir, sec["m_tel"]),
        "kiraci_ad":    _hucre(satir, sec["k_ad"]),
        "kiraci_tc":    _hucre(satir, sec["k_tc"]),
        "kiraci_tel":   _tel_hucre(satir, sec["k_tel"]),
        "plaka":        _hucre(satir, sec["plaka"]),
        # Finansal alanlar
        "devreden_borc":   _tutar(satir, sec["dev_borc"]),
        "borc_aciklama":   _hucre(satir, sec["borc_acik"]),
        "odenmis_tutar":   _tutar(satir, sec["ode_tutar"]),
        "odenmis_aciklama":_hucre(satir, sec["ode_acik"]),
    }


def _excel_satirlarini_coz(
    df: pd.DataFrame,
    sec: dict[str, str],
) -> tuple[list[tuple[int, dict[str, Any]]], int, list[dict[str, Any]]]:
    """
    Satırları (blok, daire) anahtarına göre çöz.
    Aynı anahtar tekrar ederse son satır geçerli; öncekiler nota düşer.
    Döndürür: (satir_listesi, atlanan_bos_sayisi, ic_notlar)
    """
    by_key: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
    atlanan = 0
    notlar: list[dict[str, Any]] = []

    for i, (_, satir) in enumerate(df.iterrows()):
        excel_no = i + 2
        alan = _satiri_isle(satir, sec)

        if not alan["blok"] or not alan["daire_no"]:
            atlanan += 1
            continue

        anahtar = (alan["blok"], alan["daire_no"])
        if anahtar in by_key:
            notlar.append({
                "Excel Satırı": by_key[anahtar][0],
                "Blok":  alan["blok"],
                "Daire": alan["daire_no"],
                "Not":   "Excel içinde aynı blok+daire tekrar etti; son satır kullanıldı.",
            })
        by_key[anahtar] = (excel_no, alan)

    return list(by_key.values()), atlanan, notlar


def _sablon_bytes() -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame(columns=SABLON_SUTUNLAR).to_excel(w, index=False, sheet_name="Sakinler")
    return buf.getvalue()


def _df_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()


# ─── Ana ekran ────────────────────────────────────────────────────────────────

def goster(db_yolu: str) -> None:
    render_header("📥 Mali Devir & Veri Aktarım Merkezi")

    # ── Başlık kartı + şablon ──
    with st.container(border=True):
        h1, h2 = st.columns([4, 1])
        with h1:
            st.markdown(
                "Eski yönetim sisteminizden dışa aktardığınız **Excel (.xlsx)** dosyasını "
                "buradan içe alın. Sakin bilgilerinin yanı sıra **devreden borçları** ve "
                "**ödeme geçmişini** de sisteme taşıyabilirsiniz."
            )
            st.caption(
                "Tüm yeni sakinlere varsayılan şifre **1234** atanır; sakin ilk girişte değiştirebilir."
            )
        with h2:
            st.download_button(
                label="Şablon .xlsx",
                data=_sablon_bytes(),
                file_name="sitemaster_sablon.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Finansal sütunları da içeren boş şablon dosyası.",
            )

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # ADIM 1: Dosya yükle
    # ══════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown("#### Adım 1 — Excel dosyasını yükleyin")
        yuklenen = st.file_uploader(
            "**.xlsx** seçin",
            type=["xlsx"],
            key="aktar_uploader",
            label_visibility="collapsed",
        )

    if yuklenen is None:
        st.info("Dosya seçildiğinde sütun eşleştirme ve aktarım seçenekleri görüntülenecek.")
        return

    try:
        df = pd.read_excel(yuklenen, dtype=str)
        df.fillna("", inplace=True)
        df.replace("nan", "", inplace=True)
    except Exception as e:
        st.error(f"Dosya okunamadı — {e}")
        return

    if df.empty:
        st.error("Yüklenen dosya boş; veri içeren bir Excel seçin.")
        return

    st.success(f"Dosya okundu: **{len(df)}** veri satırı, **{len(df.columns)}** sütun.")
    with st.expander("İlk 5 satıra göz at", expanded=False):
        st.dataframe(df.head(5), use_container_width=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # ADIM 2: Aktarım kuralları
    # ══════════════════════════════════════════════════════════════
    opts = _sutun_opts(df)
    bilinen_bloklar = _mevcut_bloklar(db_yolu)

    with st.container(border=True):
        st.markdown("#### Adım 2 — Aktarım kurallarını belirleyin")

        k1, k2, k3 = st.columns(3)
        with k1:
            cift_politikasi = st.radio(
                "Aynı blok + daire sistemde zaten varsa:",
                (CIFT_ATLA, CIFT_GUNCELLE),
                index=0,
                help="İlk yüklemede 'Atla'; bilgileri tazelemek için tekrar yüklerseniz 'Güncelle'.",
            )
        with k2:
            gecmis_aktar = st.checkbox(
                "Ödenmiş geçmiş kayıtları da aktar",
                value=True,
                help=(
                    "Excel'de 'Ödenmiş Geçmiş TL' ve 'Ödenmiş Açıklama' sütunları "
                    "varsa bunları aidatlar tablosuna 'Ödendi' durumuyla yazar."
                ),
            )
            blok_uyari_ac = st.checkbox(
                "Tanınmayan blok adlarında uyar",
                value=True,
            )
        with k3:
            kuru = st.checkbox(
                "Kuru çalıştır (veritabanına yazma)",
                value=False,
                help="Hangi kayıtların ne kadar borçla geleceğini önce görün; onayladıktan sonra gerçek aktarımı yapın.",
            )
            varsayilan_borc_acik = st.text_input(
                "Varsayılan borç açıklaması",
                value="Geçmiş Dönem Devir Borcu",
                help="Excel'de açıklama sütunu boşsa veya seçilmezse bu metin kullanılır.",
            )

    st.divider()

    # ══════════════════════════════════════════════════════════════
    # ADIM 3: Sütun eşleştirme
    # ══════════════════════════════════════════════════════════════
    with st.container(border=True):
        st.markdown("#### Adım 3 — Sütunları eşleştirin")
        st.caption(
            "Zorunlu alanlar ✱ dışındaki her şeyi boş bırakabilirsiniz. "
            "Finansal sütunlar boş bırakılırsa borç/ödeme kaydı oluşturulmaz."
        )

        with st.form("aktar_form"):
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.markdown("**Daire Bilgileri**")
                sec_blok  = st.selectbox("Blok / Apartman adı ✱", opts, key="f_blok")
                sec_daire = st.selectbox("Daire / Kapı no ✱",     opts, key="f_daire")
                sec_plaka = st.selectbox("Araç plakası",           opts, key="f_plaka")

                st.markdown("**Finansal Devir**")
                sec_dev_borc = st.selectbox(
                    "Devreden Borç Tutarı (TL)",
                    opts,
                    key="f_dev_borc",
                    help="Bu sütundaki tutar > 0 ise daire kaydedildikten sonra aidatlar tablosuna 'Ödenmedi' kaydı eklenir.",
                )
                sec_borc_acik = st.selectbox(
                    "Borç Açıklaması",
                    opts,
                    key="f_borc_acik",
                    help="Boş bırakılırsa yukarıdaki 'Varsayılan borç açıklaması' kullanılır.",
                )
                sec_ode_tutar = st.selectbox(
                    "Ödenmiş Geçmiş Tutarı (TL)",
                    opts,
                    key="f_ode_tutar",
                    help="Geçmişte ödenmiş toplamı 'Ödendi' durumuyla aidatlar tablosuna yazar.",
                )
                sec_ode_acik = st.selectbox(
                    "Ödenmiş Geçmiş Açıklaması",
                    opts,
                    key="f_ode_acik",
                )

            with col_b:
                st.markdown("**Kat Maliki**")
                sec_m_ad  = st.selectbox("Malik adı soyadı", opts, key="f_m_ad")
                sec_m_tc  = st.selectbox("Malik TC kimlik",  opts, key="f_m_tc")
                sec_m_tel = st.selectbox("Malik telefon",    opts, key="f_m_tel")

            with col_c:
                st.markdown("**Kiracı**")
                sec_k_ad  = st.selectbox("Kiracı adı soyadı", opts, key="f_k_ad")
                sec_k_tc  = st.selectbox("Kiracı TC kimlik",  opts, key="f_k_tc")
                sec_k_tel = st.selectbox("Kiracı telefon",    opts, key="f_k_tel")

            gondir = st.form_submit_button(
                "Önizle / Aktarımı Başlat",
                type="primary",
                use_container_width=True,
            )

    if not gondir:
        return

    if sec_blok == YOK or sec_daire == YOK:
        st.error("**Blok** ve **Daire No** sütunları zorunludur; lütfen eşleştirin.")
        return

    sec_map = {
        "blok": sec_blok, "daire": sec_daire, "plaka": sec_plaka,
        "m_ad": sec_m_ad, "m_tc": sec_m_tc, "m_tel": sec_m_tel,
        "k_ad": sec_k_ad, "k_tc": sec_k_tc, "k_tel": sec_k_tel,
        "dev_borc":  sec_dev_borc,  "borc_acik": sec_borc_acik,
        "ode_tutar": sec_ode_tutar, "ode_acik":  sec_ode_acik,
    }

    # ── Excel satırlarını çöz ──
    with st.spinner("Satırlar analiz ediliyor…"):
        satirlar, atlanan_bos, ic_notlar = _excel_satirlarini_coz(df, sec_map)

    guncelle_modu = cift_politikasi == CIFT_GUNCELLE
    bugun_str = datetime.date.today().isoformat()

    # ── Veritabanı ön kontrol ──
    eklenecek:  list[tuple[int, dict[str, Any]]] = []
    atlanan_db: list[dict[str, Any]] = []
    uyari_blok: list[dict[str, Any]] = []
    notlar_list = list(ic_notlar)

    try:
        kon = get_conn(db_yolu)
        cur = kon.cursor()
        for excel_no, alan in satirlar:
            blok, daire = alan["blok"], alan["daire_no"]

            if blok_uyari_ac and bilinen_bloklar and blok not in bilinen_bloklar:
                uyari_blok.append({
                    "Excel Satırı": excel_no, "Blok": blok, "Daire": daire,
                    "Uyarı": f"'{blok}' bloku site kurulumunda tanımlı değil.",
                })

            cur.execute("SELECT id FROM sakinler WHERE blok=? AND daire_no=?", (blok, daire))
            mevcut = cur.fetchone()

            if mevcut and not guncelle_modu:
                atlanan_db.append({
                    "Excel Satırı": excel_no, "Blok": blok, "Daire": daire,
                    "Sebep": "Sistemde kayıt zaten var; politika 'atla'.",
                })
                continue

            eklenecek.append((excel_no, alan))
    except Exception as e:
        st.error(f"Ön kontrol hatası: {e}")
        return
    finally:
        kon.close()

    # ── Finansal özet hesapla ──
    toplam_borc = sum(
        a["devreden_borc"] for _, a in eklenecek if a["devreden_borc"] is not None
    )
    toplam_odenmis = sum(
        a["odenmis_tutar"] for _, a in eklenecek if a["odenmis_tutar"] is not None
    )
    borc_olan_daire = sum(1 for _, a in eklenecek if a["devreden_borc"] is not None)
    odenmis_olan_daire = sum(1 for _, a in eklenecek if a["odenmis_tutar"] is not None)

    # ── Özet metrikler ──
    st.divider()
    st.markdown("#### Aktarım Özeti")

    m1, m2, m3 = st.columns(3)
    m1.metric("İşlenecek daire",          len(eklenecek))
    m2.metric("Blok/daire boş → atlandı", atlanan_bos)
    m3.metric("Sistemde var → atlandı",   len(atlanan_db))

    with st.container(border=True):
        st.markdown("##### Finansal Yük")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Devreden Borçlu Daire",  borc_olan_daire)
        f2.metric("Toplam Aktarılacak Borç", f"{toplam_borc:,.2f} TL")
        f3.metric("Ödenmiş Geçmişi Olan Daire", odenmis_olan_daire)
        f4.metric("Toplam Ödenmiş Geçmiş",  f"{toplam_odenmis:,.2f} TL")

    # Uyarı tabloları
    if uyari_blok:
        st.warning(f"{len(uyari_blok)} satırda tanınmayan blok adı var; aktarım yine de yapılabilir.")
        with st.expander("Tanınmayan blok adları", expanded=True):
            st.dataframe(pd.DataFrame(uyari_blok), use_container_width=True)

    if atlanan_db:
        with st.expander(f"Sistemde zaten var, atlandı ({len(atlanan_db)})", expanded=False):
            st.dataframe(pd.DataFrame(atlanan_db), use_container_width=True)

    if notlar_list:
        with st.expander(f"Excel içi tekrar notları ({len(notlar_list)})", expanded=False):
            st.dataframe(pd.DataFrame(notlar_list), use_container_width=True)

    if not eklenecek:
        st.error("Veritabanına yazılacak satır yok. Çift kayıt politikasını veya eşleştirmeyi gözden geçirin.")
        return

    # ══════════════════════════════════════════════════════════════
    # KURU ÇALIŞTIRMA
    # ══════════════════════════════════════════════════════════════
    if kuru:
        st.info(
            f"**Kuru çalıştırma** — veritabanı değişmedi. "
            f"Yazılacak ilk {min(20, len(eklenecek))} kayıt aşağıda:"
        )
        onizle = []
        for excel_no, alan in eklenecek[:20]:
            borc_acik = alan["borc_aciklama"] or varsayilan_borc_acik
            onizle.append({
                "Excel": excel_no,
                "Blok":  alan["blok"],
                "Daire": alan["daire_no"],
                "Malik": alan["malik_ad"],
                "Kiracı":alan["kiraci_ad"],
                "Devreden Borç (TL)": (
                    f"{alan['devreden_borc']:,.2f}" if alan["devreden_borc"] else "—"
                ),
                "Borç Açıklaması": borc_acik if alan["devreden_borc"] else "—",
                "Ödenmiş Geçmiş (TL)": (
                    f"{alan['odenmis_tutar']:,.2f}" if alan["odenmis_tutar"] and gecmis_aktar else "—"
                ),
            })
        st.dataframe(pd.DataFrame(onizle), use_container_width=True)
        if len(eklenecek) > 20:
            st.caption(f"… ve {len(eklenecek) - 20} satır daha.")
        st.caption("Kuru modu kapatıp tekrar gönderin; kayıtlar ve borçlar birlikte işlenecek.")
        return

    # ══════════════════════════════════════════════════════════════
    # GERÇEK YAZIM
    # ══════════════════════════════════════════════════════════════
    sakin_eklenen    = 0
    sakin_guncellenen = 0
    borc_yazilan     = 0
    gecmis_yazilan   = 0
    yazim_hata: list[dict[str, Any]] = []

    progress = st.progress(0, text="Kayıtlar işleniyor…")
    toplam_satir = len(eklenecek)

    try:
        conn = get_conn(db_yolu)
        cur  = conn.cursor()

        for idx, (excel_no, alan) in enumerate(eklenecek):
            blok, daire = alan["blok"], alan["daire_no"]
            try:
                cur.execute("SELECT id FROM sakinler WHERE blok=? AND daire_no=?", (blok, daire))
                mevcut = cur.fetchone()

                # ── Sakin kaydı ──
                if mevcut and guncelle_modu:
                    cur.execute(
                        """UPDATE sakinler
                           SET malik_ad=?, malik_tc=?, malik_tel=?,
                               kiraci_ad=?, kiraci_tc=?, kiraci_tel=?,
                               plaka=?
                           WHERE blok=? AND daire_no=?""",
                        (
                            alan["malik_ad"],  alan["malik_tc"],  alan["malik_tel"],
                            alan["kiraci_ad"], alan["kiraci_tc"], alan["kiraci_tel"],
                            alan["plaka"],
                            blok, daire,
                        ),
                    )
                    sakin_guncellenen += 1
                elif not mevcut:
                    cur.execute(
                        """INSERT INTO sakinler
                           (blok, daire_no,
                            malik_ad,  malik_tc,  malik_tel,
                            kiraci_ad, kiraci_tc, kiraci_tel,
                            plaka,     sifre)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (
                            blok, daire,
                            alan["malik_ad"],  alan["malik_tc"],  alan["malik_tel"],
                            alan["kiraci_ad"], alan["kiraci_tc"], alan["kiraci_tel"],
                            alan["plaka"],     "1234",
                        ),
                    )
                    sakin_eklenen += 1

                # ── Devreden borç kaydı ──
                if alan["devreden_borc"] is not None:
                    aciklama = alan["borc_aciklama"] or varsayilan_borc_acik
                    cur.execute(
                        """INSERT INTO aidatlar
                           (blok, daire_no, tarih, tutar, aciklama,
                            durum, son_odeme_tarihi, faiz_uygula, yillik_faiz)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            blok, daire,
                            bugun_str,
                            alan["devreden_borc"],
                            aciklama,
                            "Ödenmedi",
                            bugun_str,
                            0,
                            0.0,
                        ),
                    )
                    borc_yazilan += 1

                # ── Ödenmiş geçmiş kaydı (opsiyonel) ──
                if gecmis_aktar and alan["odenmis_tutar"] is not None:
                    ode_acik = alan["odenmis_aciklama"] or "Geçmiş Dönem Ödeme (Devir)"
                    cur.execute(
                        """INSERT INTO aidatlar
                           (blok, daire_no, tarih, tutar, aciklama,
                            durum, son_odeme_tarihi, faiz_uygula, yillik_faiz)
                           VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            blok, daire,
                            bugun_str,
                            alan["odenmis_tutar"],
                            ode_acik,
                            "Ödendi",
                            bugun_str,
                            0,
                            0.0,
                        ),
                    )
                    gecmis_yazilan += 1

            except Exception as satir_hata:
                yazim_hata.append({
                    "Excel Satırı": excel_no,
                    "Blok": blok, "Daire": daire,
                    "Hata": str(satir_hata),
                })

            progress.progress(
                int((idx + 1) / toplam_satir * 100),
                text=f"{idx + 1} / {toplam_satir} satır işlendi…",
            )

        conn.commit()
        progress.empty()

    except Exception as genel_hata:
        conn.rollback()
        progress.empty()
        st.error(f"Kritik hata — işlem geri alındı: {genel_hata}")
        return
    finally:
        conn.close()

    # ── Sonuç kartı ──
    st.divider()
    if sakin_eklenen + sakin_guncellenen > 0:
        with st.container(border=True):
            st.markdown("#### Aktarım Tamamlandı")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Yeni sakin eklendi",   sakin_eklenen)
            r2.metric("Sakin güncellendi",     sakin_guncellenen)
            r3.metric("Borç kaydı oluşturuldu", borc_yazilan)
            r4.metric("Geçmiş ödeme aktarıldı", gecmis_yazilan)

            if borc_yazilan > 0:
                # gerçek yazılan borç toplamı (sadece yazılanlar)
                yazilan_borc_tl = sum(
                    a["devreden_borc"]
                    for _, a in eklenecek
                    if a["devreden_borc"] is not None
                )
                st.success(
                    f"Toplam **{borc_yazilan}** daireye "
                    f"**{yazilan_borc_tl:,.2f} TL** devreden borç başarıyla tahakkuk ettirildi."
                )
            if gecmis_yazilan > 0:
                yazilan_ode_tl = sum(
                    a["odenmis_tutar"]
                    for _, a in eklenecek
                    if a["odenmis_tutar"] is not None
                )
                st.info(
                    f"**{gecmis_yazilan}** dairenin geçmiş ödemesi "
                    f"(**{yazilan_ode_tl:,.2f} TL**) 'Ödendi' olarak hesap geçmişine işlendi."
                )
            if len(yazim_hata) == 0:
                st.balloons()
    else:
        st.warning("Hiçbir sakin kaydı yazılamadı; hata tablosunu inceleyin.")

    if yazim_hata:
        with st.expander(f"Yazım hataları ({len(yazim_hata)} satır)", expanded=True):
            st.dataframe(pd.DataFrame(yazim_hata), use_container_width=True)
            st.download_button(
                label="Hatalı satırları indir (.xlsx)",
                data=_df_excel(pd.DataFrame(yazim_hata)),
                file_name="aktarim_hatali_satirlar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

