"""SiteMaster – Ortak Araçlar"""
from __future__ import annotations
import base64
from pathlib import Path
import streamlit as st

_LOGO = Path(__file__).parent / "logo.png"


def sitemaster_logo_koy():
    # DB'den gelen logo önce denenir, yoksa dosyadan okunur
    b64: str | None = st.session_state.get("logo_b64")
    if not b64:
        if not _LOGO.exists():
            return
        b64 = base64.b64encode(_LOGO.read_bytes()).decode()

    st.markdown(
        f"""
        <div style="position: fixed; top: 20px; right: 20px;
                    z-index: 1000; text-align: center;">
            <img src="data:image/png;base64,{b64}" width="250">
            <p style="font-size: 10px; margin-top: -5px; color: gray;">SiteMaster</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
