from utils import get_conn
"""SiteMaster – Ortak Araçlar"""
from __future__ import annotations

import base64
import sqlite3
from pathlib import Path

import streamlit as st


def get_conn(db_yolu: str) -> sqlite3.Connection:
    """
    Thread-safe, kilitlenmeye dayanıklı SQLite bağlantısı döner.
    - check_same_thread=False : farklı thread'lerden güvenli erişim
    - timeout=15              : kilit beklemesi için 15 saniye sabır
    - WAL journal_mode        : okuma-yazma çakışmalarını en aza indirir
    - busy_timeout=15000      : PRAGMA seviyesinde ek bekleme (ms)
    """
    conn = sqlite3.connect(db_yolu, check_same_thread=False, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=15000")
    return conn

# SiteMaster markasının kendi statik logosu (asla değişmez)
_SM_LOGO = Path(__file__).parent / "logo.png"
_SM_B64_CACHE: str | None = None


def _sm_logo_b64() -> str | None:
    """SiteMaster marka logosunu (logo.png) base64 olarak döner — önbelleğe alır."""
    global _SM_B64_CACHE
    if _SM_B64_CACHE is None and _SM_LOGO.exists():
        _SM_B64_CACHE = base64.b64encode(_SM_LOGO.read_bytes()).decode()
    return _SM_B64_CACHE


def get_site_logo(master_db_yolu: str, aktif_site: str) -> str | None:
    """
    Veritabanındaki siteler tablosundan aktif sitenin logosunu
    base64 string olarak döner. Logo yoksa None.
    """
    try:
        with get_conn(master_db_yolu) as conn:
            row = conn.execute(
                "SELECT logo FROM siteler WHERE site_adi = ?", (aktif_site,)
            ).fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None


def render_header(page_title: str) -> None:
    """
    Her sayfanın en üstünde logo + başlık satırı oluşturur.
      sol kolon [1] → SiteMaster'ın kendi sabit markası (logo.png)
      sağ kolon [4] → sayfa başlığı
    İçerik bu satırın altında tam genişlikte akar.
    """
    col_logo, col_title = st.columns([1, 8])
    with col_logo:
        b64 = _sm_logo_b64()
        if b64:
            st.image(f"data:image/png;base64,{b64}", width=150)
    with col_title:
        st.subheader(page_title)


def render_sidebar_header() -> None:
    """Sidebar tepesine site logosunu (DB'den) optimize boyutla gösterir."""
    b64 = st.session_state.get("logo_b64")
    if not b64:
        return
    with st.sidebar:
        st.image(f"data:image/png;base64,{b64}", use_container_width=True)
        st.divider()
