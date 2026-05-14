"""
SiteMaster – Ortak Araçlar
utils.sitemaster_logo_koy() tüm modüllerden çağrılır; logo.png varsa
Streamlit sidebar'ın tepesine sabitler, yoksa metin markası gösterir.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_LOGO_DOSYA = Path(__file__).parent / "logo.png"


def sitemaster_logo_koy() -> None:
    """
    SiteMaster logosunu sidebar'ın en tepesine sabitler.

    Öncelik sırası:
      1. st.logo()          — Streamlit ≥ 1.26; sidebar sol üst köşeye yapışır,
                              tüm sayfa yeniden çizimlerinde kalıcıdır.
      2. st.sidebar.image() — Eski Streamlit sürümleri için yedek.
      3. Metin markası      — logo.png yoksa sidebar'da minimal marka gösterir.
    """
    if _LOGO_DOSYA.exists():
        try:
            # Streamlit ≥ 1.26: global, her sayfada otomatik görünür
            st.logo(str(_LOGO_DOSYA))
            return
        except AttributeError:
            # Eski sürüm: st.logo yoksa sidebar'a image olarak bas
            st.sidebar.image(str(_LOGO_DOSYA), use_container_width=True)
            st.sidebar.markdown(
                "<p style='text-align:center;font-weight:700;"
                "font-size:0.8rem;color:#475569;margin:0'>SiteMaster</p>",
                unsafe_allow_html=True,
            )
    else:
        # logo.png bulunamadı — metin markası
        st.sidebar.markdown(
            "<div style='text-align:center;padding:0.4rem 0 0.6rem'>"
            "<span style='font-size:1.5rem'>🏢</span><br>"
            "<strong style='font-size:0.95rem;color:#0f172a'>SiteMaster</strong><br>"
            "<span style='font-size:0.72rem;color:#64748b'>"
            "Kurumsal Site Yönetimi</span>"
            "</div>",
            unsafe_allow_html=True,
        )
