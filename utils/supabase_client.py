from supabase import create_client
import streamlit as st

@st.cache_resource
def obtener_supabase():
    """
    Devuelve una única conexión a Supabase para toda la aplicación.
    """

    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]

    return create_client(url, key)


supabase = obtener_supabase()