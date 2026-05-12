import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse

def goster(db_yolu, aktif_site):
    st.subheader("💰 Tahsilat Yönetimi (Dinamik Bakiyeli)")
    
    # --- MAKBUZ ALANI ---
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
ödeminiz için teşekkürler.
        """
        st.code(makbuz_metni, language="text")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1: st.download_button("📥 Makbuzu İndir", data=makbuz_metni, file_name="Makbuz.txt", mime="text/plain", use_container_width=True)
        with col_m2:
            if st.button("🔄 Yeni İşlem Yap", use_container_width=True):
                del st.session_state.makbuz_data
                st.rerun()
        st.divider()

    conn = sqlite3.connect(db_yolu)
    
    # Veritabanını sağlama alalım
    try:
        conn.execute("ALTER TABLE aidatlar ADD COLUMN son_odeme_tarihi TEXT")
        conn.execute("ALTER TABLE aidatlar ADD COLUMN faiz_uygula INTEGER DEFAULT 0")
        conn.execute("ALTER TABLE aidatlar ADD COLUMN yillik_faiz REAL DEFAULT 0.0")
        conn.commit()
    except: pass

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
        
        guncel_bakiyeler = []
        gecikme_gunleri = []
        faiz_tutarlari = []
        
        # OTOMATİK GÜNLÜK FAİZ MOTORU
        for index, row in df_odenmemis.iterrows():
            s_tarih_str = row['son_odeme_tarihi'] if pd.notna(row['son_odeme_tarihi']) and row['son_odeme_tarihi'] else row['tarih']
            son_odeme = datetime.datetime.strptime(s_tarih_str, "%Y-%m-%d").date()
            fark = (bugun - son_odeme).days
            gecikme = fark if fark > 0 else 0
            
            ana_para = row['ana_para']
            faiz_miktari = 0.0
            
            # Eğer borç oluşturulurken faiz işlesin denmişse ve gün geçmişse
            if row['faiz_uygula'] == 1 and gecikme > 0:
                gunluk_oran = (row['yillik_faiz'] / 365) / 100
                faiz_miktari = ana_para * gunluk_oran * gecikme
            
            toplam_bakiye = ana_para + faiz_miktari
            
            gecikme_gunleri.append(gecikme)
            faiz_tutarlari.append(faiz_miktari)
            guncel_bakiyeler.append(toplam_bakiye)
            
        df_odenmemis['Son Ödeme'] = [row['son_odeme_tarihi'] if pd.notna(row['son_odeme_tarihi']) and row['son_odeme_tarihi'] else row['tarih'] for _, row in df_odenmemis.iterrows()]
        df_odenmemis['Gecikme (Gün)'] = gecikme_gunleri
        df_odenmemis['Faiz Yükü (₺)'] = faiz_tutarlari
        df_odenmemis['Güncel Bakiye (₺)'] = guncel_bakiyeler
        
        st.markdown("##### 📌 Bekleyen Borçlar ve Otomatik Güncel Bakiyeler")
        gosterim_df = df_odenmemis[['blok', 'daire_no', 'malik_ad', 'aciklama', 'Son Ödeme', 'Gecikme (Gün)', 'ana_para', 'Faiz Yükü (₺)', 'Güncel Bakiye (₺)']].copy()
        gosterim_df.columns = ['Blok', 'Daire', 'Ad Soyad', 'Ödeme Türü', 'Son Ödeme', 'Gecikme', 'Ana Para', 'Faiz Yükü', 'TOPLAM BAKİYE']
        st.dataframe(gosterim_df.style.format({"Ana Para": "{:.2f}", "Faiz Yükü": "{:.2f}", "TOPLAM BAKİYE": "{:.2f}"}), use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown("##### 🧾 Tahsilat İşlemi")
        
        # Selectbox'ta artık direkt TOPLAM BAKİYE görünüyor
        borclar_dict = {
            f"{r['blok']} No:{r['daire_no']} | {r['malik_ad']} | Güncel Bakiye: {r['Güncel Bakiye (₺)']:.2f} ₺": r['id'] 
            for _, r in df_odenmemis.iterrows()
        }
        
        secilen_metin = st.selectbox("Tahsil Edilecek Otomatik Bakiyeyi Seçin", list(borclar_dict.keys()))
        secilen_id = borclar_dict[secilen_metin]
        sec_kayit = df_odenmemis[df_odenmemis['id'] == secilen_id].iloc[0]
        
        odenecek_toplam = sec_kayit['Güncel Bakiye (₺)']
        eklenen_faiz = sec_kayit['Faiz Yükü (₺)']
        tel_no = str(sec_kayit['malik_tel']).replace(" ", "")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            with st.form("tahsilat_formu"):
                st.info(f"💵 Sistem Tarafından Hesaplanmış Güncel Bakiye: **{odenecek_toplam:.2f} ₺**")
                tahsilat_tarihi = st.date_input("Tahsilat Tarihi", bugun)
                
                if st.form_submit_button("✅ Bakiyeyi Tahsil Et", type="primary"):
                    c = conn.cursor()
                    
                    # Veritabanına yeni şişmiş tutarı ve açıklamayı gömüyoruz
                    yeni_aciklama = sec_kayit['aciklama']
                    if eklenen_faiz > 0:
                        yeni_aciklama += f" (+{eklenen_faiz:.2f}₺ Otomatik Faiz)"
                        
                    c.execute("UPDATE aidatlar SET durum='Ödendi', tutar=?, aciklama=? WHERE id=?", (odenecek_toplam, yeni_aciklama, secilen_id))
                    conn.commit()
                    
                    st.session_state.makbuz_data = f"{sec_kayit['malik_ad']} | {yeni_aciklama} | Tahsil Edilen: {odenecek_toplam:.2f} ₺"
                    st.session_state.tahsilat_tarihi = tahsilat_tarihi.strftime("%d.%m.%Y")
                    st.rerun()

        with col2:
            st.markdown("##### 📱 Hatırlatma")
            if sec_kayit['Gecikme (Gün)'] > 0:
                mesaj = f"Sayın {sec_kayit['malik_ad']},\n{aktif_site} {sec_kayit['blok']} Blok {sec_kayit['daire_no']} numaralı dairenize ait borcunuzun son ödeme tarihi ({sec_kayit['Son Ödeme']}) üzerinden {sec_kayit['Gecikme (Gün)']} gün geçmiş olup, günlük faiz işlemiyle birlikte güncel bakiyeniz {odenecek_toplam:.2f} TL olmuştur. Lütfen ödemenizi yapınız."
                url_mesaj = urllib.parse.quote(mesaj)
                
                if tel_no and tel_no != "None" and tel_no != "":
                    wp_link = f"https://wa.me/90{tel_no[-10:]}?text={url_mesaj}"
                    st.link_button("💬 Gecikme Mesajı At", wp_link, use_container_width=True)
            else:
                st.success("Gecikme yok.")
                
    else: 
        st.success("🎉 Bekleyen borç bulunmuyor.")
    conn.close()
