"""
SiteMaster – Ortak Araçlar
sitemaster_logo_koy() → logo.png dosyasını sayfanın sağ üst köşesine koyar.
Tüm modüller goster() başında bu fonksiyonu çağırır.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_LOGO = Path(__file__).parent / "logo.png"


def sitemaster_logo_koy() -> None:
    """
    logo.png varsa sayfanın sağ üst köşesine st.image ile gösterir.
    Dosya bulunamazsa hiçbir şey göstermez — emoji veya ikon uydurmaz.
    """
    if not _LOGO.exists():
        return  # logo.png yoksa sessizce çık, asla başka görsel koyma

    # Sağ üst köşe için CSS kılıfı
    st.markdown(
        """
        <style>
        /* sitemaster logo wrapper — sağ üst köşeye sabitler */
        .sm-logo-wrap {
            position: fixed;
            top: 58px;
            right: 18px;
            z-index: 9999;
            text-align: center;
            line-height: 1;
        }
        .sm-logo-wrap .sm-caption {
            display: block;
            font-size: 0.58rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            color: #475569;
            margin-top: 4px;
            text-transform: uppercase;
        }
        /* Streamlit'in stImage div'ini wrapper içinde sıfırla */
        .sm-logo-wrap [data-testid="stImage"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        <div class="sm-logo-wrap" id="sm-logo-wrap">
        """,
        unsafe_allow_html=True,
    )

    st.image(str(_LOGO), width=100)

    st.markdown(
        '<span class="sm-caption">SiteMaster</span></div>',
        unsafe_allow_html=True,
    )
