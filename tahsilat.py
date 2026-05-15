import streamlit as st
import pandas as pd
import sqlite3
import datetime
import urllib.parse
from utils import (
    render_header,
    get_conn,
    get_site_bilgi,
    makbuz_metni_olustur,
    makbuz_html_olustur,
    render_makbuz_karti,
    render_makbuz_indir_butonlari,
)

MASTER_DB = "master.db"


def goster(db_yolu, aktif_site, master_db_yolu: str = MASTER_DB):
    render_header("💰 Tahsilat Yönetimi (Kişi Bazlı Çoklu Seçim)")
    
    # --- MAKBUZ ALANI (TOPLU TAHSİLAT İÇİN ÖZEL DÜZENLENDİ) ---
    if 'makbuz_data' in st.session_state:
        st.success("✅ Seçili borçlar başarıyla tahsil edildi!")
        t_tarih = st.session_state.get('tahsilat_tarihi', datetime.date.today().strftime("%d.%m.%Y"))
        site = get_site_bilgi(master_db_yolu, aktif_site) or {"site_adi": aktif_site}

        makbuz_metni = makbuz_metni_olustur(
            site,
            baslik="TAHSİLAT MAKBUZU",
            islem_tarihi=t_tarih,
            govde=st.session_state.makbuz_data,
        )
        makbuz_html = makbuz_html_olustur(
            site,
            baslik="TAHSİLAT MAKBUZU",
            islem_tarihi=t_tarih,
            govde_metin=st.session_state.makbuz_data,
            durum_metin="ÖDENDİ (Tahsil edildi)",
            alt_not="Bizi tercih ettiğiniz için teşekkür ederiz.",
        )
        render_makbuz_karti(site, makbuz_metni, html_onizleme=makbuz_html)

        dosya_oneki = f"{aktif_site.replace(' ', '_')}_Makbuz_{t_tarih.replace('.', '-')}"
        render_makbuz_indir_butonlari(
            txt_icerik=makbuz_metni,
            html_icerik=makbuz_html,
            dosya_oneki=dosya_oneki,
        )
        if st.button("🔄 Yeni İşlem Yap", use_container_width=True, key="tahsilat_yeni"):
            del st.session_state.makbuz_data
            st.rerun()
        st.divider()

    conn = get_conn(db_yolu)
    
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
        son_odeme_tarihleri = []
        
        # OTOMATİK GÜNLÜK FAİZ MOTORU (borclandirma.faiz_hesapla ile senkron)
        try:
            from borclandirma import faiz_hesapla as _faiz_hesapla
        except ImportError:
            _faiz_hesapla = None

        for index, row in df_odenmemis.iterrows():
            s_tarih_str = row['son_odeme_tarihi'] if pd.notna(row['son_odeme_tarihi']) and row['son_odeme_tarihi'] else row['tarih']
            son_odeme = datetime.datetime.strptime(s_tarih_str, "%Y-%m-%d").date()
            fark = (bugun - son_odeme).days
            gecikme = fark if fark > 0 else 0

            ana_para = row['ana_para']
            faiz_miktari = 0.0

            if row['faiz_uygula'] == 1 and gecikme > 0:
                if _faiz_hesapla:
                    sonuc = _faiz_hesapla(ana_para, row['yillik_faiz'], s_tarih_str)
                    faiz_miktari = sonuc['faiz_tutari']
                else:
                    gunluk_oran = (row['yillik_faiz'] / 365) / 100
                    faiz_miktari = ana_para * gunluk_oran * gecikme

            toplam_bakiye = ana_para + faiz_miktari
            
            son_odeme_tarihleri.append(s_tarih_str)
            gecikme_gunleri.append(gecikme)
            faiz_tutarlari.append(faiz_miktari)
            guncel_bakiyeler.append(toplam_bakiye)
            
        df_odenmemis['Son Ödeme'] = son_odeme_tarihleri
        df_odenmemis['Gecikme (Gün)'] = gecikme_gunleri
        df_odenmemis['Faiz Yükü (₺)'] = faiz_tutarlari
        df_odenmemis['Güncel Bakiye (₺)'] = guncel_bakiyeler
        
        # Kişileri Gruplamak İçin Etiket Oluşturuyoruz
        df_odenmemis['kisi_etiket'] = df_odenmemis['blok'] + " Blok No:" + df_odenmemis['daire_no'] + " | " + df_odenmemis['malik_ad']
        
        st.markdown("##### 👤 1. Tahsilat Yapılacak Kişiyi Seçin")
        kisiler = df_odenmemis['kisi_etiket'].unique()
        secilen_kisi = st.selectbox("Sadece borcu olan daireler listelenmektedir:", kisiler)
        
        # SADECE SEÇİLEN KİŞİNİN BORÇLARINI FİLTRELE
        df_kisi = df_odenmemis[df_odenmemis['kisi_etiket'] == secilen_kisi]
        kisi_ad_soyad = secilen_kisi.split('|')[1].strip()
        tel_no = str(df_kisi.iloc[0]['malik_tel']).replace(" ", "")
        genel_toplam_borc = df_kisi['Güncel Bakiye (₺)'].sum()
        
        st.divider()
        st.markdown(f"##### 📊 {kisi_ad_soyad} Adlı Kişinin Dökümü (Toplam Borç: {genel_toplam_borc:.2f} ₺)")
        
        # Kişinin tablosunu şık bir şekilde göster
        gosterim_df = df_kisi[['aciklama', 'Son Ödeme', 'Gecikme (Gün)', 'ana_para', 'Faiz Yükü (₺)', 'Güncel Bakiye (₺)']].copy()
        gosterim_df.columns = ['Ödeme Türü', 'Son Ödeme', 'Gecikme', 'Ana Para', 'Faiz Yükü', 'TOPLAM BAKİYE']
        st.dataframe(gosterim_df.style.format({"Ana Para": "{:.2f}", "Faiz Yükü": "{:.2f}", "TOPLAM BAKİYE": "{:.2f}"}), use_container_width=True, hide_index=True)
        
        st.divider()
        st.markdown("##### 🧾 2. Ödenecek Borçları İşaretleyin")
        
        secilen_borclar = []
        odenecek_toplam = 0.0
        
        # Her bir borç için dinamik checkbox oluştur
        for index, row in df_kisi.iterrows():
            c_label = f"📌 {row['aciklama']} (Ana Para: {row['ana_para']:.2f} ₺ + Faiz: {row['Faiz Yükü (₺)']:.2f} ₺) ➡️ GÜNCEL TUTAR: {row['Güncel Bakiye (₺)']:.2f} ₺"
            # Yönetici tıkladıkça sayfa anında güncellenir ve alt kısımdaki toplam değişir
            if st.checkbox(c_label, key=f"chk_{row['id']}"):
                secilen_borclar.append(row)
                odenecek_toplam += row['Güncel Bakiye (₺)']
        
        # Eğer en az 1 borç seçildiyse Tahsilat butonunu göster
        if secilen_borclar:
            with st.container(border=True):
                st.info(f"💵 Seçilen Borçların Toplam Tutarı: **{odenecek_toplam:.2f} ₺**")
                col_t1, col_t2 = st.columns([2, 1])
                
                with col_t1:
                    tahsilat_tarihi = st.date_input("Tahsilat Tarihi", bugun)
                with col_t2:
                    st.write("") # Hizalama boşluğu
                    if st.button("✅ İşaretli Borçları Tahsil Et", type="primary", use_container_width=True):
                        c = conn.cursor()
                        makbuz_kalemleri = []
                        
                        # Seçilen her bir borcu veritabanında ÖDENDİ yapıyoruz
                        for borc in secilen_borclar:
                            b_id = borc['id']
                            b_toplam = borc['Güncel Bakiye (₺)']
                            b_faiz = borc['Faiz Yükü (₺)']
                            
                            yeni_aciklama = borc['aciklama']
                            if b_faiz > 0:
                                yeni_aciklama += f" (+{b_faiz:.2f}₺ Otomatik Faiz)"
                                
                            c.execute("UPDATE aidatlar SET durum='Ödendi', tutar=?, aciklama=? WHERE id=?", (b_toplam, yeni_aciklama, b_id))
                            makbuz_kalemleri.append(f"- {yeni_aciklama} : {b_toplam:.2f} ₺")
                        
                        conn.commit()
                        
                        # Makbuzu tüm kalemleri içerecek şekilde hazırla
                        makbuz_detay = "\n".join(makbuz_kalemleri)
                        st.session_state.makbuz_data = f"İLGİLİ KİŞİ: {secilen_kisi}\n\nÖDENEN KALEMLER:\n{makbuz_detay}\n-------------------------------------------------\nGENEL TOPLAM: {odenecek_toplam:.2f} ₺"
                        st.session_state.tahsilat_tarihi = tahsilat_tarihi.strftime("%d.%m.%Y")
                        st.rerun()
        else:
            st.warning("Tahsilat işlemini tamamlamak için yukarıdaki listeden en az bir borcu işaretlemelisiniz.")
            
        # --- WHATSAPP İLETİŞİM ALANI ---
        st.divider()
        st.markdown("##### 📱 Hızlı İletişim (Tüm Borçlar İçin)")
        if df_kisi['Gecikme (Gün)'].max() > 0:
            mesaj = f"Sayın {kisi_ad_soyad},\n{aktif_site} sitemize ait toplamda {genel_toplam_borc:.2f} TL gecikmiş güncel aidat/gider borcunuz bulunmaktadır. Lütfen en kısa sürede ödemenizi gerçekleştiriniz."
            url_mesaj = urllib.parse.quote(mesaj)
            
            if tel_no and tel_no != "None" and tel_no != "":
                wp_link = f"https://wa.me/90{tel_no[-10:]}?text={url_mesaj}"
                st.link_button(f"💬 WhatsApp'tan Toplam Borç Bildirimi Gönder ({genel_toplam_borc:.2f} ₺)", wp_link)
            else:
                st.error("Kişinin telefonu sisteme kayıtlı değil.")
                
    else: 
        st.success("🎉 Harika! Ödenmemiş aidat borcu bulunmuyor.")
    conn.close()

