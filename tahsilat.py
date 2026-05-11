import streamlit as st
import pandas as pd
import sqlite3
import datetime

def goster(db_yolu, aktif_site):
    st.subheader("💰 Tahsilat ve Makbuz Kesimi")
    
    # --- MAKBUZ GÖSTERİM ALANI ---
    if 'makbuz_data' in st.session_state:
        st.success("✅ Tahsilat başarıyla kaydedildi!")
        
        t_tarih = st.session_state.get('tahsilat_tarihi', datetime.date.today().strftime("%d.%m.%Y"))
        
        makbuz_metni = f"""
====================================
 🏢 SİTEMASTER TAHSİLAT MAKBUZU
====================================
Site Adı    : {aktif_site}
İşlem Tarihi: {t_tarih}
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
                if 'tahsilat_tarihi' in st.session_state:
                    del st.session_state.tahsilat_tarihi
                st.rerun()
        st.divider()

    # --- TAHSİLAT LİSTESİ VE FORM (KIRMIZI VE YEŞİL ALAN) ---
    conn = sqlite3.connect(db_yolu)
    
    # SQL JOIN ile aidat tablosuna sakinler tablosundan AD SOYAD çekiyoruz
    query = """
    SELECT 
        a.id, 
        a.blok, 
        a.daire_no, 
        s.malik_ad, 
        a.aciklama, 
        a.tutar 
    FROM aidatlar a
    INNER JOIN sakinler s ON a.blok = s.blok AND a.daire_no = s.daire_no
    WHERE a.durum = 'Ödenmedi'
    """
    df_odenmemis = pd.read_sql_query(query, conn)
    
    if not df_odenmemis.empty:
        # 🔴 KIRMIZI ALAN: Detaylı Liste
        st.markdown("##### 📌 Bekleyen Borçlar Listesi")
        display_df = df_odenmemis.copy()
        display_df.columns = ['ID', 'Blok', 'Daire No', 'Ad Soyad', 'Açıklama', 'Tutar (₺)']
        st.dataframe(display_df.drop(columns=['ID']), use_container_width=True, hide_index=True)
        
        st.divider()
        
        # 🟢 YEŞİL ALAN: Tahsilat Formu
        st.markdown("##### 🧾 Tahsilat İşlemi")
        # Selectbox içinde görünecek havalı metni hazırlıyoruz
        borclar_dict = {
            f"{r['blok']} Blok No:{r['daire_no']} | {r['malik_ad']} | {r['aciklama']} ({r['tutar']:.2f}₺)": r['id'] 
            for _, r in df_odenmemis.iterrows()
        }
        
        with st.form("tahsilat_formu"):
            secilen_metin = st.selectbox("Tahsil Edilecek Kişi ve Borç", list(borclar_dict.keys()))
            tahsilat_tarihi = st.date_input("Tahsilat Tarihi", datetime.date.today())
            
            if st.form_submit_button("✅ Tahsil Et ve Makbuz Oluştur", type="primary"):
                c = conn.cursor()
                borc_id = borclar_dict[secilen_metin]
                
                # Borcu ödendi olarak güncelle
                c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (borc_id,))
                conn.commit()
                
                # Makbuz için bilgileri sakla
                st.session_state.makbuz_data = secilen_metin
                st.session_state.tahsilat_tarihi = tahsilat_tarihi.strftime("%d.%m.%Y")
                st.rerun()
    else: 
        st.success("🎉 Harika! Ödenmemiş aidat borcu bulunmuyor.")
    
    conn.close()
