import streamlit as st
import pandas as pd
import sqlite3
import datetime

def goster(db_yolu, aktif_site):
    st.subheader("💰 Tahsilat ve Makbuz Kesimi")
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
        with col_m1: st.download_button("📥 Makbuzu İndir (Txt)", data=makbuz_metni, file_name="Makbuz.txt", mime="text/plain", use_container_width=True)
        with col_m2:
            if st.button("🔄 Yeni İşlem Yap", use_container_width=True):
                del st.session_state.makbuz_data
                st.rerun()
        st.divider()

    conn = sqlite3.connect(db_yolu)
    df_b = pd.read_sql_query("SELECT id, blok, daire_no, aciklama, tutar FROM aidatlar WHERE durum='Ödenmedi'", conn)
    if not df_b.empty:
        st.dataframe(df_b.drop(columns=['id']), use_container_width=True, hide_index=True)
        borclar = {f"{r[1]} Blok No:{r[2]} | {r[3]} ({r[4]}₺)": r[0] for r in df_b.values}
        with st.form("t_form"):
            secili = st.selectbox("Tahsil Edilecek Kayıt", list(borclar.keys()))
            if st.form_submit_button("✅ Tahsil Et ve Makbuz Kes", type="primary"):
                c = conn.cursor()
                c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (borclar[secili],))
                conn.commit()
                st.session_state.makbuz_data = secili
                st.rerun()
    else: st.success("Bekleyen borç yok.")
    conn.close()
