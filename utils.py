"""
SiteMaster – Ortak Araçlar
utils.sitemaster_logo_koy() tüm modüllerden çağrılır; logo.png varsa
sayfanın sağ üst köşesine CSS fixed ile sabitler.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_LOGO_DOSYA = Path(__file__).parent / "logo.png"

# Base64 önbelleği — her rerun'da dosya açılmasın
_LOGO_B64: str | None = None


def _logo_b64() -> str | None:
    global _LOGO_B64
    if _LOGO_B64 is None and _LOGO_DOSYA.exists():
        _LOGO_B64 = base64.b64encode(_LOGO_DOSYA.read_bytes()).decode()
    return _LOGO_B64


def sitemaster_logo_koy() -> None:
    """
    SiteMaster logosunu sayfanın SAĞ ÜST köşesine sabitler.

    • CSS position:fixed kullanır → scroll'da bile sabit kalır.
    • Streamlit sürümünden bağımsız çalışır (st.logo gerektirmez).
    • Tüm modüller goster() başında bu fonksiyonu çağırır.
    """
    b64 = _logo_b64()

    if b64:
        img_html = (
            f'<img src="data:image/png;base64,{b64}" '
            f'style="width:110px;border-radius:10px;'
            f'box-shadow:0 2px 8px rgba(0,0,0,.15);" alt="SiteMaster Logo">'
        )
    else:
        img_html = '<span style="font-size:2rem;">🏢</span>'

    st.markdown(
        f"""
        <style>
        /* Streamlit varsayılan header yüksekliğinin altına yerleştir */
        #sm-header-logo {{
            position: fixed;
            top: 62px;
            right: 24px;
            z-index: 9999;
            text-align: center;
            pointer-events: none;   /* tıklamayı engellemesin */
        }}
        #sm-header-logo .sm-label {{
            display: block;
            font-size: 0.60rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #475569;
            margin-top: 3px;
            text-transform: uppercase;
        }}
        </style>
        <div id="sm-header-logo">
            {img_html}
            <span class="sm-label">SiteMaster</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
