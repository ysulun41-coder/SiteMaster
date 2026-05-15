import streamlit as st
import sqlite3
import datetime
import pandas as pd
from utils import render_header, get_conn

def goster(db_yolu):
    render_header("💳 Gider Girişi ve Ödeme Tutanağı")
    
    # Veritabanına yeni sütunları (firma_kisi ve tc_no) otomatik ekleyelim (Eski veriler bozulmaz)
    conn = get_conn(db_yolu)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE giderler ADD COLUMN firma_kisi TEXT")
        c.execute("ALTER TABLE giderler ADD COLUMN tc_no TEXT")
        conn.commit()
    except:
        pass # Zaten varsa hata vermez

    # --- ÖDEME TUTANAĞI / MAKBUZ GÖSTERİM ALANI ---
    if 'gider_makbuz' in st.session_state:
        st.success("✅ Gider kaydı ve tutanak hazır!")
        m = st.session_state.gider_makbuz
        
        tutanak_metni = f"""
============================================================
                🏢 SİTEMASTER ÖDEME TUTANAĞI
============================================================
TARİH           : {m['tarih']}
KATEGORİ        : {m['kategori']}
AÇIKLAMA        : {m['aciklama']}
------------------------------------------------------------
ÖDEME YAPILAN   : {m['firma_kisi']}
TC KİMLİK NO    : {m['tc_no'] if m['tc_no'] else '-------'}
------------------------------------------------------------
ÖDENEN TUTAR    : {m['tutar']:.2f} ₺
Yalnızca        : #{m['tutar']:.2f}# Türk Lirasıdır.
------------------------------------------------------------
Yukarıda belirtilen iş/hizmet karşılığı olan tutarı 
tam ve eksiksiz olarak teslim aldım.

         TESLİM EDEN                     TESLİM ALAN
       (Site Yönetimi)                 (Ad Soyad / İmza)

    ......................             ......................
============================================================
        """
        st.code(tutanak_metni, language="text")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button("📥 Tutanağı İndir (Txt)", data=tutanak_metni, file_name=f"Gider_Tutanagi_{m['firma_kisi']}.txt", mime="text/plain", use_container_width=True)
        with col_d2:
            if st.button("🔄 Yeni Gider Gir", use_container_width=True):
                del st.session_state.gider_makbuz
                st.rerun()
        st.divider()

    # --- GİDER GİRİŞ FORMU ---
    with st.form("gider_form", clear_on_submit=True):
        st.markdown("##### ➕ Harcama Detayları")
        c1, c2 = st.columns(2)
        with c1:
            firma_kisi = st.text_input("Ödeme Yapılan Firma veya Şahıs Adı")
            tc_no = st.text_input("Şahıs ise TC Kimlik No (Opsiyonel)", max_chars=11)
            kat = st.selectbox("Harcama Kategorisi", ["Elektrik", "Su", "Maaş", "Bakım / Onarım", "Peyzaj / Ot Biçme", "Temizlik", "Demirbaş", "Diğer"])
        with c2:
            t = st.number_input("Ödenen Tutar (₺)", min_value=0.0)
            harcama_tarihi = st.date_input("Harcama Tarihi", datetime.date.today())
            a = st.text_input("Gider Açıklaması (Örn: Bahçe otlarının biçilmesi)")
            
        if st.form_submit_button("💳 Harcamayı Kaydet ve Tutanak Bas", type="primary"):
            if t > 0 and firma_kisi:
                conn = get_conn(db_yolu)
                c = conn.cursor()
                c.execute("""INSERT INTO giderler (tarih, kategori, tutar, aciklama, firma_kisi, tc_no) 
                             VALUES (?,?,?,?,?,?)""", 
                          (str(harcama_tarihi), kat, t, a, firma_kisi, tc_no))
                conn.commit()
                conn.close()
                
                # Tutanak için verileri session_state'e atalım
                st.session_state.gider_makbuz = {
                    "tarih": harcama_tarihi.strftime("%d.%m.%Y"),
                    "kategori": kat,
                    "tutar": t,
                    "aciklama": a,
                    "firma_kisi": firma_kisi,
                    "tc_no": tc_no
                }
                st.rerun()
            else:
                st.error("Lütfen Firma/Kişi adı ve tutarı boş bırakmayın!")
    
    st.divider()
    st.markdown("##### 📜 Son Harcamalar")
    conn = get_conn(db_yolu)
    # Listeyi güncellenmiş haliyle (Firma adıyla) gösterelim
    df_g = pd.read_sql_query("""SELECT tarih as Tarih, firma_kisi as 'Ödenen Yer/Kişi', 
                                kategori as Kategori, tutar as 'Tutar (₺)', aciklama as Açıklama 
                                FROM giderler ORDER BY id DESC LIMIT 15""", conn)
    conn.close()
    if not df_g.empty: 
        st.dataframe(df_g, use_container_width=True, hide_index=True)

