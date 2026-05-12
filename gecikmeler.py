import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse

def goster(db_yolu, aktif_site):
    st.subheader("🚨 Gecikmiş Borçlar ve İletişim Merkezi")

    conn = sqlite3.connect(db_yolu)
    
    # Sadece Ödenmemiş borçları çekiyoruz (Faiz oranları ve son ödeme tarihleriyle birlikte)
    query = """
    SELECT 
        a.id, a.blok, a.daire_no, s.malik_ad, s.malik_tel, 
        a.aciklama, a.tutar as ana_para, a.tarih, a.son_odeme_tarihi, a.faiz_uygula, a.yillik_faiz
    FROM aidatlar a
    INNER JOIN sakinler s ON a.blok = s.blok AND a.daire_no = s.daire_no
    WHERE a.durum = 'Ödenmedi'
    """
    df_odenmemis = pd.read_sql_query(query, conn)
    
    if not df_odenmemis.empty:
        bugun = datetime.date.today()
        
        gecikmis_borclar_df = []
        
        # Filtreleme: Sadece tarihi geçenleri listeye alacağız
        for index, row in df_odenmemis.iterrows():
            s_tarih_str = row['son_odeme_tarihi'] if pd.notna(row['son_odeme_tarihi']) and row['son_odeme_tarihi'] else row['tarih']
            son_odeme = datetime.datetime.strptime(s_tarih_str, "%Y-%m-%d").date()
            fark = (bugun - son_odeme).days
            
            # Eğer gün farkı 0'dan büyükse bu borç gecikmiştir!
            if fark > 0: 
                ana_para = row['ana_para']
                faiz_miktari = 0.0
                
                # Faiz hesaplama motoru (Tahsilat ekranıyla aynı senkron)
                if row['faiz_uygula'] == 1:
                    gunluk_oran = (row['yillik_faiz'] / 365) / 100
                    faiz_miktari = ana_para * gunluk_oran * fark
                
                toplam_bakiye = ana_para + faiz_miktari
                
                satir = row.to_dict()
                satir['Gecikme (Gün)'] = fark
                satir['Güncel Bakiye (₺)'] = toplam_bakiye
                satir['Son Ödeme'] = s_tarih_str
                gecikmis_borclar_df.append(satir)
        
        if gecikmis_borclar_df:
            df_gecikmeler = pd.DataFrame(gecikmis_borclar_df)
            
            st.markdown("##### 📌 Kırmızı Liste (Gecikmedeki Daireler)")
            gosterim_df = df_gecikmeler[['blok', 'daire_no', 'malik_ad', 'aciklama', 'Son Ödeme', 'Gecikme (Gün)', 'Güncel Bakiye (₺)']].copy()
            gosterim_df.columns = ['Blok', 'Daire', 'Ad Soyad', 'Ödeme Türü', 'Son Ödeme', 'Gecikme (Gün)', 'Güncel Bakiye (₺)']
            
            st.dataframe(gosterim_df.style.format({"Güncel Bakiye (₺)": "{:.2f}"}), use_container_width=True, hide_index=True)
            
            st.divider()
            st.markdown("##### 📨 Otomatik Bildirim Gönder")
            
            # Selectbox için kişileri ve güncel bakiyelerini hazırlıyoruz
            secenekler = {
                f"{r['blok']} No:{r['daire_no']} | {r['malik_ad']} | Gecikme: {r['Gecikme (Gün)']} Gün | Bakiye: {r['Güncel Bakiye (₺)']:.2f} ₺": r
                for r in gecikmis_borclar_df
            }
            
            secilen_metin = st.selectbox("Bildirim Gönderilecek Kişiyi Seçin", list(secenekler.keys()))
            secilen_kisi = secenekler[secilen_metin]
            
            tel_no = str(secilen_kisi['malik_tel']).replace(" ", "")
            
            # Otomatik Mesaj Şablonu
            mesaj = f"Sayın {secilen_kisi['malik_ad']},\n{aktif_site} {secilen_kisi['blok']} Blok {secilen_kisi['daire_no']} numaralı dairenize ait borcunuzun son ödeme tarihi ({secilen_kisi['Son Ödeme']}) üzerinden {secilen_kisi['Gecikme (Gün)']} gün geçmiş olup, güncel bakiyeniz {secilen_kisi['Güncel Bakiye (₺)']:.2f} TL olmuştur. Lütfen en kısa sürede ödemenizi gerçekleştiriniz."
            url_mesaj = urllib.parse.quote(mesaj)
            
            st.info("Aşağıdaki butonlara tıklayarak seçili kişiye ilgili platformdan otomatik mesaj gönderebilirsiniz.")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if tel_no and tel_no not in ["None", "", "nan"]:
                    wp_link = f"https://wa.me/90{tel_no[-10:]}?text={url_mesaj}"
                    st.link_button("💬 WhatsApp'tan Gönder", wp_link, use_container_width=True)
                else:
                    st.error("WhatsApp: Telefon kaydı yok.")
                    
            with col2:
                if tel_no and tel_no not in ["None", "", "nan"]:
                    # Telefonun varsayılan SMS uygulamasını açar
                    sms_link = f"sms://+90{tel_no[-10:]}?body={url_mesaj}"
                    st.markdown(f'<a href="{sms_link}" target="_blank"><button style="width:100%; padding:10px; background-color:#1E90FF; color:white; border:none; border-radius:5px; cursor:pointer;">📱 SMS Uygulamasını Aç</button></a>', unsafe_allow_html=True)
                else:
                    st.error("SMS: Telefon kaydı yok.")
                    
            with col3:
                # Veritabanında şu an e-mail adresi olmadığı için E-Posta istemcisini boş alıcıyla ama metin dolu şekilde açarız.
                mail_link = f"mailto:?subject={urllib.parse.quote('Gecikmiş Aidat Ödemesi Hakkında')}&body={url_mesaj}"
                st.markdown(f'<a href="{mail_link}" target="_blank"><button style="width:100%; padding:10px; background-color:#FFA500; color:white; border:none; border-radius:5px; cursor:pointer;">📧 E-Posta Yaz</button></a>', unsafe_allow_html=True)
                
        else:
            st.success("🎉 Harika! Gecikmede olan hiçbir borç bulunmuyor.")
    else:
        st.success("🎉 Harika! Ödenmemiş aidat borcu bulunmuyor.")
        
    conn.close()
