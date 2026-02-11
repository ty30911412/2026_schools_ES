import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re
## python3 -m streamlit run dashboard/app.py

# --- Page Config ---
st.set_page_config(
    page_title="2026 KIST Engagement Survey 儀表板",
    page_icon="",
    layout="wide"
)

# --- Data Loading ---
@st.cache_data
def load_data():
    # Load 2026 Cleaned Data
    if os.path.exists("data/cleaned_data_2026.csv"):
        df_2026 = pd.read_csv("data/cleaned_data_2026.csv")
    elif os.path.exists("dashboard/data/cleaned_data_2026.csv"):
        df_2026 = pd.read_csv("dashboard/data/cleaned_data_2026.csv")
    else:
        st.error("找不到資料檔 'cleaned_data_2026.csv'")
        return None, None, None

    # Load Trend Data
    if os.path.exists("data/ES_Trend_2023_2026_UPDATED.csv"):
        df_trend = pd.read_csv("data/ES_Trend_2023_2026_UPDATED.csv")
    elif os.path.exists("dashboard/data/ES_Trend_2023_2026_UPDATED.csv"):
        df_trend = pd.read_csv("dashboard/data/ES_Trend_2023_2026_UPDATED.csv")
    else:
        st.error("找不到趨勢資料檔 'ES_Trend_2023_2026_UPDATED.csv'")
        df_trend = None

    # Load Codebook for mapping
    # Assuming CODEBOOK_DRAFT.md is in the root or parallel to data
    codebook_path = None
    if os.path.exists("CODEBOOK_DRAFT.md"):
        codebook_path = "CODEBOOK_DRAFT.md"
    elif os.path.exists("../CODEBOOK_DRAFT.md"):
        codebook_path = "../CODEBOOK_DRAFT.md"
    
    var_map = {}
    if codebook_path:
        with open(codebook_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "|" in line and "Variable Name" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 5:
                        var_name = parts[3]
                        orig_q = parts[4]
                        if var_name and orig_q:
                            var_map[var_name] = orig_q
                            # Also map with _num suffix for convenience
                            var_map[var_name + "_num"] = orig_q

    return df_2026, df_trend, var_map

df_2026, df_trend, var_map = load_data()

if df_2026 is None:
    st.stop()

# --- Sidebar ---
st.sidebar.title("導航")
page = st.sidebar.radio("選擇頁面", ["首頁概覽", "跨年度趨勢比較"])

# --- Helper Functions ---
def get_label(var_name):
    """Returns the Chinese label for a variable if available, else the variable name."""
    # Special handling for demo variables to make them look nicer
    if var_name == 'demo_school': return "服務學校"
    if var_name == 'demo_role': return "擔任職務"
    if var_name == 'demo_tenure_kist': return "KIST 服務年資"
    if var_name == 'demo_join_reason': return "加入 KIST 原因"
    
    return var_map.get(var_name, var_name)

def plot_bar_chart(df, col, title_override=None, orientation='v'):
    label = title_override if title_override else get_label(col)
    
    is_multi = df[col].astype(str).str.contains(r'[\n,]', regex=True).any()
    
    if is_multi:
        s = df[col].dropna().astype(str).str.split(r'[\n,、]+').explode().str.strip()
        s = s[s != '']
        counts = s.value_counts().reset_index()
        counts.columns = ['Option', 'Count']
    else:
        counts = df[col].value_counts().reset_index()
        counts.columns = ['Option', 'Count']
        
    if orientation == 'h':
        fig = px.bar(counts, x='Count', y='Option', orientation='h', title=label, text='Count')
    else:
        fig = px.bar(counts, x='Option', y='Count', title=label, text='Count')
        
    return fig

# --- Page: Home & Demographics ---
if page == "首頁概覽":
    st.title("2026 KIST Engagement Survey 概覽")
    st.markdown("---")
    
    # KPI Metrics
    col1, col2, col3 = st.columns(3)
    
    # Total Respondents
    total_respondents = len(df_2026)
    col1.metric("總填答人數", total_respondents)
    
    # Overall Satisfaction
    if 'out_job_satisfaction_num' in df_2026.columns:
        avg_sat = df_2026['out_job_satisfaction_num'].mean()
        col2.metric("整體工作滿意度", f"{avg_sat:.2f}")
    
    # NPS
    if 'out_nps_num' in df_2026.columns:
        avg_nps = df_2026['out_nps_num'].mean()
        col3.metric("是否願意推薦 KIST 聯盟", f"{avg_nps:.2f}")

    st.markdown("---")
    st.header("樣本結構")
    
    row1_1, row1_2 = st.columns(2)
    with row1_1:
        st.subheader("服務學校")
        st.plotly_chart(plot_bar_chart(df_2026, 'demo_school'), use_container_width=True)
    with row1_2:
        st.subheader("身份別")
        st.plotly_chart(plot_bar_chart(df_2026, 'demo_role', orientation='h'), use_container_width=True)
        
    row2_1, row2_2 = st.columns(2)
    with row2_1:
        st.subheader("服務年資")
        st.plotly_chart(plot_bar_chart(df_2026, 'demo_tenure_kist'), use_container_width=True)
    with row2_2:
        st.subheader("加入原因")
        st.plotly_chart(plot_bar_chart(df_2026, 'demo_join_reason', orientation='h'), use_container_width=True)

# --- Page: Trends ---
elif page == "跨年度趨勢比較":
    st.title("跨年度趨勢分析 (2023-2026)")
    st.markdown("請選擇題目以查看該指標在歷年的變化趨勢。")
    
    if df_trend is not None:
        # Data Prep
        df_trend.columns = [c.replace('\n', '').replace('（換算分數）', '').replace('（原始分數）', '').strip() for c in df_trend.columns]
        id_vars = ['問題']
        value_vars = [c for c in df_trend.columns if '年' in c]
        df_melt = df_trend.melt(id_vars=id_vars, value_vars=value_vars, var_name='Year', value_name='Score')
        df_melt = df_melt.dropna(subset=['Score'])
        
        # Interactive Selection
        # Group questions by category? Or simple list.
        # Let's clean up the 'Year' column to be cleaner (e.g. "2023 年" -> "2023")
        df_melt['Year_Clean'] = df_melt['Year'].str.extract(r'(\d{4})')
        
        search_term = st.text_input("🔍 搜尋題目 (輸入關鍵字，如：滿意度、核心價值)", "")
        options = df_trend['問題'].unique().tolist()
        
        if search_term:
            options = [o for o in options if search_term in str(o)]
            
        selected_question = st.selectbox("請選擇一個題目進行分析：", options)
        
        if selected_question:
            st.markdown("---")
            st.subheader(f"題目：{selected_question}")
            
            # Trend Chart
            subset = df_melt[df_melt['問題'] == selected_question].sort_values('Year_Clean')
            
            # Use Bar chart for clearer comparison of values
            fig_trend = px.bar(
                subset, 
                x='Year_Clean', 
                y='Score', 
                text='Score',
                title="歷年平均分數比較",
                labels={'Year_Clean': '年份', 'Score': '平均分數'}
            )
            fig_trend.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            
            # Dynamic Y-axis to highlight differences
            min_score = subset['Score'].min()
            max_score = subset['Score'].max()
            # Set lower bound slightly below min, but not below 1 (lowest possible Likert)
            lower_bound = max(1, min_score - 0.5)
            upper_bound = min(4.5, max_score + 0.5) # Assuming 4 is max usually, give some headroom
            
            fig_trend.update_layout(yaxis_range=[lower_bound, upper_bound])
            fig_trend.update_xaxes(type='category') # Force categorical X-axis
            
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Show 2026 Detailed Distribution if available
            # We need to find the variable name for this question
            # Reverse lookup in var_map (Value -> Key)
            # This is tricky because var_map is Key -> Value.
            
            # Find the variable name(s) that map to this question
            target_vars = [k for k, v in var_map.items() if v.strip() == selected_question.strip() and k.endswith('_num')]
            
            if target_vars:
                # If found, show distribution for the first match
                target_var = target_vars[0]
                
                st.markdown("---")
                st.subheader("2026 年詳細填答分佈")
                
                # Calculate distribution
                dist_data = df_2026[target_var].value_counts(normalize=True).sort_index().reset_index()
                dist_data.columns = ['Score', 'Percentage']
                dist_data['Percentage_Label'] = (dist_data['Percentage'] * 100).round(1).astype(str) + '%'
                
                fig_dist = px.bar(
                    dist_data,
                    x='Score',
                    y='Percentage',
                    text='Percentage_Label',
                    title="2026 年選項分佈比例",
                    labels={'Score': '選項分數', 'Percentage': '比例'}
                )
                fig_dist.update_traces(textposition='outside')
                st.plotly_chart(fig_dist, use_container_width=True)
                
            else:
                st.info("註：此題目在 2026 原始資料中未找到完全對應的變數名稱，因此無法顯示詳細分佈。")

    else:
        st.warning("找不到趨勢資料檔案。")