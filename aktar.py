"""
SiteMaster – Arşiv & Veri Aktarım Merkezi
Eski sistemden alınan Excel'i sakinler tablosuna güvenle aktarır.
"""

from __future__ import annotations

import io
import sqlite3
from typing import Any

import pandas as pd
import streamlit as st

# Hiçbir sütunla eşleştirilmediğini belirten sabit
YOK = "── SÜTUN YOK / BOŞ BIRAK ──"

# Şablon Excel sütun başlıkları
SABLON_SUTUNLAR = [
    "Blok", "Daire_No", "Malik_Ad", "Malik_TC", "Malik_Tel",
    "Kiraci_Ad", "Kiraci_TC", "Kiraci_Tel", "Plaka", "Sifre",
]

# Şifre politikası seçenekleri
POL_EXCEL   = "Excel şifre sütununu kullan (boşsa 1234)"
POL_FORMAT  = "Site formatı: {blok}{daire}-{ek}  (manuel kayıtla aynı)"
POL_TAMHALI = "Tam şifre tek sütunda – arşivdeki gibi aynen al"

# Çift kayıt politikası seçenekleri
CIFT_ATLA   = "Yalnızca yeni kayıt ekle – mevcut daireleri atla"
CIFT_GUNCELLE = "Mevcut kaydı Excel satırıyla güncelle"


# ─── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _sutun_opts(df: pd.DataFrame) -> list[str]:
    return [YOK] + df.columns.tolist()


def _hucre(satir: pd.Series, sutun: str) -> str:
    """Hücreyi oku, normalize et, boş string döndür."""
    if sutun == YOK:
        return ""
    val = satir.get(sutun, "")
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", ""):
        return ""
    # Excel bazen tamsayıları 12.0 olarak yazar; düzelt
    if s.endswith(".0") and s[:-2].lstrip("-").isdigit():
        s = s[:-2]
    return s


def _sifre_uret(politika: str, blok: str, daire: str,
                sifre_excel: str, sifre_ek: str) -> str:
    if politika == POL_TAMHALI:
        return sifre_excel or "1234"
    if politika == POL_FORMAT:
        ek = sifre_ek or sifre_excel or "1234"
        return f"{blok}{daire}-{ek}"
    # POL_EXCEL (varsayılan)
    return sifre_excel or "1234"


def _mevcut_bloklar(db_yolu: str) -> set[str]:
    try:
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT blok_adi FROM bloklar")
        return {str(r[0]).strip() for r in c.fetchall() if r[0]}
    except Exception:
        return set()
    finally:
        conn.close()


def _satiri_isle(satir: pd.Series, sec: dict[str, str]) -> dict[str, str]:
    return {
        "blok":      _hucre(satir, sec["blok"]),
        "daire_no":  _hucre(satir, sec["daire"]),
        "malik_ad":  _hucre(satir, sec["m_ad"]),
        "malik_tc":  _hucre(satir, sec["m_tc"]),
        "malik_tel": _hucre(satir, sec["m_tel"]),
        "kiraci_ad": _hucre(satir, sec["k_ad"]),
        "kiraci_tc": _hucre(satir, sec["k_tc"]),
        "kiraci_tel":_hucre(satir, sec["k_tel"]),
        "plaka":     _hucre(satir, sec["plaka"]),
        "sifre_ham": _hucre(satir, sec["sifre"]),
        "sifre_ek":  _hucre(satir, sec["sifre_ek"]),
    }


def _excel_satirlarini_coz(
    df: pd.DataFrame,
    sec: dict[str, str],
) -> tuple[list[tuple[int, dict[str, str]]], int, list[dict[str, Any]]]:
    """
    DataFrame'i satır satır işler.
    - Blok veya daire boşsa atlar (atlanan sayısını tutar).
    - Aynı blok+daire Excel içinde tekrar ederse son satır geçerli, öncekiler notlara iner.
    Döndürür: (işlenecek_satirlar, atlanan_bos, ic_notlar)
    """
    by_key: dict[tuple[str, str], tuple[int, dict[str, str]]] = {}
    atlanan = 0
    notlar: list[dict[str, Any]] = []

    for i, (_, satir) in enumerate(df.iterrows()):
        excel_no = i + 2  # başlık satırı = 1
        alan = _satiri_isle(satir, sec)

        if not alan["blok"] or not alan["daire_no"]:
            atlanan += 1
            continue

        anahtar = (alan["blok"], alan["daire_no"])
        if anahtar in by_key:
            notlar.append({
                "Excel Satırı": by_key[anahtar][0],
                "Blok": alan["blok"],
                "Daire": alan["daire_no"],
                "Not": "Excel içinde aynı blok+daire tekrar etti; son satır kullanıldı.",
            })
        by_key[anahtar] = (excel_no, alan)

    return list(by_key.values()), atlanan, notlar


def _sablon_indir() -> bytes:
    """Boş şablon Excel oluştur ve bytes döndür."""
    df_sablon = pd.DataFrame(columns=SABLON_SUTUNLAR)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_sablon.to_excel(writer, index=False, sheet_name="Sakinler")
    return buf.getvalue()


# ─── Ana ekran ────────────────────────────────────────────────────────────────

def goster(db_yolu: str) -> None:

    st.subheader("📥 Arşiv & Veri Aktarım Merkezi")

    # ── Üst bilgi + şablon indirme ──
    with st.container(border=True):
        ic1, ic2 = st.columns([3, 1])
        with ic1:
            st.markdown(
                "Eski yönetim veya muhasebe sisteminizden dışa aktardığınız "
                "**Excel (.xlsx)** dosyasını buradan içe alın. "
                "Sütun adları ne olursa olsun eşleştirebilirsiniz."
            )
            st.caption(
                "Çift kayıt politikasını seçin, şifre stratejisini belirleyin, "
                "gerekirse kuru çalıştırmayla önce sonucu görün."
            )
        with ic2:
            st.download_button(
                label="Şablon .xlsx indir",
                data=_sablon_indir(),
                file_name="sitemaster_sablon.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Boş şablon; verilerinizi bu formata kopyalayarak aktarabilirsiniz.",
            )

    st.divider()

    # ── ADIM 1: Dosya yükleme ──
    with st.container(border=True):
        st.markdown("#### Adım 1 — Excel dosyasını yükleyin")
        yuklenen = st.file_uploader(
            "**.xlsx** dosyası seçin",
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

    # ── ADIM 2: Aktarım kuralları ──
    with st.container(border=True):
        st.markdown("#### Adım 2 — Aktarım kurallarını belirleyin")
        kural_c1, kural_c2 = st.columns(2)

        with kural_c1:
            cift_politikasi = st.radio(
                "Aynı blok + daire sistemde zaten varsa:",
                (CIFT_ATLA, CIFT_GUNCELLE),
                index=0,
                help=(
                    "Arşiv genelde bir kez yüklenir → 'Atla' seçin. "
                    "Bilgileri tazelemek için tekrar yüklerseniz → 'Güncelle' seçin."
                ),
            )

        with kural_c2:
            sifre_politikasi = st.radio(
                "Sakin giriş şifresi nasıl oluşturulsun?",
                (POL_EXCEL, POL_FORMAT, POL_TAMHALI),
                index=0,
                help=(
                    f"'{POL_FORMAT}' seçilirse şifre eki sütununu da eşleştirin."
                ),
            )

        kural_c3, kural_c4 = st.columns(2)
        with kural_c3:
            blok_uyari_ac = st.checkbox(
                "Tanınmayan blok adlarında uyar",
                value=True,
                help="Site kurulumunda tanımlı bloklar dışında bir ad gelirse tablo olarak gösterilir.",
            )
        with kural_c4:
            kuru_calistir = st.checkbox(
                "Kuru çalıştır (veritabanına yazma)",
                value=False,
                help="Sadece ne yazılacağını önizler; gerçek aktarım için bu kutuyu boş bırakın.",
            )

        if sifre_politikasi == POL_FORMAT:
            st.info(
                "**Site formatı seçildi:** Şifre `{blok}{daire}-{ek}` biçiminde oluşturulur. "
                "Aşağıda 'Şifre Eki' sütununu eşleştirmeyi unutmayın. "
                "Ek boşsa otomatik **1234** kullanılır."
            )

    st.divider()

    # ── ADIM 3: Sütun eşleştirme ──
    opts = _sutun_opts(df)
    bilinen_bloklar = _mevcut_bloklar(db_yolu)

    with st.container(border=True):
        st.markdown("#### Adım 3 — Sütunları eşleştirin")
        st.caption("Sistemin ihtiyaç duyduğu her alan için Excel'deki karşılık sütununu seçin. Bilgi yoksa boş bırakın.")

        with st.form("aktar_eslestirme_formu"):
            f_c1, f_c2, f_c3 = st.columns(3)

            with f_c1:
                st.markdown("**Temel Bilgiler**")
                sec_blok   = st.selectbox("Blok / Apartman adı ✱", opts, key="f_blok")
                sec_daire  = st.selectbox("Daire / Kapı no ✱",    opts, key="f_daire")
                sec_plaka  = st.selectbox("Araç plakası",          opts, key="f_plaka")
                st.markdown("**Şifre**")
                sec_sifre    = st.selectbox("Şifre sütunu",        opts, key="f_sifre",
                                            help="Tam şifre ya da şifre eki; politikaya göre kullanılır.")
                sec_sifre_ek = st.selectbox("Şifre eki (site formatı için)", opts, key="f_sifre_ek",
                                            help="Yalnızca 'Site formatı' politikasında gereklidir.")

            with f_c2:
                st.markdown("**Kat Maliki**")
                sec_m_ad  = st.selectbox("Malik adı soyadı", opts, key="f_m_ad")
                sec_m_tc  = st.selectbox("Malik TC kimlik",  opts, key="f_m_tc")
                sec_m_tel = st.selectbox("Malik telefon",    opts, key="f_m_tel")

            with f_c3:
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

    # Zorunlu alan kontrolü
    if sec_blok == YOK or sec_daire == YOK:
        st.error("**Blok** ve **Daire No** sütunları zorunludur; lütfen eşleştirin.")
        return

    sec_map = {
        "blok": sec_blok, "daire": sec_daire,
        "sifre": sec_sifre, "sifre_ek": sec_sifre_ek,
        "plaka": sec_plaka,
        "m_ad": sec_m_ad, "m_tc": sec_m_tc, "m_tel": sec_m_tel,
        "k_ad": sec_k_ad, "k_tc": sec_k_tc, "k_tel": sec_k_tel,
    }

    # ── Ön işleme: Excel satırlarını çöz ──
    with st.spinner("Excel satırları analiz ediliyor..."):
        satirlar, atlanan_bos, ic_notlar = _excel_satirlarini_coz(df, sec_map)

    guncelle_modu = cift_politikasi == CIFT_GUNCELLE

    # ── Veritabanı ön kontrol (hangi satırlar yazılacak?) ──
    eklenecek:   list[tuple[dict[str, str], str, int]] = []
    atlanan_db:  list[dict[str, Any]] = []
    uyari_blok:  list[dict[str, Any]] = []
    notlar_list: list[dict[str, Any]] = list(ic_notlar)

    try:
        kon = sqlite3.connect(db_yolu)
        cur = kon.cursor()
        for excel_no, alan in satirlar:
            blok, daire = alan["blok"], alan["daire_no"]

            if blok_uyari_ac and bilinen_bloklar and blok not in bilinen_bloklar:
                uyari_blok.append({
                    "Excel Satırı": excel_no,
                    "Blok": blok,
                    "Daire": daire,
                    "Uyarı": f"'{blok}' bloku site kurulumunda tanımlı değil.",
                })

            sifre = _sifre_uret(sifre_politikasi, blok, daire,
                                alan["sifre_ham"], alan["sifre_ek"])

            cur.execute("SELECT id FROM sakinler WHERE blok=? AND daire_no=?", (blok, daire))
            mevcut = cur.fetchone()

            if mevcut and not guncelle_modu:
                atlanan_db.append({
                    "Excel Satırı": excel_no,
                    "Blok": blok,
                    "Daire": daire,
                    "Sebep": "Sistemde kayıt var; politika 'atla' olduğundan yazılmadı.",
                })
                continue

            eklenecek.append((alan, sifre, excel_no))
    except Exception as e:
        st.error(f"Veritabanı ön kontrol hatası: {e}")
        return
    finally:
        kon.close()

    # ── Özet metrikler ──
    st.divider()
    st.markdown("#### Aktarım Özeti")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Yazılacak kayıt",        len(eklenecek))
    m2.metric("Blok/daire boş → atlandı", atlanan_bos)
    m3.metric("Sistemde var → atlandı", len(atlanan_db))
    m4.metric("Excel iç not / uyarı",   len(notlar_list) + len(uyari_blok))

    # Blok uyarıları
    if uyari_blok:
        st.warning(
            f"{len(uyari_blok)} satırda tanınmayan blok adı var. "
            "Aktarım yine de yapılabilir; ancak blok adının doğru olduğundan emin olun."
        )
        with st.expander("Tanınmayan blok adları", expanded=True):
            st.dataframe(pd.DataFrame(uyari_blok), use_container_width=True)

    # Atlanan DB kayıtları
    if atlanan_db:
        with st.expander(f"Sistemde zaten var, atlandı ({len(atlanan_db)} adet)", expanded=False):
            st.dataframe(pd.DataFrame(atlanan_db), use_container_width=True)

    # Excel içi tekrar notları
    if notlar_list:
        with st.expander(f"Excel içi tekrar notları ({len(notlar_list)} adet)", expanded=False):
            st.dataframe(pd.DataFrame(notlar_list), use_container_width=True)

    if not eklenecek:
        st.error(
            "Veritabanına yazılacak satır yok. "
            "Çift kayıt politikasını veya eşleştirmeyi gözden geçirin."
        )
        return

    # ── Kuru çalıştırma önizlemesi ──
    if kuru_calistir:
        st.info(
            f"**Kuru çalıştırma aktif** — veritabanına hiçbir şey yazılmadı. "
            f"Aşağıda yazılacak ilk **{min(20, len(eklenecek))}** kayıt gösteriliyor."
        )
        onizle_rows = []
        for alan, sifre, excel_no in eklenecek[:20]:
            onizle_rows.append({
                "Excel Satırı": excel_no,
                "Blok": alan["blok"],
                "Daire": alan["daire_no"],
                "Malik": alan["malik_ad"],
                "Kiracı": alan["kiraci_ad"],
                "Plaka": alan["plaka"],
                "Şifre (örnek)": sifre if len(sifre) <= 20 else sifre[:20] + "…",
            })
        st.dataframe(pd.DataFrame(onizle_rows), use_container_width=True)
        if len(eklenecek) > 20:
            st.caption(f"… ve {len(eklenecek) - 20} satır daha.")
        st.caption("Kuru modu kapatıp tekrar gönderin; tüm kayıtlar işlenecek.")
        return

    # ── Gerçek yazım ──
    eklenen    = 0
    guncellenen = 0
    yazim_hata: list[dict[str, Any]] = []

    progress = st.progress(0, text="Kayıtlar işleniyor…")
    toplam = len(eklenecek)

    try:
        conn = sqlite3.connect(db_yolu)
        cur  = conn.cursor()

        for idx, (alan, sifre, excel_no) in enumerate(eklenecek):
            blok, daire = alan["blok"], alan["daire_no"]
            try:
                cur.execute(
                    "SELECT id FROM sakinler WHERE blok=? AND daire_no=?",
                    (blok, daire),
                )
                mevcut = cur.fetchone()

                if mevcut and guncelle_modu:
                    cur.execute(
                        """UPDATE sakinler
                           SET malik_ad=?, malik_tc=?, malik_tel=?,
                               kiraci_ad=?, kiraci_tc=?, kiraci_tel=?,
                               plaka=?, sifre=?
                           WHERE blok=? AND daire_no=?""",
                        (
                            alan["malik_ad"],  alan["malik_tc"],  alan["malik_tel"],
                            alan["kiraci_ad"], alan["kiraci_tc"], alan["kiraci_tel"],
                            alan["plaka"],     sifre,
                            blok,              daire,
                        ),
                    )
                    guncellenen += 1

                elif not mevcut:
                    cur.execute(
                        """INSERT INTO sakinler
                           (blok, daire_no,
                            malik_ad,  malik_tc,  malik_tel,
                            kiraci_ad, kiraci_tc, kiraci_tel,
                            plaka,     sifre)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (
                            blok,              daire,
                            alan["malik_ad"],  alan["malik_tc"],  alan["malik_tel"],
                            alan["kiraci_ad"], alan["kiraci_tc"], alan["kiraci_tel"],
                            alan["plaka"],     sifre,
                        ),
                    )
                    eklenen += 1

            except Exception as satir_hata:
                yazim_hata.append({
                    "Excel Satırı": excel_no,
                    "Blok": blok,
                    "Daire": daire,
                    "Hata": str(satir_hata),
                })

            progress.progress(
                int((idx + 1) / toplam * 100),
                text=f"{idx + 1} / {toplam} satır işlendi…",
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

    # ── Sonuç ──
    st.divider()
    if eklenen + guncellenen > 0:
        st.success(
            f"Aktarım tamamlandı:  "
            f"**{eklenen}** yeni kayıt eklendi,  "
            f"**{guncellenen}** kayıt güncellendi.  "
            f"Yazım hatası: **{len(yazim_hata)}**."
        )
        st.balloons()
    else:
        st.warning("Hiçbir kayıt yazılamadı; hata tablosunu inceleyin.")

    if yazim_hata:
        with st.expander(f"Yazım hataları ({len(yazim_hata)} satır)", expanded=True):
            st.dataframe(pd.DataFrame(yazim_hata), use_container_width=True)
            st.download_button(
                label="Hatalı satırları indir (.xlsx)",
                data=_df_to_excel_bytes(pd.DataFrame(yazim_hata)),
                file_name="aktarim_hatali_satirlar.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()
