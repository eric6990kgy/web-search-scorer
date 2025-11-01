"""
網路內容自動搜尋與評分系統 - Streamlit 互動介面
運行方式: streamlit run app_streamlit.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import io

# 導入你的搜尋評分系統
from ContentScorer import WebContentScorer


# ============================================================================
# 頁面配置
# ============================================================================

st.set_page_config(
    page_title="智能網路內容搜尋與評分系統",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# 自訂樣式
# ============================================================================

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(120deg, #1f77b4 0%, #ff7f0e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .stat-number {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    
    .stat-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    
    .progress-container {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# 初始化 Session State
# ============================================================================

if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'scorer' not in st.session_state:
    st.session_state.scorer = None


# ============================================================================
# 側邊欄
# ============================================================================

with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/search.png", width=80)
    st.markdown("### ⚙️ 進階設定")
    
    with st.expander("🔑 SerpAPI 配置（可選）", expanded=False):
        api_key = st.text_input(
            "API Key",
            value="",
            type="password",
            help="在 https://serpapi.com/ 註冊獲取免費 API Key"
        )
        st.caption("💡 提示：留空則使用免費搜尋")
    
    st.markdown("---")
    st.markdown("### 🎯 搜尋參數")
    
    num_results = st.slider(
        "📊 搜尋結果數量",
        min_value=5,
        max_value=20,
        value=10,
        step=1,
        help="建議 10-15 條"
    )
    
    with st.expander("⚖️ 評分權重調整", expanded=False):
        relevance_weight = st.slider(
            "相關性權重",
            min_value=0.0,
            max_value=1.0,
            value=0.65,
            step=0.05
        )
        quality_weight = 1 - relevance_weight
        st.caption(f"品質權重: {quality_weight:.2f}")
    
    st.markdown("---")
    
    if st.session_state.search_history:
        st.markdown("### 📜 搜尋歷史")
        for hist in reversed(st.session_state.search_history[-5:]):
            st.caption(f"🔸 {hist['keyword']} ({hist['count']}條) - {hist['time']}")


# ============================================================================
# 主頁面
# ============================================================================

st.markdown('<h1 class="main-header">🔍 智能網路內容搜尋與評分系統</h1>', unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 10px; margin: 1rem 0;'>
    <p style='font-size: 1.1rem; color: #495057; margin: 0;'>
        🚀 輸入關鍵詞，自動搜尋、抓取、評分，為你找到最有價值的網路資訊
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("## 🔍 開始搜尋")

# 搜尋框
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    keyword = st.text_input(
        "請輸入搜尋關鍵詞",
        value="",
        placeholder="例如：人工智慧、氣候變遷、川普政策...",
        help="輸入你想搜尋的任何主題",
        key="main_keyword_input",
        label_visibility="collapsed"
    )
    
    search_button = st.button("🔍 開始搜尋", use_container_width=True, type="primary")

# 快速範例按鈕
st.markdown("")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if st.button("💡 人工智慧", use_container_width=True):
        st.session_state.quick_search = "人工智慧"
        st.rerun()
with col2:
    if st.button("🌍 氣候變遷", use_container_width=True):
        st.session_state.quick_search = "氣候變遷"
        st.rerun()
with col3:
    if st.button("📈 經濟政策", use_container_width=True):
        st.session_state.quick_search = "經濟政策"
        st.rerun()
with col4:
    if st.button("🏛️ 川普政策", use_container_width=True):
        st.session_state.quick_search = "川普政策"
        st.rerun()
with col5:
    if st.button("🔬 量子電腦", use_container_width=True):
        st.session_state.quick_search = "量子電腦"
        st.rerun()

# 處理快速搜尋
if 'quick_search' in st.session_state:
    keyword = st.session_state.quick_search
    del st.session_state.quick_search
    search_button = True

st.markdown("---")


# ============================================================================
# 搜尋執行
# ============================================================================

if search_button:
    if not keyword or not keyword.strip():
        st.error("❌ 請輸入搜尋關鍵詞！")
    else:
        progress_container = st.container()
        
        with progress_container:
            st.markdown('<div class="progress-container">', unsafe_allow_html=True)
            st.markdown(f"### 🔄 正在搜尋「{keyword}」...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("⚙️ 初始化搜尋引擎...")
            progress_bar.progress(10)
            
            scorer = WebContentScorer(serpapi_key=api_key if api_key else None)
            st.session_state.scorer = scorer
            
            time.sleep(0.5)
            
            status_text.text(f"🌐 正在搜尋 {num_results} 條結果...")
            progress_bar.progress(20)
            
            try:
                with st.spinner(""):
                    results_df = scorer.run(keyword, num_results=num_results)
                
                progress_bar.progress(100)
                status_text.text("✅ 搜尋完成！")
                st.markdown('</div>', unsafe_allow_html=True)
                
                if results_df is not None and not results_df.empty:
                    # 檢查並統一欄位名稱
                    # 如果是簡體中文欄位，不做更改
                    # 如果是繁體中文欄位，轉換為簡體
                    column_mapping = {
                        '綜合評分': '综合评分',
                        '相關性評分': '相关性评分',
                        '品質評分': '品质评分',
                        '抓取狀態': '抓取状态',
                        '標題': '标题',
                        '來源': '来源',
                        '網址': '网址',
                        '發佈日期': '发布日期',
                        '內容長度': '内容长度'
                    }
                    
                    # 重命名欄位（如果存在繁體欄位的話）
                    results_df = results_df.rename(columns=column_mapping)
                    
                    # 應用自訂權重
                    if relevance_weight != 0.65:
                        results_df['综合评分'] = (
                            results_df['相关性评分'] * relevance_weight + 
                            results_df['品质评分'] * quality_weight
                        ).round(2)
                        results_df = results_df.sort_values('综合评分', ascending=False).reset_index(drop=True)
                        results_df['排名'] = range(1, len(results_df) + 1)
                    
                    st.session_state.results_df = results_df
                    
                    st.session_state.search_history.append({
                        'keyword': keyword,
                        'count': len(results_df),
                        'time': datetime.now().strftime('%H:%M')
                    })
                    
                    st.success(f"✅ 成功獲取 {len(results_df)} 條結果！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ 未能獲取搜尋結果，請重試或更換關鍵詞")
                    
            except Exception as e:
                st.error(f"❌ 搜尋過程中出現錯誤: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                progress_bar.progress(0)


# ============================================================================
# 結果展示
# ============================================================================

if st.session_state.results_df is not None:
    df = st.session_state.results_df
    
    st.markdown("---")
    st.markdown("## 📊 搜尋結果分析")
    
    # 統計卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="stat-label">📝 總結果數</div>
            <div class="stat-number">{len(df)}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        avg_score = df['综合评分'].mean()
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="stat-label">⭐ 平均評分</div>
            <div class="stat-number">{avg_score:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        success_count = len(df[df['抓取状态'] == '成功'])
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="stat-label">✅ 成功抓取</div>
            <div class="stat-number">{success_count}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        top_score = df['综合评分'].max()
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <div class="stat-label">🏆 最高分</div>
            <div class="stat-number">{top_score:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("")
    
    # 圖表
    tab1, tab2, tab3 = st.tabs(["📈 評分分佈", "🎯 相關性 vs 品質", "📊 資料表格"])
    
    with tab1:
        st.markdown("### 📈 綜合評分分佈")
        
        fig_bar = px.bar(
            df,
            x='排名',
            y='综合评分',
            color='综合评分',
            color_continuous_scale='Viridis',
            hover_data=['标题', '来源', '相关性评分', '品质评分'],
            labels={'综合评分': '綜合評分', '排名': '排名'}
        )
        fig_bar.update_layout(height=400, showlegend=False, hovermode='x unified')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 📊 評分統計")
            stats_df = pd.DataFrame({
                '指標': ['平均分', '最高分', '最低分', '中位數', '標準差'],
                '綜合評分': [
                    f"{df['综合评分'].mean():.2f}",
                    f"{df['综合评分'].max():.2f}",
                    f"{df['综合评分'].min():.2f}",
                    f"{df['综合评分'].median():.2f}",
                    f"{df['综合评分'].std():.2f}"
                ]
            })
            st.dataframe(stats_df, hide_index=True, use_container_width=True)
        
        with col2:
            st.markdown("#### 🎯 評分等級分佈")
            
            def score_category(score):
                if score >= 80:
                    return '優秀 (≥80)'
                elif score >= 60:
                    return '良好 (60-79)'
                elif score >= 40:
                    return '一般 (40-59)'
                else:
                    return '較低 (<40)'
            
            df['評分等級'] = df['综合评分'].apply(score_category)
            category_counts = df['評分等級'].value_counts()
            
            fig_pie = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            fig_pie.update_layout(height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with tab2:
        st.markdown("### 🎯 相關性評分 vs 品質評分")
        
        fig_scatter = px.scatter(
            df,
            x='相关性评分',
            y='品质评分',
            size='综合评分',
            color='综合评分',
            hover_data=['标题', '来源'],
            color_continuous_scale='Viridis',
            size_max=20
        )
        fig_scatter.update_layout(height=500, xaxis_title='相關性評分', yaxis_title='品質評分')
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        correlation = df['相关性评分'].corr(df['品质评分'])
        st.info(f"📊 相關性與品質的相關係數: {correlation:.3f}")
    
    with tab3:
        st.markdown("### 📋 完整資料表格")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_score = st.slider("最低綜合評分", 0, 100, 0, 5)
        
        with col2:
            status_filter = st.multiselect("抓取狀態", ['成功', '失敗'], ['成功', '失敗'])
        
        with col3:
            sort_options = {'綜合評分': '综合评分', '相關性評分': '相关性评分', '品質評分': '品质评分', '內容長度': '内容长度'}
            sort_label = st.selectbox("排序方式", list(sort_options.keys()))
            sort_by = sort_options[sort_label]
        
        filtered_df = df[
            (df['综合评分'] >= min_score) &
            (df['抓取状态'].isin(status_filter))
        ].sort_values(sort_by, ascending=False)
        
        display_columns = ['排名', '标题', '来源', '综合评分', '相关性评分', '品质评分', '内容长度', '抓取状态']
        
        st.dataframe(filtered_df[display_columns], hide_index=True, use_container_width=True, height=400)
        st.caption(f"顯示 {len(filtered_df)} 條結果（共 {len(df)} 條）")
    
    # TOP 3
    st.markdown("---")
    st.markdown("## 🏆 TOP 3 最有價值的資料")
    
    top3 = df.head(3)
    
    for idx, row in top3.iterrows():
        with st.expander(f"🥇 第 {idx + 1} 名 - {row['标题'][:80]}... (評分: {row['综合评分']})"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**📰 標題:** {row['标题']}")
                st.markdown(f"**🌐 來源:** {row['来源']}")
                st.markdown(f"**🔗 網址:** [{row['网址']}]({row['网址']})")
                st.markdown(f"**📅 發佈日期:** {row['发布日期']}")
                st.markdown(f"**📝 摘要:** {row['摘要']}")
            
            with col2:
                st.markdown("##### 📊 評分詳情")
                
                metrics_data = {
                    '指標': ['綜合評分', '相關性', '品質', '內容長度'],
                    '數值': [
                        f"{row['综合评分']:.1f}",
                        f"{row['相关性评分']:.1f}",
                        f"{row['品质评分']:.1f}",
                        f"{row['内容长度']} 字"
                    ]
                }
                st.dataframe(pd.DataFrame(metrics_data), hide_index=True, use_container_width=True)
                
                categories = ['相關性', '品質']
                values = [row['相关性评分'], row['品质评分']]
                
                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=values, theta=categories, fill='toself', name='評分'))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=False,
                    height=250,
                    margin=dict(l=40, r=40, t=40, b=40)
                )
                st.plotly_chart(fig_radar, use_container_width=True)
    
    # 匯出
    st.markdown("---")
    st.markdown("## 💾 匯出結果")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='搜尋結果')
        buffer.seek(0)
        
        st.download_button(
            label="📥 下載 Excel",
            data=buffer,
            file_name=f"搜尋結果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下載 CSV",
            data=csv,
            file_name=f"搜尋結果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col3:
        json_str = df.to_json(orient='records', force_ascii=False, indent=2)
        st.download_button(
            label="📥 下載 JSON",
            data=json_str,
            file_name=f"搜尋結果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )


# 頁尾
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6c757d; padding: 2rem 0;'>
    <p style='margin: 0;'>🔍 智能網路內容搜尋與評分系統 v1.0</p>
    <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>
        Powered by Streamlit | 基於 BeautifulSoup & Scikit-learn
    </p>
</div>
""", unsafe_allow_html=True)
