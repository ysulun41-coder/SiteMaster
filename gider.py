import streamlit as st
import sqlite3
import datetime
import pandas as pd
from utils import (
    render_header,
    get_conn,
    get_site_bilgi,
    makbuz_metni_olustur,
    makbuz_html_olustur,
    render_makbuz_karti,
    render_makbuz_indir_butonlari,
    tarih_input,
)

MASTER_DB = "master.db"


def _gider_tutanak_govde(m: dict) -> str:
    tc = m["tc_no"] if m.get("tc_no") else "—"
    return f"""KATEGORİ        : {m['kategori']}
AÇIKLAMA        : {m['aciklama']}
------------------------------------------------------------
ÖDEME YAPILAN   : {m['firma_kisi']}
TC KİMLİK NO    : {tc}
------------------------------------------------------------
ÖDENEN TUTAR    : {m['tutar']:.2f} ₺
Yalnızca        : #{m['tutar']:.2f}# Türk Lirasıdır.
------------------------------------------------------------
Yukarıda belirtilen iş/hizmet karşılığı tutarı
tam ve eksiksiz olarak teslim aldım."""


def _gider_imza_html() -> str:
    return """
    <div class="imza">
      <p>Yukarıda belirtilen iş/hizmet karşılığı olan tutarı tam ve eksiksiz olarak teslim aldım.</p>
      <div class="imza-row">
        <div class="imza-kutu">
          <div>TESLİM EDEN</div>
          <div class="imza-cizgi"></div>
          <div>Site Yönetimi</div>
        </div>
        <div class="imza-kutu">
          <div>TESLİM ALAN</div>
          <div class="imza-cizgi"></div>
          <div>Ad Soyad / İmza</div>
        </div>
      </div>
    </div>
    """


def goster(db_yolu, aktif_site, master_db_yolu: str = MASTER_DB):
    render_header("💳 Gider Girişi ve Ödeme Tutanağı")

    conn = get_conn(db_yolu)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE giderler ADD COLUMN firma_kisi TEXT")
        c.execute("ALTER TABLE giderler ADD COLUMN tc_no TEXT")
        conn.commit()
    except Exception:
        pass

    if "gider_makbuz" in st.session_state:
        st.success("✅ Gider kaydı ve tutanak hazır!")
        m = st.session_state.gider_makbuz
        site = get_site_bilgi(master_db_yolu, aktif_site) or {"site_adi": aktif_site}
        govde = _gider_tutanak_govde(m)

        tutanak_metni = makbuz_metni_olustur(
            site,
            baslik="ÖDEME TUTANAĞI",
            islem_tarihi=m["tarih"],
            govde=govde,
            alt_not="Bu belge SiteMaster üzerinden üretilmiştir.",
            durum_satir="Ödeme yapıldı — tutanak düzenlendi",
        )

        tutanak_html = makbuz_html_olustur(
            site,
            baslik="ÖDEME TUTANAĞI",
            islem_tarihi=m["tarih"],
            detay_satirlari=[
                ("Kategori", m["kategori"]),
                ("Açıklama", m["aciklama"]),
                ("Ödeme yapılan", m["firma_kisi"]),
                ("TC Kimlik No", m["tc_no"] or "—"),
                ("Ödenen tutar", f"{m['tutar']:.2f} ₺"),
            ],
            durum_metin="Ödeme yapıldı — tutanak düzenlendi",
            imza_html=_gider_imza_html(),
            alt_not="Belgeyi yazdırmak için logolu HTML dosyasını indirin (Ctrl+P).",
        )

        render_makbuz_karti(site, tutanak_metni, html_onizleme=tutanak_html)

        dosya_oneki = f"Gider_Tutanagi_{m['firma_kisi'].replace(' ', '_')}_{m['tarih'].replace('.', '-')}"
        render_makbuz_indir_butonlari(
            txt_icerik=tutanak_metni,
            html_icerik=tutanak_html,
            dosya_oneki=dosya_oneki,
        )
        if st.button("🔄 Yeni Gider Gir", use_container_width=True, key="gider_yeni"):
            del st.session_state.gider_makbuz
            st.rerun()
        st.divider()

    with st.form("gider_form", clear_on_submit=True):
        st.markdown("##### ➕ Harcama Detayları")
        c1, c2 = st.columns(2)
        with c1:
            firma_kisi = st.text_input("Ödeme Yapılan Firma veya Şahıs Adı")
            tc_no = st.text_input("Şahıs ise TC Kimlik No (Opsiyonel)", max_chars=11)
            kat = st.selectbox(
                "Harcama Kategorisi",
                ["Elektrik", "Su", "Maaş", "Bakım / Onarım", "Peyzaj / Ot Biçme", "Temizlik", "Demirbaş", "Diğer"],
            )
        with c2:
            t = st.number_input("Ödenen Tutar (₺)", min_value=0.0)
            harcama_tarihi = tarih_input("Harcama Tarihi", datetime.date.today(), key="gider_tarih")
            a = st.text_input("Gider Açıklaması (Örn: Bahçe otlarının biçilmesi)")

        if st.form_submit_button("💳 Harcamayı Kaydet ve Tutanak Bas", type="primary"):
            if t > 0 and firma_kisi:
                c.execute(
                    """INSERT INTO giderler (tarih, kategori, tutar, aciklama, firma_kisi, tc_no)
                       VALUES (?,?,?,?,?,?)""",
                    (str(harcama_tarihi), kat, t, a, firma_kisi, tc_no),
                )
                conn.commit()

                st.session_state.gider_makbuz = {
                    "tarih": harcama_tarihi.strftime("%d.%m.%Y"),
                    "kategori": kat,
                    "tutar": t,
                    "aciklama": a,
                    "firma_kisi": firma_kisi,
                    "tc_no": tc_no,
                }
                st.rerun()
            else:
                st.error("Lütfen Firma/Kişi adı ve tutarı boş bırakmayın!")

    st.divider()
    st.markdown("##### 📜 Son Harcamalar")
    df_g = pd.read_sql_query(
        """SELECT tarih as Tarih, firma_kisi as 'Ödenen Yer/Kişi',
                  kategori as Kategori, tutar as 'Tutar (₺)', aciklama as Açıklama
           FROM giderler ORDER BY id DESC LIMIT 15""",
        conn,
    )
    conn.close()
    if not df_g.empty:
        st.dataframe(df_g, use_container_width=True, hide_index=True)
