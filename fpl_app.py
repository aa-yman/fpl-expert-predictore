import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# إعداد صفحة الويب
st.set_page_config(
    page_title="FPL Expert Predictor",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ترويسة التطبيق
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🔥 FPL Expert Predictor ⚽</h1>', unsafe_allow_html=True)
st.markdown("### التوقعات الذكية للاعبين الذين سيحققون نقاطاً عالية 🔮")

class FPLExpertPredictor:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api/"
        self.session = requests.Session()
        self.current_gameweek = None
        self.player_data = None
        self.fixture_data = None
        self.team_data = None
        
    def get_current_gameweek(self):
        """الحصول على الجيمويك الحالي"""
        try:
            bootstrap = self.session.get(f"{self.base_url}bootstrap-static/").json()
            for event in bootstrap['events']:
                if event['is_current']:
                    self.current_gameweek = event['id']
                    break
        except:
            self.current_gameweek = 1
    
    def fetch_data(self):
        """جلب البيانات من API"""
        try:
            with st.spinner('🔄 جاري تحميل البيانات من FPL...'):
                # بيانات اللاعبين
                player_data = self.session.get(f"{self.base_url}bootstrap-static/").json()
                self.player_data = pd.DataFrame(player_data['elements'])
                
                # بيانات المباريات
                fixture_data = self.session.get(f"{self.base_url}fixtures/").json()
                self.fixture_data = pd.DataFrame(fixture_data)
                
                # بيانات الفرق
                self.team_data = pd.DataFrame(player_data['teams'])
            
            st.success('✅ تم تحميل البيانات بنجاح!')
            return True
        except Exception as e:
            st.error(f'❌ خطأ في تحميل البيانات: {e}')
            return False
    
    def calculate_advanced_metrics(self):
        """حساب المقاييس المتقدمة للاعبين"""
        if self.player_data is None:
            return
        
        df = self.player_data.copy()
        
        numeric_cols = ['now_cost', 'points_per_game', 'selected_by_percent', 
                       'form', 'value_season', 'total_points', 'minutes', 
                       'goals_scored', 'assists', 'clean_sheets']
        
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # المقاييس المتقدمة
        df['points_per_minute'] = np.where(df['minutes'] > 0, df['total_points'] / df['minutes'], 0)
        df['value_index'] = np.where(df['now_cost'] > 0, (df['total_points'] / (df['now_cost'] / 10)), 0)
        df['recent_form_index'] = pd.to_numeric(df['form'], errors='coerce') * 1.5
        df['differential_index'] = (100 - pd.to_numeric(df['selected_by_percent'], errors='coerce')) * df['points_per_game']
        df['surprise_index'] = np.where(
            df['selected_by_percent'].astype(float) < 5.0,
            df['points_per_game'] * 2,
            df['points_per_game']
        )
        
        self.player_data = df
    
    def analyze_fixture_difficulty(self, player_id, target_gw):
        """تحليل صعوبة المباراة في جولة محددة للاعب"""
        try:
            player_team = self.player_data[self.player_data['id'] == player_id]['team'].values[0]
            
            team_fixture = self.fixture_data[
                ((self.fixture_data['team_a'] == player_team) | 
                 (self.fixture_data['team_h'] == player_team)) &
                (self.fixture_data['event'] == target_gw)
            ]
            
            if team_fixture.empty:
                return 3.0
            
            fixture = team_fixture.iloc[0]
            
            if fixture['team_a'] == player_team:
                difficulty = fixture['team_a_difficulty']
            else:
                difficulty = fixture['team_h_difficulty']
                
            return difficulty
        except:
            return 3.0
    
    def get_player_fixture_opponent(self, player_id, target_gw):
        """الحصول على خصم اللاعب في الجولة المحددة"""
        try:
            player_team = self.player_data[self.player_data['id'] == player_id]['team'].values[0]
            
            team_fixture = self.fixture_data[
                ((self.fixture_data['team_a'] == player_team) | 
                 (self.fixture_data['team_h'] == player_team)) &
                (self.fixture_data['event'] == target_gw)
            ]
            
            if team_fixture.empty:
                return "غير معروف"
            
            fixture = team_fixture.iloc[0]
            
            if fixture['team_a'] == player_team:
                opponent_id = fixture['team_h']
            else:
                opponent_id = fixture['team_a']
                
            opponent_team = self.team_data[self.team_data['id'] == opponent_id]['name'].values[0]
            
            if fixture['team_a'] == player_team:
                venue = "خارج الأرض"
            else:
                venue = "داخل الأرض"
                
            return f"{opponent_team} ({venue})"
        except:
            return "غير معروف"
    
    def generate_recommendations_for_gw(self, target_gw, position=None, budget=None, top_n=10):
        """توليد التوصيات لجولة محددة"""
        if self.player_data is None:
            if not self.fetch_data():
                return None
        
        self.calculate_advanced_metrics()
        df = self.player_data.copy()
        
        if position:
            position_map = {'GKP': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
            df = df[df['element_type'] == position_map[position]]
        
        if budget:
            df = df[df['now_cost'] <= budget]
        
        df['fixture_difficulty'] = df['id'].apply(lambda x: self.analyze_fixture_difficulty(x, target_gw))
        df['opponent'] = df['id'].apply(lambda x: self.get_player_fixture_opponent(x, target_gw))
        
        form_numeric = pd.to_numeric(df['form'], errors='coerce')
        df['predicted_points'] = (
            (form_numeric * 2.0) +
            (df['points_per_minute'] * 90 * 1.5) +
            (df['value_index'] * 0.7) -
            (df['fixture_difficulty'] * 0.8) +
            (df['differential_index'] * 0.4) +
            (df['surprise_index'] * 0.6)
        )
        
        recommendations = df.nlargest(top_n, 'predicted_points')[
            ['web_name', 'element_type', 'now_cost', 'total_points', 
             'points_per_game', 'selected_by_percent', 'fixture_difficulty', 'opponent', 'predicted_points']
        ]
        
        position_names = {1: 'حارس', 2: 'مدافع', 3: 'وسط', 4: 'مهاجم'}
        recommendations['position'] = recommendations['element_type'].map(position_names)
        
        return recommendations[['web_name', 'position', 'now_cost', 'total_points', 
                               'points_per_game', 'selected_by_percent', 'fixture_difficulty', 
                               'opponent', 'predicted_points']]
    
    def get_surprise_picks_for_gw(self, target_gw, top_n=5):
        """الحصول على مفاجآت لجولة محددة"""
        df = self.player_data.copy()
        
        selected_by_percent_numeric = pd.to_numeric(df['selected_by_percent'], errors='coerce')
        df = df[selected_by_percent_numeric < 5.0]
        
        form_numeric = pd.to_numeric(df['form'], errors='coerce')
        df = df[form_numeric > 3.0]
        
        df['fixture_difficulty'] = df['id'].apply(lambda x: self.analyze_fixture_difficulty(x, target_gw))
        df['opponent'] = df['id'].apply(lambda x: self.get_player_fixture_opponent(x, target_gw))
        
        form_numeric = pd.to_numeric(df['form'], errors='coerce')
        selected_by_percent_numeric = pd.to_numeric(df['selected_by_percent'], errors='coerce')
        
        df['surprise_score'] = (
            (form_numeric * 2.5) +
            (df['points_per_minute'] * 120) -
            (df['fixture_difficulty'] * 1.5) +
            (100 - selected_by_percent_numeric)
        )
        
        surprise_picks = df.nlargest(top_n, 'surprise_score')[
            ['web_name', 'element_type', 'now_cost', 'team', 
             'total_points', 'points_per_game', 'selected_by_percent', 'opponent', 'surprise_score']
        ]
        
        position_names = {1: 'حارس', 2: 'مدافع', 3: 'وسط', 4: 'مهاجم'}
        surprise_picks['position'] = surprise_picks['element_type'].map(position_names)
        
        team_names = dict(zip(self.team_data['id'], self.team_data['name']))
        surprise_picks['team_name'] = surprise_picks['team'].map(team_names)
        
        return surprise_picks[['web_name', 'position', 'team_name', 'now_cost', 
                              'total_points', 'points_per_game', 'selected_by_percent', 'opponent', 'surprise_score']]

# إنشاء الكائن الرئيسي
predictor = FPLExpertPredictor()
predictor.get_current_gameweek()

# الشريط الجانبي
with st.sidebar:
    st.header("⚙️ الإعدادات")
    
    # اختيار الجولة
    gw_options = list(range(1, 39))
    selected_gw = st.selectbox(
        "اختر الجولة:",
        options=gw_options,
        index=predictor.current_gameweek-1 if predictor.current_gameweek else 0
    )
    
    # تصفية حسب المركز
    position_filter = st.selectbox(
        "تصفية حسب المركز:",
        options=["الكل", "حارس", "مدافع", "وسط", "مهاجم"]
    )
    
    # تصفية حسب الميزانية
    budget_filter = st.slider(
        "الحد الأقصى للسعر:",
        min_value=4.0,
        max_value=15.0,
        value=15.0,
        step=0.5
    )
    
    # زر تحديث البيانات
    if st.button("🔄 تحديث البيانات"):
        predictor.fetch_data()

# تحميل البيانات
if predictor.player_data is None:
    predictor.fetch_data()

if predictor.player_data is not None:
    # عرض التوصيات
    st.markdown(f'<h2 class="sub-header">📊 أفضل التوصيات للجولة {selected_gw}</h2>', unsafe_allow_html=True)
    
    position_map = {"الكل": None, "حارس": "GKP", "مدافع": "DEF", "وسط": "MID", "مهاجم": "FWD"}
    selected_position = position_map[position_filter]
    
    recommendations = predictor.generate_recommendations_for_gw(
        selected_gw, 
        position=selected_position, 
        budget=budget_filter*10,  # التحويل إلى القيمة الحقيقية
        top_n=15
    )
    
    if recommendations is not None:
        # تنسيق الجدول
        recommendations_display = recommendations.copy()
        recommendations_display['now_cost'] = recommendations_display['now_cost'] / 10  # التحويل إلى ملايين
        recommendations_display.rename(columns={
            'web_name': 'اللاعب',
            'position': 'المركز',
            'now_cost': 'السعر',
            'total_points': 'النقاط',
            'points_per_game': 'نقاط/مباراة',
            'selected_by_percent': 'النسبة %',
            'fixture_difficulty': 'صعوبة المباراة',
            'opponent': 'الخصم',
            'predicted_points': 'النقاط المتوقعة'
        }, inplace=True)
        
        # عرض الجدول
        st.dataframe(recommendations_display, use_container_width=True)
        
        # رسم بياني للنقاط المتوقعة
        fig = px.bar(
            recommendations, 
            x='web_name', 
            y='predicted_points',
            title='النقاط المتوقعة لأفضل اللاعبين',
            labels={'web_name': 'اللاعب', 'predicted_points': 'النقاط المتوقعة'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # المفاجآت
    st.markdown(f'<h2 class="sub-header">💎 مفاجآت الجولة {selected_gw}</h2>', unsafe_allow_html=True)
    
    surprise_picks = predictor.get_surprise_picks_for_gw(selected_gw, top_n=5)
    
    if surprise_picks is not None:
        surprise_display = surprise_picks.copy()
        surprise_display['now_cost'] = surprise_display['now_cost'] / 10
        surprise_display.rename(columns={
            'web_name': 'اللاعب',
            'position': 'المركز',
            'team_name': 'الفريق',
            'now_cost': 'السعر',
            'total_points': 'النقاط',
            'points_per_game': 'نقاط/مباراة',
            'selected_by_percent': 'النسبة %',
            'opponent': 'الخصم',
            'surprise_score': 'مؤشر المفاجأة'
        }, inplace=True)
        
        st.dataframe(surprise_display, use_container_width=True)
    
    # نصائح استراتيجية
    st.markdown('<h2 class="sub-header">🎯 نصائح استراتيجية</h2>', unsafe_allow_html=True)
    
    tips = [
        "ركز على اللاعبين ذوي المؤشر التفاضلي العالي (قلة الاختيار + أداء جيد)",
        "انظر إلى صعوبة المباراة في هذه الجولة وليس الأداء السابق فقط",
        "فاجئ منافسيك باختيارات غير متوقعة ولكنها ذكية",
        "انظر إلى خصم كل لاعب وحالة المباراة (داخل/خارج الأرض)",
        "لا تهمل اللاعبين الرخيصين ذوي الأداء الجيد"
    ]
    
    for i, tip in enumerate(tips, 1):
        st.write(f"{i}. {tip}")
    
    # إحصائيات سريعة
    st.markdown('<h2 class="sub-header">📈 إحصائيات سريعة</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if recommendations is not None:
            avg_price = recommendations['now_cost'].mean() / 10
            st.metric("متوسط سعر اللاعبين الموصى بهم", f"{avg_price:.2f}M")
    
    with col2:
        if recommendations is not None:
            avg_points = recommendations['predicted_points'].mean()
            st.metric("متوسط النقاط المتوقعة", f"{avg_points:.1f}")
    
    with col3:
        if surprise_picks is not None:
            avg_ownership = surprise_picks['selected_by_percent'].astype(float).mean()
            st.metric("متوسط نسبة الامتلاك للمفاجآت", f"{avg_ownership:.1f}%")

else:
    st.error("فشل في تحميل البيانات. يرجى التحقق من اتصال الإنترنت والمحاولة مرة أخرى.")

# تذييل الصفحة
st.markdown("---")
st.markdown("""
    <div style='text-align: center'>
        <p>تم تطويره باستخدام ❤️ و Python • FPL Expert Predictor © 2024</p>
    </div>
""", unsafe_allow_html=True)