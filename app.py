import os
import pandas as pd
import streamlit as st
from supabase import create_client

# ==========================================
# 0. 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="公司內部用戶資料管理系統", page_icon="👥", layout="wide"
)

# ==========================================
# 1. 連線設定 (建議部署時設定在 Streamlit Secrets)
# ==========================================
# 如果在本地測試，可以直接填入字串；若部署到雲端，請使用 st.secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
  return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
  supabase = init_supabase()
except Exception as e:
  st.error(f"無法連線至 Supabase 資料庫：{e}")
  st.stop()

# ==========================================
# 2. 簡易登入驗證（保護個資不外洩）
# ==========================================
def check_password():
  """簡單的密碼驗證函式"""
  def password_entered():
    # 預設密碼設為 "company123"，你可以自行更改或改從 st.secrets 讀取
    if st.session_state["password"] == st.secrets.get("APP_PASSWORD"):
      st.session_state["password_correct"] = True
      del st.session_state["password"]  # 不要在記憶體留下密碼
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    st.subheader("🔒 內部系統登入")
    st.text_input(
        "請輸入內部存取密碼", type="password", on_change=password_entered, key="password"
    )
    return False
  elif not st.session_state["password_correct"]:
    st.subheader("🔒 內部系統登入")
    st.text_input(
        "請輸入內部存取密碼", type="password", on_change=password_entered, key="password"
    )
    st.error("😕 密碼錯誤，請重新輸入")
    return False
  else:
    return True

if not check_password():
  st.stop()

# ==========================================
# 3. 資料讀取函式
# ==========================================
def load_data():
  try:
    response = supabase.table("users").select("*").execute()
    data = response.data
    if data:
      return pd.DataFrame(data)
    else:
      return pd.DataFrame()
  except Exception as e:
    st.error(f"讀取資料失敗: {e}")
    return pd.DataFrame()

# ==========================================
# 4. 主介面邏輯
# ==========================================
st.title("👥 公司內部用戶資料管理系統")
st.markdown("透過此系統，內部同仁可以快速查詢、篩選與更新用戶資料。")

# 重新載入按鈕
if st.button("🔄 重新載入最新資料"):
  st.rerun()

df = load_data()

if df.empty:
  st.warning("目前資料庫中沒有用戶資料，或者尚未建立 `users` 資料表。")
else:
  # 確保 ID 欄位存在且適合做為索引
  if "id" in df.columns:
    df = df.sort_values(by="id")

  # --- 搜尋與篩選區 ---
  st.subheader("🔍 搜尋與篩選")
  search_col1, search_col2 = st.columns(2)
  
  with search_col1:
    search_keyword = st.text_input("輸入關鍵字搜尋（姓名、電話、信箱等）")

  # 篩選邏輯
  filtered_df = df.copy()
  if search_keyword:
    # 將所有欄位轉成字串進行模糊搜尋
    mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_keyword, case=False, na=False)).any(axis=1)
    filtered_df = filtered_df[mask]

  st.info(f"符合條件的用戶共 {len(filtered_df)} 筆")

  # --- 表格檢視與編輯區 ---
  st.subheader("📝 用戶資料列表（可在表格內直接點擊修改）")
  
  # 使用 data_editor 讓使用者直接在介面修改表格
  edited_df = st.data_editor(
      filtered_df,
      num_rows="dynamic",  # 允許新增或刪除列
      use_container_width=True,
      key="user_editor"
  )

  # --- 儲存變更按鈕 ---
  if st.button("💾 儲存所有變更至資料庫", type="primary"):
    with st.spinner("正在同步至 Supabase 資料庫..."):
      try:
        # 將修改後的 DataFrame 轉換回字典格式
        updated_records = edited_df.to_dict(orient="records")
        
        # 逐筆 upsert（更新或新增）到 Supabase 的 users 資料表
        # 假設資料表的主鍵是 'id'
        for row in updated_records:
          # 移除 Pandas 可能帶入的 NaN 或空值問題
          clean_row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
          supabase.table("users").upsert(clean_row).execute()
          
        st.success("✅ 資料已成功同步並儲存至雲端資料庫！")
        st.rerun()
      except Exception as e:
        st.error(f"❌ 儲存失敗：{e}")
