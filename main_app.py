"""
Vandatrack Navigator - Main Application
Version 1.3.2 - Secure Edition with Authentication & Rate Limiting
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import base64
from pathlib import Path
import hashlib
import hmac

import sys
# Force reload of multi_security module
if 'multi_security' in sys.modules:
    del sys.modules['multi_security']

# ==========================================
# SECURITY: AUTHENTICATION
# ==========================================

def check_password():
    """Returns True if user entered correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Hash the entered password and compare with stored hash
        entered_hash = hashlib.sha256(st.session_state["password"].encode()).hexdigest()
        stored_hash = st.secrets.get("password_hash", "")
        
        if hmac.compare_digest(entered_hash, stored_hash):
            st.session_state["password_correct"] = True
            st.session_state["login_time"] = datetime.now()
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False
            st.session_state["failed_attempts"] = st.session_state.get("failed_attempts", 0) + 1

    # Check if already authenticated
    if st.session_state.get("password_correct", False):
        return True

    # Show login screen
    st.markdown("""
    <div style="text-align: center; padding: 3rem 0;">
        <h1 style="color: #1a73e8; margin-bottom: 1rem;">🔐 VandaTrack Navigator</h1>
        <p style="color: #5f6368; font-size: 1.1rem;">Secure Access Required</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.text_input(
            "Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            placeholder="Enter your password"
        )
        
        if "password_correct" in st.session_state:
            if not st.session_state["password_correct"]:
                attempts = st.session_state.get("failed_attempts", 0)
                st.error(f"🔒 Incorrect password. Attempt {attempts}")
                
                if attempts >= 3:
                    st.warning("⚠️ Multiple failed attempts detected. Please contact administrator.")
        
        st.caption("🔐 This application is password-protected for security.")
    
    return False

# ==========================================
# SECURITY: RATE LIMITING
# ==========================================

def check_rate_limit(max_requests=50, window_minutes=60):
    """
    Rate limiting to prevent API abuse.
    Default: 50 requests per hour per session.
    """
    
    # Initialize request history
    if "request_history" not in st.session_state:
        st.session_state.request_history = []
    
    now = datetime.now()
    cutoff = now - timedelta(minutes=window_minutes)
    
    # Remove old requests outside the time window
    st.session_state.request_history = [
        req_time for req_time in st.session_state.request_history 
        if req_time > cutoff
    ]
    
    # Check if limit exceeded
    current_count = len(st.session_state.request_history)
    
    if current_count >= max_requests:
        remaining_time = (st.session_state.request_history[0] + timedelta(minutes=window_minutes) - now).seconds // 60
        st.error(f"⚠️ **Rate Limit Exceeded**")
        st.warning(f"""
        You have reached the maximum of **{max_requests} requests per {window_minutes} minutes**.
        
        Please wait **{remaining_time} minutes** before making more requests.
        
        Current usage: {current_count}/{max_requests} requests
        """)
        st.stop()
    
    # Add current request
    st.session_state.request_history.append(now)
    
    # Show usage in sidebar
    with st.sidebar:
        usage_pct = (current_count / max_requests) * 100
        
        if usage_pct < 50:
            color = "#28a745"
            emoji = "🟢"
        elif usage_pct < 80:
            color = "#ffc107"
            emoji = "🟡"
        else:
            color = "#dc3545"
            emoji = "🔴"
        
        st.markdown(f"""
        <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <div style="font-size: 0.75rem; color: #6c757d; text-transform: uppercase; margin-bottom: 0.5rem;">
                API Usage
            </div>
            <div style="font-size: 1.5rem; font-weight: 600; color: {color};">
                {emoji} {current_count}/{max_requests}
            </div>
            <div style="font-size: 0.75rem; color: #6c757d; margin-top: 0.5rem;">
                Requests this hour
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# SECURITY: SESSION MONITORING
# ==========================================

def monitor_session():
    """Monitor session for security events."""
    
    if "session_start" not in st.session_state:
        st.session_state.session_start = datetime.now()
    
    # Auto-logout after 1 hour
    session_duration = datetime.now() - st.session_state.get("login_time", datetime.now())
    if session_duration.total_seconds() > 1 * 3600:  # 1 hour
        st.session_state.clear()
        st.warning("⏱️ Session expired after 1 hour of activity. Please login again.")
        st.stop()
    
    # Show session info in sidebar
    with st.sidebar:
        login_time = st.session_state.get("login_time")
        if login_time:
            st.markdown(f"""
            <div style="font-size: 0.7rem; color: #6c757d; padding: 0.5rem;">
                🔐 Logged in at {login_time.strftime('%H:%M')}
            </div>
            """, unsafe_allow_html=True)
        
        # Logout button
        if st.button("🔓 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ==========================================
# CHECK AUTHENTICATION FIRST
# ==========================================

if not check_password():
    st.stop()

# Monitor session after authentication
monitor_session()

# Import our analysis modules (same directory)
from single_security import SingleSecurityAnalyzer
from multi_security import MultiSecurityAnalyzer

# ==========================================
# APP CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Vandatrack Navigator", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="📊"
)

# Enhanced CSS with Mobile Optimizations
st.markdown("""
<style>
    .main {
        padding-top: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .analytics-header {
        background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(26, 115, 232, 0.15);
        border: none;
    }
    
    .analytics-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 500;
        letter-spacing: -0.02em;
    }
    
    .analytics-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1rem;
        font-weight: 400;
    }
    
    .control-panel {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e8eaed;
        margin-bottom: 2rem;
    }
    
    .control-panel h3 {
        margin: 0 0 1rem 0;
        font-size: 1.125rem;
        font-weight: 500;
        color: #202124;
    }
    
    .chart-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e8eaed;
        margin-bottom: 1.5rem;
    }
    
    .chart-title {
        font-size: 1.125rem;
        font-weight: 500;
        color: #202124;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #e8eaed;
    }
    
    .status-chip {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-chip.success {
        background: #e8f5e8;
        color: #137333;
    }
    
    .status-chip.warning {
        background: #fef7e0;
        color: #ea8600;
    }
    
    .status-chip.error {
        background: #fce8e6;
        color: #d93025;
    }
    
    .section-divider {
        height: 2rem;
    }
    
    .footer {
        background: #f8f9fa;
        border-top: 1px solid #e8eaed;
        padding: 2rem 0;
        margin-top: 3rem;
        text-align: center;
        color: #5f6368;
    }
    
    /* ================================================ */
    /* 📱 MOBILE-FRIENDLY OPTIMIZATIONS */
    /* ================================================ */
    
    @media (max-width: 768px) {
        /* Reduce padding on mobile */
        .main {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Smaller header on mobile */
        .analytics-header {
            padding: 1rem 1.5rem !important;
        }
        
        .analytics-header h1 {
            font-size: 1.5rem !important;
        }
        
        .analytics-header p {
            font-size: 0.875rem !important;
        }
        
        /* Compact control panel */
        .control-panel {
            padding: 1rem !important;
        }
        
        .control-panel h3 {
            font-size: 1rem !important;
        }
        
        /* Smaller chart cards */
        .chart-card {
            padding: 1rem !important;
        }
        
        .chart-title {
            font-size: 1rem !important;
        }
        
        /* Better touch targets */
        .stButton > button {
            min-height: 44px !important;
            font-size: 0.875rem !important;
        }
        
        /* Larger text inputs on mobile */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > select {
            font-size: 16px !important; /* Prevents zoom on iOS */
            min-height: 44px !important;
        }
        
        /* Stack columns on mobile */
        [data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
        }
        
        /* Scrollable tables */
        .dataframe {
            font-size: 0.75rem !important;
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch !important;
        }
        
        /* Plotly charts mobile optimization */
        .js-plotly-plot .plotly .modebar {
            top: 0 !important;
            right: 0 !important;
        }
        
        .js-plotly-plot .plotly .modebar-btn {
            height: 40px !important;
            width: 40px !important;
        }
        
        /* Prevent double-tap zoom */
        * {
            touch-action: manipulation !important;
        }
        
        /* Better spacing for forms */
        .stSelectbox, .stTextInput, .stDateInput {
            margin-bottom: 0.75rem !important;
        }
        
        /* Compact metrics */
        [data-testid="metric-container"] {
            padding: 0.5rem !important;
        }
        
        /* Responsive footer */
        .footer {
            padding: 1rem 0 !important;
            font-size: 0.75rem !important;
        }
        
        /* Hide sidebar by default on mobile */
        section[data-testid="stSidebar"] {
            width: 0 !important;
        }
        
        section[data-testid="stSidebar"][aria-expanded="true"] {
            width: 21rem !important;
        }
    }
    
    /* ================================================ */
    /* 📱 EXTRA SMALL MOBILE (< 480px) */
    /* ================================================ */
    
    @media (max-width: 480px) {
        .analytics-header h1 {
            font-size: 1.25rem !important;
        }
        
        .analytics-header p {
            font-size: 0.75rem !important;
        }
        
        .chart-card {
            padding: 0.75rem !important;
        }
        
        .stButton > button {
            font-size: 0.75rem !important;
            padding: 0.5rem !important;
        }
    }
    
    /* ================================================ */
    /* 📱 TABLET (768px - 1024px) */
    /* ================================================ */
    
    @media (min-width: 768px) and (max-width: 1024px) {
        .main {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        .analytics-header h1 {
            font-size: 1.75rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================

for key, default in [('call_put_selection', 'net_premium'), ('transaction_type', 'combined'), 
                     ('moneyness_option', 'OTM'), ('size_option', 'combined'),
                     ('z_score_window', 21)]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==========================================
# API KEYS CONFIGURATION
# ==========================================

try:
    VANDATRACK_TOKEN = st.secrets.get("VANDATRACK_TOKEN")
except:
    VANDATRACK_TOKEN = None

# ==========================================
# HEADER WITH LOGO
# ==========================================

# Load and prepare logo
logo_path = Path("pmvectors_logo.png")
if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_data}" style="height: 60px; width: auto; border-radius: 8px;">'
else:
    logo_html = """
    <div style="background: rgba(255,255,255,0.15); backdrop-filter: blur(10px); 
                border-radius: 12px; padding: 1rem 1.5rem; text-align: center;
                border: 1px solid rgba(255,255,255,0.2);">
        <div style="color: white; font-weight: 600; font-size: 1.3rem; 
                    letter-spacing: 1px; margin-bottom: 0.25rem;">
            PM<span style="color: #64b5f6;">VEC</span>TORS
        </div>
        <div style="color: rgba(255,255,255,0.8); font-size: 0.75rem; 
                    text-transform: uppercase; letter-spacing: 1px;">
            OPTIMIZE YOUR ANALYSIS!
        </div>
    </div>
    """

st.markdown(f"""
<div class="analytics-header" style="display: flex; justify-content: space-between; align-items: center;">
    <div style="flex: 1;">
        <h1 style="margin: 0; font-size: 2rem; font-weight: 500; letter-spacing: -0.02em;">📊 Vandatrack Navigator</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 1rem; font-weight: 400;">Advanced Options & Retail Flow Analysis Platform</p>
    </div>
    <div style="flex: 0 0 auto; margin-left: 2rem;">
        {logo_html}
    </div>
</div>
""", unsafe_allow_html=True)

# Add User Guide and Control Buttons
col1, col2, col3, col4, col5 = st.columns([1, 6, 1, 1, 1])
with col1:
    if st.button("📖 User Guide", use_container_width=True):
        st.session_state['show_guide'] = not st.session_state.get('show_guide', False)

with col4:
    if st.button("🔄 Rerun", use_container_width=True, help="Restart the application"):
        st.rerun()

with col5:
    if st.button("⏹️ Stop", use_container_width=True, help="Stop execution", type="secondary"):
        st.stop()

# Display User Guide if toggled
if st.session_state.get('show_guide', False):
    with st.expander("📖 VandaTrack Navigator - User Guide", expanded=True):
        st.markdown("""
        # VandaTrack Navigator - Comprehensive User Guide
        
        ## 🎯 Overview
        VandaTrack Navigator is an advanced analytics platform for analyzing retail and institutional options flow data. 
        It provides powerful tools to understand market sentiment, momentum, and activity levels across securities.
        
        ---
        
        ## 📊 Analysis Types
        
        ### 1. **Single Security Analysis**
        Analyze individual securities with multiple flow types and advanced metrics.
        
        #### Available Analyses:
        
        **A. Stock Retail Flow**
        - Tracks retail investor buying and selling activity
        - Shows combined, buy-only, or sell-only flow
        - **Z-Score Window**: Configurable 21-day or 60-day rolling window
        - **Key Observations:**
          - Net positive flow indicates retail buying pressure
          - Z-scores > 1.5 suggest "crowded" trades
          - Compare flow with stock price to identify divergences
        
        **B. Options Flow** ✨ NEW: Z-Score Window Support
        - Analyzes options premium flow (calls vs puts)
        - Filters by moneyness (OTM, ITM, ATM) and size (small, large, combined)
        - **Z-Score Window**: Now configurable (21-day or 60-day)
        - **Key Observations:**
          - Call premium > Put premium suggests bullish sentiment
          - Large trades indicate institutional activity
          - OTM flow often signals speculative positioning
        
        **C. Combined Flow** ✨ NEW: Z-Score Window Support
        - Shows total market flow: Retail + OTM Small Net Premium + OTM Large Net Premium
        - **Z-Score Window**: Now configurable (21-day or 60-day)
        - Provides comprehensive view of all buying/selling pressure
        - **Key Observations:**
          - Combines retail and institutional flow into single metric
          - Higher combined flow = higher total market conviction
          - Compare combined flow direction with stock price movement
          - Divergences may signal upcoming reversals
        
        **D. Z-Score Comparison**
        - Compares retail flow, options flow, and combined flow on normalized Z-score basis
        - **Three lines displayed:**
          - Blue: Retail Flow Z-Score
          - Red: Options Flow Z-Score
          - Green: Combined Flow Z-Score (Retail + Options)
        - **Key Observations:**
          - Divergence between retail and options suggests conflicting sentiment
          - Combined Z-score > 2 indicates extremely high activity
          - Correlation metric shows alignment between retail and institutional flows
        
        **E. MA Ratio Analysis - Retail**
        - Calculates 5-day MA / 21-day MA ratio for retail flow
        - **Interpretation (Updated Thresholds):**
          - Ratio > 1.5: Strong uptrend (short-term accelerating rapidly)
          - Ratio 1.0 - 1.5: Uptrend (short-term gaining momentum)
          - Ratio 0.5 - 1.0: Downtrend (short-term losing momentum)
          - Ratio < 0.5: Strong downtrend (short-term decelerating rapidly)
        
        **F. MA Ratio Analysis - Options Small**
        - Same as above but for small options trades (retail-sized)
        - Tracks shorter-term sentiment shifts
        
        **G. MA Ratio Analysis - Options Large**
        - Same as above but for large options trades (institutional-sized)
        - Tracks institutional positioning changes
        
        **H. MA Ratio Analysis - Combined**
        - Comprehensive momentum indicator combining all flow types
        - **Most comprehensive view** of market momentum
        - Combines: Retail + Options Small + Options Large
        
        ---
        
        ### 2. **Multi-Securities Comparison**
        Compare multiple securities side-by-side to identify relative strength and opportunities.
        
        #### Available Flow Types:
        
        **A. Retail Flow**
        - Compare retail activity across multiple stocks
        - Identify which securities are attracting retail interest
        
        **B. Options Flow**
        - Compare institutional options activity
        - Spot relative options positioning
        
        **C. Combined Flow**
        - Most comprehensive comparison
        - Combines Retail + Options Small OTM + Options Large OTM
        - Shows total market activity per security
        
        #### Metrics Available:
        - **Net Flow**: Dollar value comparison
        - **Z-Score**: Normalized activity level comparison
        
        ---
        
        ## 📈 Understanding the Metrics
        
        ### Activity Levels (Based on Z-Score)
        - 🔴 **Extreme Light** (Z < -1.5): Very low activity
        - 🟡 **Light** (-1.5 ≤ Z < -0.5): Below average activity
        - 🟢 **Neutral** (-0.5 ≤ Z < 0.5): Normal activity
        - 🟠 **Elevated** (0.5 ≤ Z < 1.5): Above average activity
        - 🔥 **Crowded** (Z ≥ 1.5): Extremely high activity (potential reversal signal)
        
        ### Z-Score Windows
        - **21-day window**: Better for short-term trading (default)
        - **60-day window**: Better for longer-term trends
        - **NEW**: Now available for Options Flow and Combined Flow analyses
        
        ### MA Ratio Signals (Updated Thresholds)
        - **> 1.5**: Strong uptrend (flow accelerating rapidly)
        - **1.0 - 1.5**: Uptrend (flow increasing steadily)
        - **0.5 - 1.0**: Downtrend (flow decreasing)
        - **< 0.5**: Strong downtrend (flow decelerating rapidly)
        
        ---
        
        ## 💡 Key Observations & Trading Insights
        
        ### 1. **Divergence Signals**
        - **Price up, Flow down**: Potential weakness, consider taking profits
        - **Price down, Flow up**: Potential accumulation, watch for reversal
        - **Retail buying, Options selling**: Smart money vs retail divergence
        
        ### 2. **Crowded Trade Warning**
        - Z-score > 2 often indicates overcrowded positioning
        - Historical precedent suggests potential for reversal
        - Consider contrarian positioning or reduce exposure
        
        ### 3. **Momentum Confirmation**
        - MA Ratio > 1.5 + Price trending up = Strong bullish confirmation
        - MA Ratio < 0.5 + Price trending down = Strong bearish confirmation
        - Look for alignment across all three MA analyses (Retail, Small, Large)
        
        ### 4. **Combined Flow Analysis**
        - Most comprehensive view of total market pressure
        - Use for conviction assessment: Higher combined flow = higher conviction
        - Compare combined Z-scores across securities to find relative opportunities
        
        ### 5. **Multi-Security Insights**
        - Use statistics table to rank securities by activity
        - Compare MA Ratios to find momentum leaders
        - Look for correlation patterns between related securities
        
        ---
        
        ## 📊 Multi-Security Statistics Table
        
        ### Column Descriptions:
        - **Activity Level**: Current Z-score based classification
        - **Latest Z-Score**: Standardized activity level
        - **Latest Value**: Most recent flow value
        - **Average**: Mean flow over the period
        - **Median**: Middle value (less affected by outliers)
        - **Std Dev**: Volatility measure
        - **Min/Max**: Range of values
        - **Total**: Cumulative flow
        - **Percentile**: Where current value ranks historically
        - **Volatility (CV)**: Coefficient of variation (risk measure)
        - **MA Ratio (5d/21d)**: Current momentum indicator
        - **Avg MA Ratio**: Average momentum over period
        - **MA Signal**: Momentum classification
        - **Price Δ 1W**: Stock price change over 1 week
        - **Price Δ 1M**: Stock price change over 1 month
        - **Days > Avg**: Number of days above average
        - **Days < Avg**: Number of days below average
        - **Data Points**: Total observations
        
        ---
        
        ## 📄 Report Generation - NEW: 4-Flow Report
        
        ### Comprehensive HTML Report
        Available for all Multi-Securities analyses, now includes **4 separate flow tables**:
        
        #### Table Structure:
        1. **Table 1: Retail Flow** - Retail investor activity
        2. **Table 2: Options OTM Small Net Premium** - Retail-sized options (NEW - separated)
        3. **Table 3: Options OTM Large Net Premium** - Institutional-sized options (NEW - separated)
        4. **Table 4: Combined Flow** - Total flow (Retail + Small + Large)
        
        #### Report Features:
        - Complete statistics for each ticker in each flow type
        - MA Ratio analysis and signals
        - Stock price changes (1W and 1M)
        - Activity level classifications
        - Downloadable HTML format for offline review
        
        **How to Generate:**
        1. Select "Multi Securities" view
        2. Choose any flow type
        3. Run analysis
        4. Click "Download 4-Flow HTML Report" button
        5. Open the downloaded HTML file in your browser
        
        ---
        
        ## ⚙️ Configuration Options
        
        ### Date Range
        - Default: 60 days (optimal for most analyses)
        - Adjust based on time horizon (longer for position trading, shorter for day trading)
        
        ### Z-Score Window ✨ ENHANCED
        - **21 days**: More responsive to recent changes (recommended for trading)
        - **60 days**: Smoother, better for longer-term analysis
        - **Now available for**: Stock Retail Flow, Options Flow, Combined Flow, Z-Score Comparison, and all MA Ratio analyses
        
        ### Transaction Type (Retail Flow)
        - **Combined**: Net flow (buy - sell)
        - **Buy**: Buy activity only
        - **Sell**: Sell activity only
        
        ### Moneyness (Options)
        - **OTM**: Out-of-the-money (speculative)
        - **ITM**: In-the-money (higher conviction)
        - **ATM**: At-the-money (delta hedging)
        
        ### Size (Options)
        - **Small**: Retail-sized trades
        - **Large**: Institutional-sized trades
        - **Combined**: All trades
        
        ---
        
        ## 🎓 Best Practices
        
        1. **Start with Combined Flow**: Get the full picture first
        2. **Check Z-Scores**: Understand relative activity levels
        3. **Verify with MA Ratio**: Confirm momentum direction
        4. **Compare Multiple Securities**: Find relative opportunities
        5. **Look for Divergences**: Often signal turning points
        6. **Monitor Crowded Trades**: Z > 2 = caution
        7. **Use 4-Flow Reports**: Compare retail vs institutional activity
        8. **Adjust Z-Score Windows**: Match window to your time horizon
        
        ---
        
        ## 🚨 Important Disclaimers
        
        - Flow data shows past activity, not future predictions
        - High activity doesn't guarantee price movement
        - Always use proper risk management
        - Consider multiple data sources for decisions
        - This tool is for analysis, not investment advice
        
        ---
        
        ## 📞 Support
        
        For questions or issues:
        - Check the guide first
        - Verify API keys are configured
        - Clear cache if data seems stale
        - Contact support team for technical issues
        
        ---
        
        **Version 1.3.2** | Enhanced Analytics Platform with Extended Z-Score Support
        """)


# ==========================================
# CONTROL PANEL
# ==========================================

st.markdown('<div class="control-panel">', unsafe_allow_html=True)
st.markdown('<h3>🎯 Analysis Configuration</h3>', unsafe_allow_html=True)

# First row of controls
col1, col2, col3, col4 = st.columns(4)

with col1:
    view_type = st.selectbox("View Type", ["Single Security", "Multi Securities"], label_visibility="collapsed")
    st.caption("📊 **View Type**")

with col2:
    if view_type == "Single Security":
        data_source = st.selectbox("Analysis Type", ["Stock Retail Flow", "Options Flow", "Combined Flow", "Z-Score Comparison", "MA Ratio Analysis - Retail", "MA Ratio Analysis - Options Small", "MA Ratio Analysis - Options Large", "MA Ratio Analysis - Combined"], label_visibility="collapsed")
    else:
        data_source = "Multi-Securities Comparison"
    st.caption("📈 **Analysis Type**")

with col3:
    today = date.today()
    to_date = st.date_input("To Date", today, label_visibility="collapsed")
    st.caption("📅 **To Date**")

with col4:
    default_from_date = today - timedelta(days=60)
    from_date = st.date_input("From Date", default_from_date, max_value=today-timedelta(days=1), label_visibility="collapsed")
    st.caption("📅 **From Date**")

# Second row of controls
col1, col2, col3, col4 = st.columns(4)

with col1:
    tickers_input = st.text_input("Tickers", 'AAPL', placeholder="AAPL, MSFT, GOOGL", label_visibility="collapsed")
    st.caption("🎯 **Target Tickers**")

with col2:
    if data_source == "Options Flow":
        st.session_state.moneyness_option = st.selectbox("Moneyness", ('OTM', 'ITM', 'ATM'), label_visibility="collapsed")
        st.caption("💰 **Moneyness**")
    elif data_source == "Stock Retail Flow":
        st.session_state.transaction_type = st.selectbox("Transaction Type", ('combined', 'buy', 'sell'), label_visibility="collapsed")
        st.caption("💱 **Transaction Type**")
    elif data_source in ["MA Ratio Analysis - Retail", "MA Ratio Analysis - Combined"]:
        st.session_state.transaction_type = st.selectbox("Transaction Type", ('combined', 'buy', 'sell'), label_visibility="collapsed")
        st.caption("💱 **Transaction Type**")
    else:
        st.empty()

with col3:
    if data_source == "Options Flow":
        st.session_state.size_option = st.selectbox("Size", ('small', 'large', 'combined'), label_visibility="collapsed")
        st.caption("📏 **Size**")
    elif data_source == "Multi-Securities Comparison":
        comparison_flow_type = st.selectbox("Flow Type", ('Retail Flow', 'Options Flow', 'Combined Flow'), label_visibility="collapsed")
        st.caption("🔄 **Flow Type**")
    elif data_source in ["Z-Score Comparison", "Stock Retail Flow", "Combined Flow", "MA Ratio Analysis - Retail", "MA Ratio Analysis - Options Small", "MA Ratio Analysis - Options Large", "MA Ratio Analysis - Combined"]:
        st.session_state.z_score_window = st.selectbox("Z-Score Window", (21, 60), label_visibility="collapsed")
        st.caption("📊 **Z-Score Window**")
    else:
        st.empty()

# Add Z-Score Window for Multi-Securities in col4
if data_source == "Multi-Securities Comparison":
    with col4:
        st.session_state.z_score_window = st.selectbox("Z-Score Window", (21, 60), label_visibility="collapsed", key="multi_z_score_window")
        st.caption("📊 **Z-Score Window**")

# Third row - Z-Score Window for Options Flow (CRITICAL FIX)
if data_source == "Options Flow":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.empty()
    with col2:
        st.empty()
    with col3:
        st.session_state.z_score_window = st.selectbox("Z-Score Window", (21, 60), label_visibility="collapsed", key="options_z_score_window")
        st.caption("📊 **Z-Score Window**")
    with col4:
        st.empty()

with col4:
    if data_source == "Options Flow":
        st.session_state.call_put_selection = st.selectbox("Call/Put/Net", ('call', 'put', 'net_premium'), index=2, label_visibility="collapsed")
        st.caption("📊 **Call/Put/Net**")
    elif data_source == "Multi-Securities Comparison":
        comparison_metric = st.selectbox("Metric", ('Net Flow', 'Z-Score'), label_visibility="collapsed")
        st.caption("📊 **Metric**")
    else:
        st.empty()

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ANALYSIS BUTTONS
# ==========================================

col1, col2, col3 = st.columns([6, 2, 2])

with col1:
    analyze_button = st.button("🚀 Start Analysis", type="primary", use_container_width=True)

with col2:
    if st.button("🗑️ Clear Cache", use_container_width=True, help="Clear all cached data"):
        st.cache_data.clear()
        st.success("✅ Cache cleared!")
        st.rerun()

with col3:
    if st.button("🔄 Reset Session", use_container_width=True, help="Reset all session variables"):
        for key in list(st.session_state.keys()):
            if key not in ['call_put_selection', 'transaction_type', 'moneyness_option', 'size_option', 'z_score_window']:
                del st.session_state[key]
        st.success("✅ Session reset!")
        st.rerun()

# ==========================================
# MAIN ANALYSIS EXECUTION
# ==========================================

if analyze_button:
    if not VANDATRACK_TOKEN:
        st.error("⚠️ VandaTrack API Key not configured")
    elif not tickers_input.strip():
        st.error("Please enter at least one ticker symbol")
    else:
        # SECURITY: Check rate limit before processing
        check_rate_limit(max_requests=50, window_minutes=60)
        
        ticker_list = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
        date_range = (to_date - from_date).days
        
        with st.spinner(f"🔄 Analyzing {len(ticker_list)} ticker(s) over {date_range} days..."):
            
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            
            # Route to appropriate analyzer
            if view_type == "Single Security":
                # Create analyzer instance (no alpha_vantage_key needed)
                analyzer = SingleSecurityAnalyzer(VANDATRACK_TOKEN)
                
                # Run analysis
                analyzer.analyze(
                    ticker_list,
                    from_date,
                    to_date,
                    data_source,
                    st.session_state.transaction_type if data_source in ["Stock Retail Flow", "MA Ratio Analysis - Retail", "MA Ratio Analysis - Combined"] else None,
                    st.session_state.moneyness_option if data_source == "Options Flow" else None,
                    st.session_state.size_option if data_source == "Options Flow" else None,
                    st.session_state.call_put_selection if data_source == "Options Flow" else None,
                    st.session_state.z_score_window
                )
            
            else:  # Multi Securities
                # Initialize (no alpha_vantage_key needed)
                multi_analyzer = MultiSecurityAnalyzer(
                    vandatrack_token=st.secrets["VANDATRACK_TOKEN"]
                )
                
                # Run analysis with z_score_window
                multi_analyzer.analyze(
                    ticker_list,
                    from_date,
                    to_date,
                    comparison_flow_type,
                    comparison_metric,
                    st.session_state.z_score_window
                )

# ==========================================
# STATUS INDICATORS
# ==========================================

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)

with col1:
    if VANDATRACK_TOKEN:
        st.markdown('<span class="status-chip success">✅ VandaTrack Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-chip error">❌ VandaTrack Disconnected</span>', unsafe_allow_html=True)

with col2:
    st.markdown('<span class="status-chip success">✅ Price Data: yfinance</span>', unsafe_allow_html=True)

with col3:
    st.markdown('<span class="status-chip success">✅ System Ready</span>', unsafe_allow_html=True)

# ==========================================
# FOOTER
# ==========================================

st.markdown("""
<div class="footer">
    <div style="font-size: 1.1rem; font-weight: 500; margin-bottom: 0.5rem;">
        🚀 Vandatrack Navigator v1.3.2
    </div>
    <div style="font-size: 0.875rem;">
        Powered by PMVectors | Enhanced Analytics Platform with 4-Flow Reports
    </div>
</div>
""", unsafe_allow_html=True)
