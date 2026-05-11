import streamlit as st
import sqlite3
import datetime

def goster(db_yolu):
    st.subheader("Aidat Tahakkuku")
    conn = sqlite3.connect(db_yolu); c = conn.cursor(); c.execute("SELECT blok, daire_no, malik_ad FROM sakinler"); s_list = c.fetchall(); conn.close()
    sec = ["🌟 Toplu Borçlandırma"] + [f"{s[0]} Blok - No:{s[1]} ({s[2]})" for s in s_list]
    with st.form("borc_form", clear_on_submit=True):
        h = st.selectbox("Daire", sec); tut = st.number_input("Tutar", min_value=0.0); acik = st.text_input("Açıklama")
        if st.form_submit_button("💸 Borçlandır"):
            conn = sqlite3.connect(db_yolu); c = conn.cursor()
            if h == "🌟 Toplu Borçlandırma":
                for s in s_list: c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?,?,?,?,?)", (s[0], s[1], str(datetime.date.today()), tut, acik))
            else:
                idx = sec.index(h) - 1; s = s_list[idx]
                c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?,?,?,?,?)", (s[0], s[1], str(datetime.date.today()), tut, acik))
            conn.commit(); conn.close(); st.success("Borçlar yansıtıldı!")
