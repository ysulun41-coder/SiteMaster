import streamlit as st
import sqlite3
import datetime

def goster(db_yolu):
    st.subheader("💰 Borçlandırma ve Otomatik Aidat Sistemi")
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Otomatik Aidat Talimatı", "🔄 Toplu Tahakkuk", "🎯 Tekil Borç"])

    # --- TAB 1: OTOMATİK TALİMAT AYARI ---
    with tab1:
        st.markdown("#### 🤖 Her Ay Otomatik Dağıtım")
        st.write("Burada bir miktar belirlerseniz, sistem her ayın 1'inde tüm sakinleri otomatik borçlandırır.")
        
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT tutar, aciklama, durum FROM otomatik_talimatlar WHERE id=1")
        mevcut_talimat = c.fetchone()
        
        with st.form("otomatik_ayar_form"):
            tutar = st.number_input("Aylık Sabit Aidat Tutarı (₺)", 
                                    value=mevcut_talimat[0] if mevcut_talimat else 0.0, step=100.0)
            aciklama = st.text_input("Açıklama Taslağı (Örn: Aidat Ödemesi)", 
                                     value=mevcut_talimat[1] if mevcut_talimat else "Aidat Ödemesi")
            durum = st.toggle("Otomatik Dağıtım Aktif", value=bool(mevcut_talimat[2]) if mevcut_talimat else False)
            
            if st.form_submit_button("Talimatı Kaydet / Güncelle"):
                if mevcut_talimat:
                    c.execute("UPDATE otomatik_talimatlar SET tutar=?, aciklama=?, durum=? WHERE id=1", 
                              (tutar, aciklama, 1 if durum else 0))
                else:
                    c.execute("INSERT INTO otomatik_talimatlar (tutar, aciklama, durum) VALUES (?,?,?)", 
                              (tutar, aciklama, 1 if durum else 0))
                conn.commit()
                st.success("✅ Otomatik aidat talimatı başarıyla güncellendi!")
        conn.close()

    # --- DİĞER TABLAR (TOPLU VE TEKİL) ÖNCEKİ KODUN AYNI KALABİLİR ---
    # ... (Önceki borclandirma.py kodlarını buraya ekleyebilirsin)
