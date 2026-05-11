# tahsilat.py DOSYASI
import streamlit as st
import pandas as pd
import sqlite3
import datetime

def tahsilat_ekrani(db_yolu, aktif_site):
    st.subheader("💰 Tahsilat ve Makbuz Kesimi")
    
    # Makbuz Gösterme Kısmı
    if 'makbuz_data' in st.session_state:
        st.success("✅ Tahsilat başarıyla kaydedildi!")
        makbuz_metni = f"""
====================================
 🏢 SİTEMASTER TAHSİLAT MAKBUZU
====================================
Site Adı    : {aktif_site}
İşlem Tarihi: {datetime.date.today().strftime("%d.%m.%Y")}
------------------------------------
TAHSİLAT BİLGİSİ:
{st.session_state.makbuz_data}

Durum       : ÖDENDİ (Tahsil Edildi)
====================================
Bizi tercih ettiğiniz için teşekkürler.
        """
        st.code(makbuz_metni, language="text")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.download_button("📥 Makbuzu İndir (Txt)", data=makbuz_metni, file_name="Makbuz.txt", mime="text/plain", use_container_width=True)
        with col_m2:
            if st.button("🔄 Yeni İşlem Yap", use_container_width=True):
                del st.session_state.makbuz_data
                st.rerun()
        st.divider()

    # Tahsilat Alma Formu
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    c.execute("SELECT id, blok, daire_no, aciklama, tutar FROM aidatlar WHERE durum='Ödenmedi'")
    odenmemis_listesi = c.fetchall()
    
    if odenmemis_listesi:
        df_b = pd.DataFrame(odenmemis_listesi, columns=['id', 'Blok', 'Daire No', 'Açıklama', 'Tutar (₺)'])
        st.dataframe(df_b.drop(columns=['id']), use_container_width=True, hide_index=True)
        borc_secenekleri = {f"{r[1]} Blok No: {r[2]} | {r[3]} ({r[4]:.2f} ₺)": r[0] for r in odenmemis_listesi}
        
        with st.form("tahsilat_yap_form"):
            secilen_borc_metin = st.selectbox("Ödeme Alınacak Kayıt", list(borc_secenekleri.keys()))
            if st.form_submit_button("✅ Ödemeyi Al ve Makbuz Kes", type="primary"):
                borc_id = borc_secenekleri[secilen_borc_metin]
                c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (borc_id,))
                conn.commit()
                conn.close()
                st.session_state.makbuz_data = secilen_borc_metin
                st.rerun()
    else: 
        st.success("Ödenmemiş borç yok!")
        conn.close()
