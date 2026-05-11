import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse

def goster(db_yolu, aktif_site):
    st.subheader("💰 Tahsilat, Faiz ve İletişim Yönetimi")
    
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

    # --- BEKLEYEN BORÇLAR VE GECİKME HESABI ---
    conn = sqlite3.connect(db_yolu)
    
    query = """
    SELECT 
        a.id, a.blok, a.daire_no, s.malik_ad, s.malik_tel, 
        a.aciklama, a.tutar, a.tarih 
    FROM aidatlar a
    INNER JOIN sakinler s ON a.blok = s.blok AND a.daire_no = s.daire_no
    WHERE a.durum = 'Ödenmedi'
    """
    df_odenmemis = pd.read_sql_query(query, conn)
    
    if not df_odenmemis.empty:
        bugun = datetime.date.today()
        
        # Gecikme günlerini hesaplıyoruz
        gecikme_listesi = []
        for index, row in df_odenmemis.iterrows():
            son_odeme = datetime.datetime.strptime(row['tarih'], "%Y-%m-%d").date()
            fark = (bugun - son_odeme).days
            gecikme = fark if fark > 0 else 0
            gecikme_listesi.append(gecikme)
            
        df_odenmemis['Gecikme (Gün)'] = gecikme_listesi
        
        st.markdown("##### 📌 Bekleyen Borçlar ve Gecikme Durumları")
        gosterim_df = df_odenmemis[['blok', 'daire_no', 'malik_ad', 'aciklama', 'tutar', 'tarih', 'Gecikme (Gün)']].copy()
        gosterim_df.columns = ['Blok', 'Daire', 'Ad Soyad', 'Açıklama', 'Ana Borç (₺)', 'Son Ödeme', 'Gecikme (Gün)']
        st.dataframe(gosterim_df, use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown("##### 🧾 Tahsilat İşlemi ve İletişim")
        
        borclar_dict = {
            f"{r['blok']} No:{r['daire_no']} | {r['malik_ad']} | {r['tutar']:.2f}₺ (Gecikme: {r['Gecikme (Gün)']} gün)": r['id'] 
            for _, r in df_odenmemis.iterrows()
        }
        
        secilen_metin = st.selectbox("İşlem Yapılacak Borcu Seçin", list(borclar_dict.keys()))
        secilen_id = borclar_dict[secilen_metin]
        secilen_kayit = df_odenmemis[df_odenmemis['id'] == secilen_id].iloc[0]
        
        ana_para = secilen_kayit['tutar']
        gecikme_gunu = secilen_kayit['Gecikme (Gün)']
        tel_no = str(secilen_kayit['malik_tel']).replace(" ", "")
        
        # GÜNLÜK FAİZ ORANI (Örn: Günlük binde 1 -> Aylık %3)
        faiz_orani = 0.001 
        hesaplanan_faiz = ana_para * faiz_orani * gecikme_gunu
        
        col1, col2 = st.columns([2, 1])
        
        # SOL TARAF: TAHSİLAT VE FAİZ
        with col1:
            with st.form("tahsilat_formu"):
                faiz_uygula = st.checkbox("Yöneticinin İzniyle Gecikme Faizi Uygula", value=False)
                tahsilat_tarihi = st.date_input("Tahsilat Tarihi", bugun)
                
                odenecek_tutar = ana_para
                if faiz_uygula and gecikme_gunu > 0:
                    odenecek_tutar = ana_para + hesaplanan_faiz
                    st.warning(f"⚠️ Ana Borç: {ana_para:.2f} ₺ + Gecikme Faizi: {hesaplanan_faiz:.2f} ₺ = Toplam: {odenecek_tutar:.2f} ₺")
                else:
                    st.info(f"💵 Tahsil Edilecek Tutar: {ana_para:.2f} ₺")
                
                if st.form_submit_button("✅ Tahsil Et ve Makbuz Oluştur", type="primary"):
                    c = conn.cursor()
                    if faiz_uygula and gecikme_gunu > 0:
                        yeni_aciklama = f"{secilen_kayit['aciklama']} (+{hesaplanan_faiz:.2f}₺ Gecikme Faizi)"
                        c.execute("UPDATE aidatlar SET durum='Ödendi', tutar=?, aciklama=? WHERE id=?", (odenecek_tutar, yeni_aciklama, secilen_id))
                    else:
                        c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (secilen_id,))
                    
                    conn.commit()
                    st.session_state.makbuz_data = f"{secilen_kayit['malik_ad']} | {secilen_kayit['aciklama']} | Tutar: {odenecek_tutar:.2f} ₺"
                    st.session_state.tahsilat_tarihi = tahsilat_tarihi.strftime("%d.%m.%Y")
                    st.rerun()

        # SAĞ TARAF: WHATSAPP VE UYARI
        with col2:
            st.markdown("##### 📱 Hızlı İletişim")
            if gecikme_gunu > 0:
                st.error(f"Bu borç {gecikme_gunu} gün gecikmiş!")
                
                # WhatsApp Mesajı Şablonu
                mesaj = f"Sayın {secilen_kayit['malik_ad']}, {aktif_site} {secilen_kayit['blok']} Blok {secilen_kayit['daire_no']} numaralı dairenize ait {ana_para:.2f} TL tutarındaki borcunuzun son ödeme tarihi ({secilen_kayit['tarih']}) üzerinden {gecikme_gunu} gün geçmiştir. Lütfen en kısa sürede ödemenizi yapınız."
                url_mesaj = urllib.parse.quote(mesaj)
                
                if tel_no and tel_no != "None" and tel_no != "":
                    # Numarayı WhatsApp formatına uygun hale getirme (Son 10 haneyi alıp başına 90 ekler)
                    wp_link = f"https://wa.me/90{tel_no[-10:]}?text={url_mesaj}"
                    st.link_button("💬 WhatsApp'tan Hatırlat", wp_link, use_container_width=True)
                else:
                    st.warning("Kişinin telefonu sisteme kayıtlı değil.")
            else:
                st.success("Ödemede gecikme yok.")
                
    else: 
        st.success("🎉 Harika! Ödenmemiş aidat borcu bulunmuyor.")
    
    conn.close()
