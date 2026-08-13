import pandas as pd
import streamlit as st
from supabase import create_client

@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    return create_client(url, key)

@st.cache_data(ttl=10)
def load_data():
    try:
        supabase = init_supabase()
        response = supabase.table("users").select("*").execute()
        data = response.data
        if data:
            return pd.DataFrame(data)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

def update_user_data(payload):
    try:
        supabase = init_supabase()
        supabase.table("users").upsert(payload).execute()
        st.cache_data.clear() # 清除快取以確保讀到最新資料
        return True, "✅ 用戶資料更新成功！"
    except Exception as e:
        return False, f"❌ 更新失敗：{e}"