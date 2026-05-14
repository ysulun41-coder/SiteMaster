"""
SiteMaster – Finansal Tahakkuk Motoru
Toplu aidat tahakkuku, tekil borç girişi ve gecikme faizi hesaplama motoru.
`faiz_hesapla` fonksiyonu diğer modüllerden import edilebilir.
"""

from __future__ import annotations

import datetime
import sqlite3
from typing import Any, Optional

import streamlit as st
from utils import render_header

# ─── Sabitler ────────────────────────────────────────────────────────────────
AYLAR = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


# ═══════════════════════════════════════════════════════════════════════════════
# GECİKME FAİZİ HESAPLAMA MOTORU  (diğer modüller bu fonksiyonu import edebilir)
# ═══════════════════════════════════════════════════════════════════════════════

def faiz_hesapla(
    ana_para: float,
    yillik_faiz_oran: float,
    son_odeme_tarihi_str: str,
    bugun: Optional[datetime.date] = None,
) -> dict[str, Any]:
    """
    Son ödeme tarihi geçmişse günlük basit faiz hesaplar.

    Formül:
        Günlük Oran = Yıllık Oran (%) / 100 / 365
        Faiz        = Ana Para × Günlük Oran × Gecikme Gün Sayısı

    Parametreler:
        ana_para              : Borç anapara tutarı (TL)
        yillik_faiz_oran      : Yıllık faiz oranı (örn. 60.0 → %60)
        son_odeme_tarihi_str  : ISO format tarih "YYYY-MM-DD"
        bugun                 : Test veya geçmiş tarih simülasyonu için; None ise today()

    Döndürür (dict):
        gecikme_gun  : Kaç gün geciktiği (0 ise vadesi geçmemiş)
        faiz_tutari  : Hesaplanan faiz miktarı (TL)
        toplam_borc  : Ana para + faiz (TL)
        gunluk_oran  : Günlük faiz oranı (ondalık, ör. 0.00164)
    """
    if bugun is None:
        bugun = datetime.date.today()

    bos: dict[str, Any] = {
        "gecikme_gun": 0,
        "faiz_tutari": 0.0,
        "toplam_borc": round(ana_para, 2),
        "gunluk_oran": 0.0,
    }

    if not son_odeme_tarihi_str or ana_para <= 0 or yillik_faiz_oran <= 0:
        return bos

    try:
        son_tarih = datetime.date.fromisoformat(son_odeme_tarihi_str)
    except ValueError:
        return bos

    if bugun <= son_tarih:
        return bos

    gecikme_gun = (bugun - son_tarih).days
    gunluk_oran = yillik_faiz_oran / 100.0 / 365.0
    faiz_tutari = round(ana_para * gunluk_oran * gecikme_gun, 2)

    return {
        "gecikme_gun": gecikme_gun,
        "faiz_tutari": faiz_tutari,
        "toplam_borc": round(ana_para + faiz_tutari, 2),
        "gunluk_oran": gunluk_oran,
    }


# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _etiket(blok: str, daire_no: str, malik_ad: Optional[str]) -> str:
    isim = (malik_ad or "").strip() or "İsimsiz"
    return f"{blok} Blok – No:{daire_no}  ({isim})"


def _otomatik_aciklama(tarih: datetime.date, ek_metin: str) -> str:
    """'Haziran 2026 Aidat Ödemesi' formatında açıklama üretir."""
    ay   = AYLAR[tarih.month - 1]
    yil  = tarih.year
    ek   = (ek_metin or "").strip()
    return f"{ay} {yil} {ek}".strip()


def _sakinleri_yukle(db_yolu: str) -> list[tuple[str, str, str]]:
    conn = sqlite3.connect(db_yolu)
    try:
        c = conn.cursor()
        c.execute(
            "SELECT blok, daire_no, malik_ad FROM sakinler ORDER BY blok, daire_no"
        )
        return c.fetchall()
    finally:
        conn.close()


def _aidat_ekle(
    cur: sqlite3.Cursor,
    blok: str,
    daire_no: str,
    tarih: str,
    tutar: float,
    aciklama: str,
    son_odeme: str,
    faiz_uygula: int,
    yillik_faiz: float,
) -> None:
    cur.execute(
        """INSERT INTO aidatlar
           (blok, daire_no, tarih, tutar, aciklama,
            son_odeme_tarihi, faiz_uygula, yillik_faiz)
           VALUES (?,?,?,?,?,?,?,?)""",
        (blok, daire_no, tarih, tutar, aciklama, son_odeme, faiz_uygula, yillik_faiz),
    )


def _faiz_aciklamasi_goster(yillik_faiz: float, son_odeme: datetime.date) -> None:
    """Faiz etkin olduğunda bilgilendirici hesap özeti gösterir."""
    bugun = datetime.date.today()
    if bugun > son_odeme and yillik_faiz > 0:
        gun = (bugun - son_odeme).days
        oran = yillik_faiz / 100 / 365
        st.warning(
            f"Seçilen son ödeme tarihi **{gun} gün** önce geçti. "
            f"Günlük faiz oranı: **%{oran * 100:.4f}** — "
            f"Örnek: 1.000 ₺ borç için gecikme faizi **{1000 * oran * gun:.2f} ₺**."
        )
    else:
        gun_kalan = (son_odeme - bugun).days if bugun <= son_odeme else 0
        st.info(
            f"Faiz aktif. Son ödeme tarihine **{gun_kalan} gün** kaldı. "
            f"Vade geçince günlük **%{yillik_faiz / 100 / 365 * 100:.4f}** oran uygulanır."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ANA EKRAN
# ═══════════════════════════════════════════════════════════════════════════════

def goster(db_yolu: str) -> None:
    render_header("💰 Finansal Tahakkuk Motoru")
    bugun = datetime.date.today()

    tab1, tab2, tab3 = st.tabs([
        "⚙️ Otomatik Talimat",
        "🔄 Toplu Tahakkuk",
        "🎯 Tekil Borç",
    ])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1 — OTOMATİK TALİMAT
    # ══════════════════════════════════════════════════════════════════════
    with tab1:
        with st.container(border=True):
            st.markdown("#### Aylık Otomatik Dağıtım Talimatı")
            st.caption(
                "Motor her ayın 1'inde çalışır. Aynı ay için tek kayıt oluşturur "
                "(`otomatik_kayitlar` tablosuyla tekilleştirilir)."
            )

            conn = sqlite3.connect(db_yolu)
            c    = conn.cursor()
            c.execute("SELECT tutar, aciklama, durum FROM otomatik_talimatlar WHERE id=1")
            mevcut = c.fetchone()

            with st.form("oto_talimat_form"):
                ot_c1, ot_c2 = st.columns(2)
                with ot_c1:
                    ot_tutar = st.number_input(
                        "Aylık Sabit Aidat Tutarı (₺)",
                        value=float(mevcut[0]) if mevcut else 0.0,
                        min_value=0.0, step=100.0,
                    )
                with ot_c2:
                    ot_aciklama = st.text_input(
                        "Açıklama Taslağı",
                        value=mevcut[1] if mevcut else "Aidat Ödemesi",
                        help="Sistem önüne 'Ocak 2026' gibi ay/yıl ekler.",
                    )

                ot_durum = st.toggle(
                    "Otomatik Dağıtım Aktif",
                    value=bool(mevcut[2]) if mevcut else False,
                )

                if st.form_submit_button("Talimatı Kaydet / Güncelle", type="primary"):
                    if mevcut:
                        c.execute(
                            "UPDATE otomatik_talimatlar SET tutar=?, aciklama=?, durum=? WHERE id=1",
                            (ot_tutar, ot_aciklama, 1 if ot_durum else 0),
                        )
                    else:
                        c.execute(
                            "INSERT INTO otomatik_talimatlar (tutar, aciklama, durum) VALUES (?,?,?)",
                            (ot_tutar, ot_aciklama, 1 if ot_durum else 0),
                        )
                    conn.commit()
                    st.success("Otomatik aidat talimatı güncellendi.")
            conn.close()

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2 — TOPLU TAHAKKUK
    # ══════════════════════════════════════════════════════════════════════
    with tab2:

        sakin_listesi = _sakinleri_yukle(db_yolu)
        etiket_harita: dict[str, tuple[str, str]] = {}
        for blok, dno, mad in sakin_listesi:
            etiket_harita[_etiket(blok, dno, mad)] = (blok, dno)
        tum_etiketler = list(etiket_harita.keys())

        with st.container(border=True):
            st.markdown("### Toplu Aidat Dağıtımı")
            st.caption(
                "Tüm kayıtlı dairelere aynı tutarda tahakkuk oluşturur. "
                "Muaf tutmak istediğiniz daireleri aşağıdan seçin."
            )

            # ── Parametre satırı ──────────────────────────────────────
            pc1, pc2 = st.columns(2)
            with pc1:
                t_aidat = st.number_input(
                    "Aidat Tutarı (₺) ✱",
                    min_value=0.0, value=0.0, step=50.0,
                    format="%.2f", key="tp_tutar",
                )
                t_tahakkuk = st.date_input(
                    "Tahakkuk Tarihi ✱",
                    value=bugun, key="tp_tarih",
                )
            with pc2:
                t_son = st.date_input(
                    "Son Ödeme Tarihi ✱",
                    value=bugun + datetime.timedelta(days=10),
                    key="tp_son",
                )
                t_acik_ek = st.text_input(
                    "Açıklama Eki",
                    value="Aidat Ödemesi",
                    key="tp_acik_ek",
                    help="Tahakkuk tarihindeki ay adı otomatik eklenir.",
                )

            # ── Akıllı açıklama önizlemesi ────────────────────────────
            onizleme_aciklama = _otomatik_aciklama(t_tahakkuk, t_acik_ek)
            st.info(f"Oluşturulacak açıklama: **{onizleme_aciklama}**")

            st.divider()

            # ── Gecikme Faizi Ayarları ────────────────────────────────
            with st.container(border=True):
                st.markdown("##### Gecikme Faizi Ayarları")
                fc1, fc2 = st.columns([1, 2])
                with fc1:
                    t_faiz_uygula = st.toggle(
                        "Gecikme faizi uygula",
                        value=False, key="tp_faiz_toggle",
                        help="Aktifse vade geçtikten sonra her gün basit faiz işlenir.",
                    )
                with fc2:
                    t_yillik_faiz = st.number_input(
                        "Yıllık Faiz Oranı (%)",
                        min_value=0.0, max_value=500.0,
                        value=0.0, step=1.0, format="%.2f",
                        key="tp_faiz_oran",
                        disabled=not t_faiz_uygula,
                        help="Örn: 60 → %60 yıllık basit faiz (günlük: 60/365).",
                    )

                if t_faiz_uygula and t_yillik_faiz > 0:
                    _faiz_aciklamasi_goster(t_yillik_faiz, t_son)
                elif t_faiz_uygula and t_yillik_faiz <= 0:
                    st.warning("Faiz uygulamak için yıllık oranı sıfırdan büyük girin.")

            st.divider()

            # ── Muafiyet seçimi ───────────────────────────────────────
            muaf_etiketler = st.multiselect(
                "Muaf Tutulacak Daireler",
                options=tum_etiketler,
                default=[],
                key="tp_muaf",
                help="Seçilen dairelere bu dönem borç kaydı oluşturulmaz.",
                placeholder="Muaf tutmak istediğiniz daireleri seçin…",
            )
            muaf_konumlar = {etiket_harita[e] for e in muaf_etiketler if e in etiket_harita}
            aktif_daire_say = len(sakin_listesi) - len(muaf_konumlar)

            # ── Özet metrik ───────────────────────────────────────────
            sm1, sm2, sm3 = st.columns(3)
            sm1.metric("Toplam Kayıtlı Daire", len(sakin_listesi))
            sm2.metric("Muaf Daire",            len(muaf_konumlar))
            sm3.metric("Borçlandırılacak",      aktif_daire_say)

            if aktif_daire_say > 0 and t_aidat > 0:
                st.caption(
                    f"Tahmini Toplam Tahakkuk: "
                    f"**{aktif_daire_say} × {t_aidat:,.2f} ₺ = "
                    f"{aktif_daire_say * t_aidat:,.2f} ₺**"
                )

            st.divider()
            btn_toplu = st.button(
                "Toplu Borçlandır",
                type="primary", use_container_width=True,
                key="btn_toplu",
            )

        # ── Toplu yazım işlemi ────────────────────────────────────────
        if btn_toplu:
            if t_aidat <= 0:
                st.error("Aidat tutarı sıfırdan büyük olmalıdır.")
            elif not sakin_listesi:
                st.error("Sistemde kayıtlı sakin yok; önce sakin ekleyin.")
            elif t_son < t_tahakkuk:
                st.error("Son ödeme tarihi, tahakkuk tarihinden önce olamaz.")
            else:
                aciklama_son = onizleme_aciklama
                tarih_str    = t_tahakkuk.isoformat()
                son_str      = t_son.isoformat()
                faiz_int     = 1 if t_faiz_uygula and t_yillik_faiz > 0 else 0
                faiz_oran    = float(t_yillik_faiz) if faiz_int else 0.0

                conn = sqlite3.connect(db_yolu)
                cur  = conn.cursor()
                islenen = 0
                try:
                    for blok, dno, _ in sakin_listesi:
                        if (blok, dno) in muaf_konumlar:
                            continue
                        _aidat_ekle(cur, blok, dno, tarih_str,
                                    float(t_aidat), aciklama_son,
                                    son_str, faiz_int, faiz_oran)
                        islenen += 1
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Kayıt hatası: {e}")
                    islenen = 0
                finally:
                    conn.close()

                if islenen > 0:
                    faiz_notu = (
                        f" | Yıllık **%{faiz_oran:.0f}** gecikme faizi aktif."
                        if faiz_int else ""
                    )
                    st.success(
                        f"**{islenen}** daireye **{islenen * t_aidat:,.2f} ₺** "
                        f"(*{aciklama_son}*) başarıyla tahakkuk ettirildi.{faiz_notu}"
                    )
                    st.balloons()

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3 — TEKİL BORÇ
    # ══════════════════════════════════════════════════════════════════════
    with tab3:

        sakin_tekil = _sakinleri_yukle(db_yolu)

        if not sakin_tekil:
            st.info("Sistemde kayıtlı sakin yok; önce sakin ekleyin.")
        else:
            tek_harita: dict[str, tuple[str, str]] = {
                _etiket(b, d, m): (b, d) for b, d, m in sakin_tekil
            }

            with st.container(border=True):
                st.markdown("### Tekil Borç / Özel Tahakkuk")
                st.caption(
                    "Belirli bir daireye, toplu dağıtımdan bağımsız özel tutar ve "
                    "açıklamayla borç kaydı oluşturur."
                )

                # ── Daire seçimi (arama destekli selectbox) ──────────
                tek_secilen = st.selectbox(
                    "Daire Seçin ✱",
                    options=list(tek_harita.keys()),
                    key="tek_daire",
                    placeholder="Arama için yazmaya başlayın…",
                )

                tc1, tc2 = st.columns(2)
                with tc1:
                    tek_tutar = st.number_input(
                        "Borç Tutarı (₺) ✱",
                        min_value=0.0, value=0.0, step=50.0,
                        format="%.2f", key="tek_tutar",
                    )
                    tek_aciklama = st.text_input(
                        "Borç Açıklaması ✱",
                        key="tek_aciklama",
                        placeholder="Örn: Ağustos 2026 Aidatı",
                    )
                with tc2:
                    tek_tahakkuk = st.date_input(
                        "Tahakkuk Tarihi ✱",
                        value=bugun, key="tek_tarih",
                    )
                    tek_son = st.date_input(
                        "Son Ödeme Tarihi ✱",
                        value=bugun + datetime.timedelta(days=10),
                        key="tek_son",
                    )

                # ── Faiz bölümü ───────────────────────────────────────
                st.divider()
                with st.container(border=True):
                    st.markdown("##### Gecikme Faizi")
                    tf1, tf2 = st.columns([1, 2])
                    with tf1:
                        tek_faiz_ac = st.toggle(
                            "Faiz uygula",
                            value=False, key="tek_faiz_toggle",
                        )
                    with tf2:
                        tek_yillik = st.number_input(
                            "Yıllık Faiz Oranı (%)",
                            min_value=0.0, max_value=500.0,
                            value=0.0, step=1.0, format="%.2f",
                            key="tek_faiz_oran",
                            disabled=not tek_faiz_ac,
                        )

                    if tek_faiz_ac and tek_yillik > 0:
                        _faiz_aciklamasi_goster(tek_yillik, tek_son)
                    elif tek_faiz_ac:
                        st.warning("Faiz için yıllık oranı girin.")

                    # Anlık faiz simülasyonu (doldurulan tutar varsa)
                    if tek_faiz_ac and tek_yillik > 0 and tek_tutar > 0:
                        sim = faiz_hesapla(tek_tutar, tek_yillik, tek_son.isoformat())
                        if sim["gecikme_gun"] > 0:
                            st.markdown(
                                f"**Bugün itibarıyla:** Ana Para **{tek_tutar:,.2f} ₺** + "
                                f"Faiz **{sim['faiz_tutari']:,.2f} ₺** = "
                                f"Toplam **{sim['toplam_borc']:,.2f} ₺** "
                                f"({sim['gecikme_gun']} gün gecikme)"
                            )

                st.divider()
                btn_tekil = st.button(
                    "Tekil Borcu Kaydet",
                    type="primary", use_container_width=True,
                    key="btn_tekil",
                )

            # ── Tekil yazım ───────────────────────────────────────────
            if btn_tekil:
                acik_k = (tek_aciklama or "").strip()
                if tek_tutar <= 0:
                    st.error("Borç tutarı sıfırdan büyük olmalıdır.")
                elif not acik_k:
                    st.error("Borç açıklaması zorunludur.")
                elif tek_son < tek_tahakkuk:
                    st.error("Son ödeme tarihi, tahakkuk tarihinden önce olamaz.")
                else:
                    b, d = tek_harita[tek_secilen]
                    faiz_int  = 1 if tek_faiz_ac and tek_yillik > 0 else 0
                    faiz_oran = float(tek_yillik) if faiz_int else 0.0

                    conn = sqlite3.connect(db_yolu)
                    cur  = conn.cursor()
                    try:
                        _aidat_ekle(
                            cur, b, d,
                            tek_tahakkuk.isoformat(),
                            float(tek_tutar),
                            acik_k,
                            tek_son.isoformat(),
                            faiz_int, faiz_oran,
                        )
                        conn.commit()
                        faiz_notu = (
                            f" (Yıllık %{faiz_oran:.0f} gecikme faizi aktif)"
                            if faiz_int else ""
                        )
                        st.success(
                            f"**{tek_secilen}** için **{tek_tutar:,.2f} ₺** "
                            f"(*{acik_k}*) borç kaydı oluşturuldu.{faiz_notu}"
                        )
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Kayıt hatası: {e}")
                    finally:
                        conn.close()
