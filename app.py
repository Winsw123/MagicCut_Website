import pandas as pd
import streamlit as st
from supabase import create_client

# ==========================================
# 0. 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="公司內部用戶資料管理系統", page_icon="👥", layout="centered"
)

# ==========================================
# 1. 連線設定
# ==========================================
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
# 2. 簡易登入驗證
# ==========================================
def check_password():
  def password_entered():
    if st.session_state["password"] == st.secrets.get("APP_PASSWORD", "company123"):
      st.session_state["password_correct"] = True
      del st.session_state["password"]
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
@st.cache_data(ttl=10) # 短暫快取讓手機瀏覽更流暢
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
# 4. 主介面邏輯 (手機優化：列表與詳情頁切換)
# ==========================================

# 用 Session State 來追蹤目前點選的用戶 ID，若為 None 則顯示列表
if "selected_user_id" not in st.session_state:
  st.session_state["selected_user_id"] = None

df = load_data()

if df.empty:
  st.warning("目前資料庫中沒有用戶資料。")
  if st.button("🔄 重新載入"):
    st.rerun()

else:
  # 確保有必要的欄位（假設資料表至少有 id, name）
  if "id" not in df.columns or "name" not in df.columns:
    st.error("資料表格式錯誤：必須包含 'id' 與 'name' 欄位。")
    st.stop()

  # ------------------------------------------
  # 狀態 A：詳細資料 / 編輯頁面
  # ------------------------------------------
  if st.session_state["selected_user_id"] is not None:
    user_id = st.session_state["selected_user_id"]
    
    # 找出該用戶的資料
    user_row = df[df["id"] == user_id]
    
    if user_row.empty:
      st.warning("找不到該用戶資料。")
      if st.button("⬅️ 返回列表"):
        st.session_state["selected_user_id"] = None
        st.rerun()
    else:
      user_data = user_row.iloc[0].to_dict()
      
      # 返回按鈕
      if st.button("⬅️ 返回用戶列表", type="secondary"):
        st.session_state["selected_user_id"] = None
        st.rerun()
        
      st.markdown(f"### 📋 用戶詳細資料：{user_data.get('name', '未命名')}室")
      st.markdown("---")
      
      # 使用表單讓手機使用者可以逐項編輯
      with st.form("edit_user_form"):
        updated_values = {}
        
        # 依序為每個欄位建立輸入框（排除 id 不可修改）
        for col in df.columns:
          if col == "id":
            st.text_input("用戶 ID", value=str(user_data[col]), disabled=True)
            continue
            
          val = user_data[col]
          # 簡單判斷型別給予對應的輸入元件
          if pd.isna(val):
            val_str = ""
          else:
            val_str = str(val)
            
          updated_values[col] = st.text_input(f"{col}", value=val_str)
          
        # 儲存按鈕
        submitted = st.form_submit_button("💾 儲存此用戶變更", type="primary")
        
        if submitted:
          try:
            # 組合回原本的型別並加上 id
            payload = {"id": user_id}
            for k, v in updated_values.items():
              payload[k] = None if v == "" else v
              
            # 寫回 Supabase
            supabase.table("users").upsert(payload).execute()
            st.success("✅ 用戶資料更新成功！")
            
            # 清除快取並重新載入
            st.cache_data.clear()
            st.session_state["selected_user_id"] = None
            st.rerun()
          except Exception as e:
            st.error(f"❌ 更新失敗：{e}")

  # ------------------------------------------
  # 狀態 B：手機版友善的用戶列表頁面
  # ------------------------------------------
  else:
    st.title("👥 用戶資料管理")
    
    # 頂部操作列
    col_search, col_refresh = st.columns([4, 1])
    with col_search:
      search_keyword = st.text_input("🔍 搜尋姓名或電話", placeholder="輸入關鍵字...")
    with col_refresh:
      st.write("") # 對齊排版
      if st.button("🔄"):
        st.cache_data.clear()
        st.rerun()

    # 篩選邏輯
    filtered_df = df.copy()
    if search_keyword:
      mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_keyword, case=False, na=False)).any(axis=1)
      filtered_df = filtered_df[mask]

    st.markdown(f"<p style='color: gray; font-size: 14px;'>共找到 {len(filtered_df)} 位用戶（點擊名字進入詳細資料）</p>", unsafe_allow_html=True)

    # 渲染卡片式清單（非常適合手機點擊）
    for index, row in filtered_df.iterrows():
      uid = row["id"]
      name = row.get("name", "未命名")
      # 可以抓取另一個常用欄位輔助顯示，例如電話或信箱
      sub_info = row.get("phone", row.get("email", ""))
      
      # 每一行使用一個簡潔的容器與按鈕
      with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
          st.markdown(f"**👤 {name}**")
          if sub_info:
            st.markdown(f"<span style='color: gray; font-size: 12px;'>{sub_info}</span>", unsafe_allow_html=True)
        with col2:
          # 點擊後將選定的 id 存入 session_state 並重新整理畫面進入詳細頁
          if st.button("查看/編輯", key=f"btn_{uid}"):
            st.session_state["selected_user_id"] = uid
            st.rerun()
            
        st.markdown("---")