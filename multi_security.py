"""
Multi Security Analyzer Module - v4 with 4-Flow Report Structure
Enhanced: yfinance integration, 4 separate flow tables, configurable Z-Score Window
All issues resolved:
1. Combined flow correctly sums retail + options
2. Price changes show actual stock prices (not flow changes)
3. Uses yfinance instead of Alpha Vantage (no rate limits)
4. Activity levels consistent with single_security.py
5. 4-Flow HTML Report (Retail, Options Small, Options Large, Combined)
6. NEW: Configurable Z-Score Window (21-day or 60-day)
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
import time
from datetime import date, timedelta

class MultiSecurityAnalyzer:
    def __init__(self, vandatrack_token):
        self.vandatrack_token = vandatrack_token
        self.price_cache = {}
    
    def analyze(self, ticker_list, from_date, to_date, comparison_flow_type, comparison_metric, z_score_window=21):
        """Main analysis router for multi-security comparison"""
        
        st.info(f"Fetching {comparison_flow_type} data for multi-securities comparison (Z-Score: {z_score_window}d)...")
        
        if comparison_flow_type == 'Retail Flow':
            self.analyze_retail_comparison(ticker_list, from_date, to_date, comparison_metric, z_score_window)
        elif comparison_flow_type == 'Options Flow':
            self.analyze_options_comparison(ticker_list, from_date, to_date, comparison_metric, z_score_window)
        elif comparison_flow_type == 'Combined Flow':
            self.analyze_combined_comparison(ticker_list, from_date, to_date, comparison_metric, z_score_window)
    
    def analyze_retail_comparison(self, ticker_list, from_date, to_date, metric_type, z_score_window=21):
        """Analyze retail flow comparison across multiple securities"""
        
        data, status = self.fetch_stock_flow_data(ticker_list, from_date, to_date, 'combined')
        
        if status == "success" and data:
            st.success("Retail flow data fetched successfully!")
            combined_data = data.get('combined_data', data)
            
            comparison_records = []
            for ticker, date_values in combined_data.items():
                if isinstance(date_values, dict):
                    for date_str, value in date_values.items():
                        comparison_records.append({
                            'date': pd.to_datetime(date_str),
                            'ticker': ticker,
                            'value': value
                        })
            
            if comparison_records:
                df = pd.DataFrame(comparison_records).sort_values(['ticker', 'date'])
                
                self.display_comparison(df, 'Retail Flow', metric_type, z_score_window)
                self.display_statistics(df, 'Retail Flow', metric_type, from_date, to_date, z_score_window)
                self.display_latest_activity(df, metric_type, z_score_window)
                
                st.markdown("---")
                st.markdown("### Download Report")
                
                with st.spinner("Preparing report download..."):
                    html_report = self.generate_report_html(ticker_list, from_date, to_date, z_score_window)
                
                st.download_button(
                    label="📥 Download 4-Flow HTML Report",
                    data=html_report,
                    file_name=f"vandatrack_4flow_report_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    key="download_retail"
                )
                st.caption(f"✨ The report includes 4 separate flow tables with {z_score_window}-day Z-scores: Retail, Options Small, Options Large, and Combined")
            else:
                st.warning("No retail flow data found for comparison")
        else:
            st.error("Failed to fetch retail flow data")
    
    def analyze_options_comparison(self, ticker_list, from_date, to_date, metric_type, z_score_window=21):
        """Analyze options flow comparison across multiple securities"""
        
        data, status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'combined')
        
        if status == "success" and data:
            st.success("Options flow data fetched successfully!")
            
            call_data = data.get('call_data', {})
            put_data = data.get('put_data', {})
            
            net_records = self.calculate_net_premium_multi(call_data, put_data, ticker_list)
            
            if net_records:
                df = pd.DataFrame(net_records).sort_values(['ticker', 'date'])
                
                self.display_comparison(df, 'Options Flow', metric_type, z_score_window)
                self.display_statistics(df, 'Options Flow', metric_type, from_date, to_date, z_score_window)
                self.display_latest_activity(df, metric_type, z_score_window)
                
                st.markdown("---")
                st.markdown("### Download Report")
                
                with st.spinner("Preparing report download..."):
                    html_report = self.generate_report_html(ticker_list, from_date, to_date, z_score_window)
                
                st.download_button(
                    label="📥 Download 4-Flow HTML Report",
                    data=html_report,
                    file_name=f"vandatrack_4flow_report_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    key="download_options"
                )
                st.caption(f"✨ The report includes 4 separate flow tables with {z_score_window}-day Z-scores: Retail, Options Small, Options Large, and Combined")
            else:
                st.warning("No net premium data calculated")
        else:
            st.error("Failed to fetch options flow data")
    
    def analyze_combined_comparison(self, ticker_list, from_date, to_date, metric_type, z_score_window=21):
        """Analyze combined flow (Retail + Options Small + Large) across multiple securities"""
        
        st.info("Fetching Retail + Options Small + Large data...")
        
        retail_data, retail_status = self.fetch_stock_flow_data(ticker_list, from_date, to_date, 'combined')
        options_small_data, small_status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'small')
        options_large_data, large_status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'large')
        
        if retail_status == "success" and small_status == "success" and large_status == "success":
            st.success("All flow data (Retail + Options Small + Large) fetched successfully!")
            
            retail_flow = retail_data.get('combined_data', {})
            small_call = options_small_data.get('call_data', {})
            small_put = options_small_data.get('put_data', {})
            large_call = options_large_data.get('call_data', {})
            large_put = options_large_data.get('put_data', {})
            
            combined_records = self.calculate_combined_flow_multi(retail_flow, small_call, small_put, 
                                                                  large_call, large_put, ticker_list)
            
            if combined_records:
                df = pd.DataFrame(combined_records).sort_values(['ticker', 'date'])
                
                self.display_comparison(df, 'Combined Flow', metric_type, z_score_window)
                self.display_statistics(df, 'Combined Flow', metric_type, from_date, to_date, z_score_window)
                self.display_latest_activity(df, metric_type, z_score_window)
                
                st.markdown("---")
                st.markdown("### Download Report")
                
                with st.spinner("Preparing report download..."):
                    html_report = self.generate_report_html(ticker_list, from_date, to_date, z_score_window)
                
                st.download_button(
                    label="📥 Download 4-Flow HTML Report",
                    data=html_report,
                    file_name=f"vandatrack_4flow_report_{from_date.strftime('%Y%m%d')}_{to_date.strftime('%Y%m%d')}.html",
                    mime="text/html",
                    key="download_combined"
                )
                st.caption(f"✨ The report includes 4 separate flow tables with {z_score_window}-day Z-scores: Retail, Options Small, Options Large, and Combined")
            else:
                st.warning("No combined flow data calculated")
        else:
            st.error("Failed to fetch all required data for Combined Flow")
    
    def calculate_combined_flow_multi(self, retail_flow, small_call, small_put, large_call, large_put, ticker_list):
        """Calculate combined flow for multiple tickers"""
        combined_records = []
        
        for target_ticker in ticker_list:
            target_upper = target_ticker.upper()
            
            # Get retail flow
            retail_records = {}
            for ticker_key, date_values in retail_flow.items():
                ticker_key_upper = ticker_key.upper()
                if ticker_key_upper == target_upper:
                    if isinstance(date_values, dict):
                        retail_records = date_values
                        break
            
            # Aggregate options data
            small_call_records = {}
            small_put_records = {}
            large_call_records = {}
            large_put_records = {}
            
            # Process small calls
            for ticker_key, date_values in small_call.items():
                if isinstance(date_values, dict):
                    base_ticker = ticker_key.split('_')[-1].upper() if '_' in ticker_key else ticker_key.upper()
                    if (base_ticker == target_upper or 
                        ticker_key.upper() == target_upper or
                        ticker_key.upper().endswith(f"_{target_upper}") or
                        ticker_key.upper().startswith(f"{target_upper}_")):
                        
                        for date_str, value in date_values.items():
                            small_call_records[date_str] = small_call_records.get(date_str, 0) + value
            
            # Process small puts
            for ticker_key, date_values in small_put.items():
                if isinstance(date_values, dict):
                    base_ticker = ticker_key.split('_')[-1].upper() if '_' in ticker_key else ticker_key.upper()
                    if (base_ticker == target_upper or 
                        ticker_key.upper() == target_upper or
                        ticker_key.upper().endswith(f"_{target_upper}") or
                        ticker_key.upper().startswith(f"{target_upper}_")):
                        
                        for date_str, value in date_values.items():
                            small_put_records[date_str] = small_put_records.get(date_str, 0) + value
            
            # Process large calls
            for ticker_key, date_values in large_call.items():
                if isinstance(date_values, dict):
                    base_ticker = ticker_key.split('_')[-1].upper() if '_' in ticker_key else ticker_key.upper()
                    if (base_ticker == target_upper or 
                        ticker_key.upper() == target_upper or
                        ticker_key.upper().endswith(f"_{target_upper}") or
                        ticker_key.upper().startswith(f"{target_upper}_")):
                        
                        for date_str, value in date_values.items():
                            large_call_records[date_str] = large_call_records.get(date_str, 0) + value
            
            # Process large puts
            for ticker_key, date_values in large_put.items():
                if isinstance(date_values, dict):
                    base_ticker = ticker_key.split('_')[-1].upper() if '_' in ticker_key else ticker_key.upper()
                    if (base_ticker == target_upper or 
                        ticker_key.upper() == target_upper or
                        ticker_key.upper().endswith(f"_{target_upper}") or
                        ticker_key.upper().startswith(f"{target_upper}_")):
                        
                        for date_str, value in date_values.items():
                            large_put_records[date_str] = large_put_records.get(date_str, 0) + value
            
            # Combine all flows
            all_dates = (set(retail_records.keys()) | 
                        set(small_call_records.keys()) | set(small_put_records.keys()) |
                        set(large_call_records.keys()) | set(large_put_records.keys()))
            
            for date_str in all_dates:
                retail_val = retail_records.get(date_str, 0)
                small_net = small_call_records.get(date_str, 0) - small_put_records.get(date_str, 0)
                large_net = large_call_records.get(date_str, 0) - large_put_records.get(date_str, 0)
                combined_flow = retail_val + small_net + large_net
                
                combined_records.append({
                    'date': pd.to_datetime(date_str),
                    'ticker': target_ticker,
                    'value': combined_flow
                })
        
        return combined_records
    
    def display_comparison(self, df, flow_label, metric_type, z_score_window=21):
        """Display comparison chart"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-title">Multi-Securities {flow_label} {metric_type} (Z-Score: {z_score_window}d)</div>',
                   unsafe_allow_html=True)
        
        if metric_type == 'Z-Score':
            for ticker in df['ticker'].unique():
                ticker_data = df[df['ticker'] == ticker]['value']
                z_scores = self.calculate_z_scores(ticker_data, window=z_score_window)
                df.loc[df['ticker'] == ticker, 'z_score'] = z_scores
            
            self.create_z_score_comparison_chart(df, flow_label, z_score_window)
        else:
            self.create_net_flow_comparison_chart(df, flow_label)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def create_z_score_comparison_chart(self, df, flow_label, z_score_window=21):
        """Create Z-score comparison chart"""
        fig = go.Figure()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        for i, ticker in enumerate(df['ticker'].unique()):
            ticker_data = df[df['ticker'] == ticker]
            fig.add_trace(go.Scatter(
                x=ticker_data['date'],
                y=ticker_data['z_score'],
                mode='lines+markers',
                name=f'{ticker} {flow_label} Z-Score',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=6)
            ))
        
        fig.add_hline(y=0, line_dash="dot", line_color="gray", annotation_text="Mean")
        fig.add_hline(y=2, line_dash="dash", line_color="orange", opacity=0.7)
        fig.add_hline(y=-2, line_dash="dash", line_color="orange", opacity=0.7)
        
        fig.update_layout(
            title=f'Multi-Securities {flow_label} Z-Score Comparison ({z_score_window}d window)',
            xaxis_title='Date',
            yaxis_title='Z-Score',
            height=600,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def create_net_flow_comparison_chart(self, df, flow_label):
        """Create net flow comparison chart"""
        fig = go.Figure()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        for i, ticker in enumerate(df['ticker'].unique()):
            ticker_data = df[df['ticker'] == ticker]
            fig.add_trace(go.Scatter(
                x=ticker_data['date'],
                y=ticker_data['value'],
                mode='lines+markers',
                name=f'{ticker} {flow_label}',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=6)
            ))
        
        y_label = 'Net Flow ($)' if 'Retail' in flow_label or 'Combined' in flow_label else 'Net Premium ($)'
        
        fig.update_layout(
            title=f'Multi-Securities {flow_label} Comparison',
            xaxis_title='Date',
            yaxis_title=y_label,
            height=600,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def display_statistics(self, df, flow_type, metric_type, from_date, to_date, z_score_window=21):
        """Display comprehensive statistics table with MA Ratio and price changes"""
        st.markdown(f"### Multi-Securities Statistics Summary (Z-Score: {z_score_window}d)")
        
        stats_data = []
        for ticker in df['ticker'].unique():
            ticker_data = df[df['ticker'] == ticker]
            if len(ticker_data) > 0:
                values = ticker_data['value']
                
                latest_flow = values.iloc[-1]
                avg_flow = values.mean()
                median_flow = values.median()
                std_flow = values.std()
                min_flow = values.min()
                max_flow = values.max()
                total_flow = values.sum()
                
                if metric_type == 'Z-Score' and 'z_score' in ticker_data.columns:
                    z_scores = ticker_data['z_score']
                    latest_z = z_scores.iloc[-1]
                else:
                    # Use configurable window for Z-score calculation
                    z_scores = self.calculate_z_scores(values, window=z_score_window)
                    latest_z = z_scores.iloc[-1]
                
                percentile = (np.sum(values <= latest_flow) / len(values)) * 100
                level, emoji = self.classify_activity_level(latest_z)
                above_avg_days = np.sum(values > avg_flow)
                below_avg_days = np.sum(values < avg_flow)
                cv = (std_flow / abs(avg_flow)) * 100 if avg_flow != 0 else 0
                
                # Calculate MA Ratio
                ticker_df = ticker_data.sort_values('date').copy()
                ticker_df['ma_5'] = ticker_df['value'].rolling(window=5, min_periods=1).mean()
                ticker_df['ma_21'] = ticker_df['value'].rolling(window=21, min_periods=1).mean()
                ticker_df['ma_ratio'] = ticker_df['ma_5'] / ticker_df['ma_21'].replace(0, np.nan)
                ticker_df['ma_ratio'] = ticker_df['ma_ratio'].fillna(1)
                
                latest_ma_ratio = ticker_df['ma_ratio'].iloc[-1]
                avg_ma_ratio = ticker_df['ma_ratio'].mean()
                
                if latest_ma_ratio > 1.5:
                    ma_signal = "Strong Up"
                elif latest_ma_ratio >= 1.0:
                    ma_signal = "Uptrend"
                elif latest_ma_ratio >= 0.5:
                    ma_signal = "Downtrend"
                else:
                    ma_signal = "Strong Down"
                
                # Get price changes
                price_1w_display, price_1m_display = self.get_stock_price_changes_display(ticker, from_date, to_date)
                
                stats_data.append({
                    'Ticker': ticker,
                    'Activity Level': f"{emoji} {level}",
                    'Latest Z-Score': f"{latest_z:.2f}",
                    'Latest Value': f"${latest_flow:,.0f}",
                    'Average': f"${avg_flow:,.0f}",
                    'Median': f"${median_flow:,.0f}",
                    'Std Dev': f"${std_flow:,.0f}",
                    'Min': f"${min_flow:,.0f}",
                    'Max': f"${max_flow:,.0f}",
                    'Total': f"${total_flow:,.0f}",
                    'Percentile': f"{percentile:.1f}%",
                    'Volatility (CV)': f"{cv:.1f}%",
                    'MA Ratio (5d/21d)': f"{latest_ma_ratio:.3f}",
                    'Avg MA Ratio': f"{avg_ma_ratio:.3f}",
                    'MA Signal': ma_signal,
                    'Price Δ 1W': price_1w_display,
                    'Price Δ 1M': price_1m_display,
                    'Days > Avg': above_avg_days,
                    'Days < Avg': below_avg_days,
                    'Data Points': len(values)
                })
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    def display_latest_activity(self, df, metric_type, z_score_window=21):
        """Display latest activity levels for each ticker"""
        st.markdown(f"### Latest Activity Levels (Z-Score: {z_score_window}d)")
        
        tickers = df['ticker'].unique()
        cols = st.columns(min(len(tickers), 4))
        
        for i, ticker in enumerate(tickers):
            if i < len(cols):
                ticker_data = df[df['ticker'] == ticker]
                if len(ticker_data) > 0:
                    if metric_type == 'Z-Score' and 'z_score' in ticker_data.columns:
                        latest_z = ticker_data['z_score'].iloc[-1]
                    else:
                        values = ticker_data['value']
                        # Use configurable window for Z-score calculation
                        z_scores = self.calculate_z_scores(values, window=z_score_window)
                        latest_z = z_scores.iloc[-1]
                    
                    level, emoji = self.classify_activity_level(latest_z)
                    latest_value = ticker_data['value'].iloc[-1]
                    
                    with cols[i % len(cols)]:
                        st.metric(f"{ticker}", f"{emoji} {level}", f"Z: {latest_z:.2f}")
                        st.caption(f"${latest_value:,.0f}")
    
    def generate_report_html(self, ticker_list, from_date, to_date, z_score_window=21):
        """Generate HTML report with 4 separate flow tables"""
        
        # Fetch RETAIL data
        retail_data, _ = self.fetch_stock_flow_data(ticker_list, from_date, to_date, 'combined')
        retail_flow = retail_data.get('combined_data', {})
        retail_records = []
        for ticker, date_values in retail_flow.items():
            if isinstance(date_values, dict):
                for date_str, value in date_values.items():
                    retail_records.append({'date': pd.to_datetime(date_str), 'ticker': ticker, 'value': value})
        retail_df = pd.DataFrame(retail_records).sort_values(['ticker', 'date']) if retail_records else pd.DataFrame()
        
        # Fetch OPTIONS SMALL data separately
        options_small_data, _ = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'small')
        small_call = options_small_data.get('call_data', {})
        small_put = options_small_data.get('put_data', {})
        options_small_records = self.calculate_net_premium_multi(small_call, small_put, ticker_list)
        options_small_df = pd.DataFrame(options_small_records).sort_values(['ticker', 'date']) if options_small_records else pd.DataFrame()
        
        # Fetch OPTIONS LARGE data separately
        options_large_data, _ = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'large')
        large_call = options_large_data.get('call_data', {})
        large_put = options_large_data.get('put_data', {})
        options_large_records = self.calculate_net_premium_multi(large_call, large_put, ticker_list)
        options_large_df = pd.DataFrame(options_large_records).sort_values(['ticker', 'date']) if options_large_records else pd.DataFrame()
        
        # Calculate COMBINED flow
        combined_records = self.calculate_combined_flow_multi(retail_flow, small_call, small_put, large_call, large_put, ticker_list)
        combined_df = pd.DataFrame(combined_records).sort_values(['ticker', 'date']) if combined_records else pd.DataFrame()
        
        return self.create_html_report(retail_df, options_small_df, options_large_df, combined_df, ticker_list, from_date, to_date, z_score_window)
    
    def create_html_report(self, retail_df, options_small_df, options_large_df, combined_df, ticker_list, from_date, to_date, z_score_window=21):
        """Create HTML report with FOUR separate tables"""
        
        report_date = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>VandaTrack 4-Flow Analysis Report ({z_score_window}d Z-Score)</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    max-width: 1400px;
                    margin: 0 auto;
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #1a73e8 0%, #4285f4 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 2.5rem;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    opacity: 0.95;
                    font-size: 1.1rem;
                }}
                .z-score-badge {{
                    display: inline-block;
                    background: rgba(255,255,255,0.2);
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    margin-top: 10px;
                    font-size: 0.95rem;
                }}
                .section {{
                    margin: 50px 0;
                    page-break-inside: avoid;
                }}
                .section h2 {{
                    color: #1a73e8;
                    border-bottom: 3px solid #1a73e8;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                    font-size: 1.8rem;
                }}
                .flow-badge {{
                    display: inline-block;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 600;
                    margin-left: 15px;
                    font-size: 0.9rem;
                }}
                .retail-badge {{
                    background: #e3f2fd;
                    color: #1976d2;
                }}
                .options-small-badge {{
                    background: #f3e5f5;
                    color: #7b1fa2;
                }}
                .options-large-badge {{
                    background: #fff3e0;
                    color: #ef6c00;
                }}
                .combined-badge {{
                    background: #e8f5e9;
                    color: #388e3c;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                th {{
                    background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 14px 10px;
                    text-align: left;
                    font-weight: 600;
                    border: 1px solid #dee2e6;
                    font-size: 0.85rem;
                    color: #495057;
                    position: sticky;
                    top: 0;
                }}
                td {{
                    padding: 12px 10px;
                    border: 1px solid #dee2e6;
                    font-size: 0.9rem;
                }}
                tr:nth-child(even) {{
                    background: #f8f9fa;
                }}
                tr:hover {{
                    background: #e3f2fd;
                    transition: background 0.2s;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }}
                .summary-item {{
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    border: 1px solid #dee2e6;
                }}
                .summary-item .label {{
                    font-size: 0.75rem;
                    color: #6c757d;
                    text-transform: uppercase;
                    font-weight: 600;
                    letter-spacing: 1px;
                    margin-bottom: 8px;
                }}
                .summary-item .value {{
                    font-size: 1.8rem;
                    font-weight: 700;
                    color: #1a73e8;
                }}
                .footer {{
                    margin-top: 60px;
                    padding-top: 30px;
                    border-top: 2px solid #dee2e6;
                    text-align: center;
                    color: #6c757d;
                }}
                .ticker-symbol {{
                    font-weight: 700;
                    color: #1a73e8;
                    font-size: 1.05rem;
                }}
                @media print {{
                    .section {{
                        page-break-after: always;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>VandaTrack 4-Flow Analysis Report</h1>
                    <p>Comprehensive Multi-Security Flow Comparison</p>
                    <div class="z-score-badge">Z-Score Window: {z_score_window} days</div>
                    <p style="font-size: 1rem; margin-top: 15px;">
                        <strong>Period:</strong> {from_date.strftime('%B %d, %Y')} to {to_date.strftime('%B %d, %Y')} 
                        ({(to_date - from_date).days} days)
                    </p>
                    <p style="font-size: 0.95rem;"><strong>Generated:</strong> {report_date}</p>
                </div>
                
                <div class="summary-grid">
                    <div class="summary-item">
                        <div class="label">Securities Analyzed</div>
                        <div class="value">{len(ticker_list)}</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">Flow Types</div>
                        <div class="value">4</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">Z-Score Window</div>
                        <div class="value">{z_score_window}d</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">Tickers</div>
                        <div class="value" style="font-size: 1.2rem;">{', '.join(ticker_list)}</div>
                    </div>
                </div>
        """
        
        # TABLE 1: RETAIL FLOW
        if not retail_df.empty:
            html += f"""
                <div class="section">
                    <h2>
                        <span>Table 1: Retail Flow Analysis</span>
                        <span class="flow-badge retail-badge">RETAIL</span>
                    </h2>
                    <p style="color: #6c757d; font-size: 1rem; margin-bottom: 20px;">
                        Retail investor buying and selling activity. Net flow represents combined buy-sell pressure.
                    </p>
                    {self.generate_flow_table_html(retail_df, "Retail", from_date, to_date, z_score_window)}
                </div>
            """
        
        # TABLE 2: OPTIONS SMALL
        if not options_small_df.empty:
            html += f"""
                <div class="section">
                    <h2>
                        <span>Table 2: Options OTM Small Net Premium</span>
                        <span class="flow-badge options-small-badge">OPTIONS SMALL</span>
                    </h2>
                    <p style="color: #6c757d; font-size: 1rem; margin-bottom: 20px;">
                        Retail-sized options positions. Net Premium = Small Call Premium - Small Put Premium.
                    </p>
                    {self.generate_flow_table_html(options_small_df, "Options Small", from_date, to_date, z_score_window)}
                </div>
            """
        
        # TABLE 3: OPTIONS LARGE
        if not options_large_df.empty:
            html += f"""
                <div class="section">
                    <h2>
                        <span>Table 3: Options OTM Large Net Premium</span>
                        <span class="flow-badge options-large-badge">OPTIONS LARGE</span>
                    </h2>
                    <p style="color: #6c757d; font-size: 1rem; margin-bottom: 20px;">
                        Institutional-sized options positions. Net Premium = Large Call Premium - Large Put Premium.
                    </p>
                    {self.generate_flow_table_html(options_large_df, "Options Large", from_date, to_date, z_score_window)}
                </div>
            """
        
        # TABLE 4: COMBINED FLOW
        if not combined_df.empty:
            html += f"""
                <div class="section">
                    <h2>
                        <span>Table 4: Combined Flow Analysis</span>
                        <span class="flow-badge combined-badge">COMBINED</span>
                    </h2>
                    <p style="color: #6c757d; font-size: 1rem; margin-bottom: 20px;">
                        Total market flow combining Retail + Options Small OTM Net Premium + Options Large OTM Net Premium.
                    </p>
                    {self.generate_flow_table_html(combined_df, "Combined", from_date, to_date, z_score_window)}
                </div>
            """
        
        html += f"""
                <div class="footer">
                    <h3 style="color: #1a73e8; margin-bottom: 15px;">VandaTrack Navigator v1.3.2 - 4-Flow Edition</h3>
                    <p style="font-size: 1rem; margin-bottom: 10px;">
                        <strong>Report Summary:</strong> {len(ticker_list)} securities analyzed across 4 flow types with {z_score_window}-day Z-scores
                    </p>
                    <p style="font-size: 0.9rem;">
                        Powered by PMVectors | Advanced Flow Analytics Platform
                    </p>
                    <p style="font-size: 0.85rem; color: #adb5bd; margin-top: 20px;">
                        This report is for informational purposes only and does not constitute investment advice.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def generate_flow_table_html(self, df, flow_type, from_date, to_date, z_score_window=21):
        """Generate HTML table for a specific flow type"""
        
        stats_rows = ""
        for ticker in df['ticker'].unique():
            ticker_data = df[df['ticker'] == ticker]
            if len(ticker_data) > 0:
                values = ticker_data['value']
                
                latest_flow = values.iloc[-1]
                avg_flow = values.mean()
                median_flow = values.median()
                std_flow = values.std()
                min_flow = values.min()
                max_flow = values.max()
                total_flow = values.sum()
                
                # Use configurable window for Z-score calculation
                z_scores = self.calculate_z_scores(values, window=z_score_window)
                latest_z = z_scores.iloc[-1]
                
                percentile = (np.sum(values <= latest_flow) / len(values)) * 100
                level, emoji = self.classify_activity_level(latest_z)
                
                ticker_df = ticker_data.sort_values('date').copy()
                ticker_df['ma_5'] = ticker_df['value'].rolling(window=5, min_periods=1).mean()
                ticker_df['ma_21'] = ticker_df['value'].rolling(window=21, min_periods=1).mean()
                ticker_df['ma_ratio'] = ticker_df['ma_5'] / ticker_df['ma_21'].replace(0, np.nan)
                ticker_df['ma_ratio'] = ticker_df['ma_ratio'].fillna(1)
                
                latest_ma_ratio = ticker_df['ma_ratio'].iloc[-1]
                avg_ma_ratio = ticker_df['ma_ratio'].mean()
                
                if latest_ma_ratio > 1.5:
                    ma_signal = "🚀 Strong Up"
                elif latest_ma_ratio >= 1.0:
                    ma_signal = "📈 Uptrend"
                elif latest_ma_ratio >= 0.5:
                    ma_signal = "📉 Downtrend"
                else:
                    ma_signal = "⚠️ Strong Down"
                
                # Get HTML-formatted price changes for report
                price_1w_html, price_1m_html = self.get_stock_price_changes_html(ticker, from_date, to_date)
                
                row_color = ""
                if "Crowded" in level:
                    row_color = 'style="background: #ffebee;"'
                elif "Elevated" in level:
                    row_color = 'style="background: #fff3e0;"'
                
                stats_rows += f"""
                    <tr {row_color}>
                        <td class="ticker-symbol">{ticker}</td>
                        <td>{emoji} {level}</td>
                        <td><strong>{latest_z:.2f}</strong></td>
                        <td><strong>${latest_flow:,.0f}</strong></td>
                        <td>${avg_flow:,.0f}</td>
                        <td>${median_flow:,.0f}</td>
                        <td>${std_flow:,.0f}</td>
                        <td>${min_flow:,.0f}</td>
                        <td>${max_flow:,.0f}</td>
                        <td>${total_flow:,.0f}</td>
                        <td>{percentile:.1f}%</td>
                        <td><strong>{latest_ma_ratio:.3f}</strong></td>
                        <td>{avg_ma_ratio:.3f}</td>
                        <td>{ma_signal}</td>
                        <td>{price_1w_html}</td>
                        <td>{price_1m_html}</td>
                        <td>{len(values)}</td>
                    </tr>
                """
        
        html = f"""
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Activity Level</th>
                        <th>Z-Score ({z_score_window}d)</th>
                        <th>Latest Value</th>
                        <th>Average</th>
                        <th>Median</th>
                        <th>Std Dev</th>
                        <th>Min</th>
                        <th>Max</th>
                        <th>Total Flow</th>
                        <th>Percentile</th>
                        <th>MA Ratio</th>
                        <th>Avg MA</th>
                        <th>MA Signal</th>
                        <th>Price Δ 1W</th>
                        <th>Price Δ 1M</th>
                        <th>Points</th>
                    </tr>
                </thead>
                <tbody>
                    {stats_rows}
                </tbody>
            </table>
        """
        
        return html
    
    def get_stock_price_changes_display(self, ticker, from_date, to_date):
        """Get price changes for Streamlit display (with emojis)"""
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        if not stock_prices or len(stock_prices) < 2:
            return "N/A", "N/A"
        
        price_list = sorted([(pd.to_datetime(d), p) for d, p in stock_prices.items()])
        
        if len(price_list) < 2:
            return "N/A", "N/A"
        
        latest_price = price_list[-1][1]
        
        # 1 week
        if len(price_list) >= 6:
            week_ago_price = price_list[-6][1]
            week_change = ((latest_price - week_ago_price) / week_ago_price * 100)
            if week_change > 0:
                price_1w = f"🟢 +{week_change:.1f}%"
            elif week_change < 0:
                price_1w = f"🔴 {week_change:.1f}%"
            else:
                price_1w = "⚪ 0.0%"
        else:
            price_1w = "N/A"
        
        # 1 month
        if len(price_list) >= 22:
            month_ago_price = price_list[-22][1]
            month_change = ((latest_price - month_ago_price) / month_ago_price * 100)
            if month_change > 0:
                price_1m = f"🟢 +{month_change:.1f}%"
            elif month_change < 0:
                price_1m = f"🔴 {month_change:.1f}%"
            else:
                price_1m = "⚪ 0.0%"
        else:
            price_1m = "N/A"
        
        return price_1w, price_1m
    
    def get_stock_price_changes_html(self, ticker, from_date, to_date):
        """Get price changes for HTML report (with colored spans)"""
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        if not stock_prices or len(stock_prices) < 2:
            return "N/A", "N/A"
        
        price_list = sorted([(pd.to_datetime(d), p) for d, p in stock_prices.items()])
        
        if len(price_list) < 2:
            return "N/A", "N/A"
        
        latest_price = price_list[-1][1]
        
        # 1 week
        if len(price_list) >= 6:
            week_ago_price = price_list[-6][1]
            week_change = ((latest_price - week_ago_price) / week_ago_price * 100)
            if week_change > 0:
                price_1w = f'<span style="color: #28a745;">+{week_change:.1f}%</span>'
            elif week_change < 0:
                price_1w = f'<span style="color: #dc3545;">{week_change:.1f}%</span>'
            else:
                price_1w = "0.0%"
        else:
            price_1w = "N/A"
        
        # 1 month
        if len(price_list) >= 22:
            month_ago_price = price_list[-22][1]
            month_change = ((latest_price - month_ago_price) / month_ago_price * 100)
            if month_change > 0:
                price_1m = f'<span style="color: #28a745;">+{month_change:.1f}%</span>'
            elif month_change < 0:
                price_1m = f'<span style="color: #dc3545;">{month_change:.1f}%</span>'
            else:
                price_1m = "0.0%"
        else:
            price_1m = "N/A"
        
        return price_1w, price_1m
    
    def fetch_stock_price_data_improved(self, ticker, from_date, to_date):
        """Fetch stock prices using yfinance (no rate limits)"""
        
        cache_key = f"{ticker}_{from_date}_{to_date}"
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            df = stock.history(start=from_date, end=to_date + timedelta(days=1))
            
            if df.empty:
                return {}
            
            price_dict = {}
            for date_idx, row in df.iterrows():
                date_str = date_idx.strftime('%Y-%m-%d')
                price_dict[date_str] = float(row['Close'])
            
            if price_dict:
                self.price_cache[cache_key] = price_dict
            
            return price_dict
            
        except Exception:
            return {}
    
    def fetch_stock_flow_data(self, tickers, from_date, to_date, transaction_type):
        """Fetch stock retail flow data"""
        if not self.vandatrack_token:
            return {}, "No token provided"
        
        url = 'https://www.vandatrack.com/tickers/api/'
        
        if transaction_type == 'combined':
            combined_data = {}
            
            for ticker in tickers:
                params = {
                    'auth_token': self.vandatrack_token,
                    'tickers': ticker,
                    'from_date': from_date.strftime('%Y-%m-%d'),
                    'to_date': to_date.strftime('%Y-%m-%d')
                }
                
                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            combined_data.update(data)
                except:
                    pass
                
                time.sleep(0.5)
            
            return {'combined_data': combined_data}, "success"
        else:
            return {}, "Not implemented"
    
    def fetch_options_data_fixed(self, tickers, from_date, to_date, moneyness, size):
        """Fetch options data with fix for combined size"""
        if not self.vandatrack_token:
            return {}, "No token provided"
        
        url = 'https://www.vandatrack.com/option/api/'
        
        base_params = {
            'auth_token': self.vandatrack_token,
            'tickers': tickers,
            'saved_list': 'false',
            'from_date': from_date.strftime('%Y-%m-%d'),
            'to_date': to_date.strftime('%Y-%m-%d'),
            'moneyness': moneyness
        }
        
        if size == 'combined':
            combined_call_data = {}
            combined_put_data = {}
            
            for size_type in ['small', 'large']:
                call_params = {**base_params, 'callput': 'call', 'size': size_type}
                put_params = {**base_params, 'callput': 'put', 'size': size_type}
                
                call_response = self.force_api_call(url, call_params)
                put_response = self.force_api_call(url, put_params)
                
                for ticker_key, date_values in call_response.items():
                    if isinstance(date_values, dict):
                        if ticker_key not in combined_call_data:
                            combined_call_data[ticker_key] = {}
                        for date_str, value in date_values.items():
                            if date_str not in combined_call_data[ticker_key]:
                                combined_call_data[ticker_key][date_str] = 0
                            combined_call_data[ticker_key][date_str] += value
                
                for ticker_key, date_values in put_response.items():
                    if isinstance(date_values, dict):
                        if ticker_key not in combined_put_data:
                            combined_put_data[ticker_key] = {}
                        for date_str, value in date_values.items():
                            if date_str not in combined_put_data[ticker_key]:
                                combined_put_data[ticker_key][date_str] = 0
                            combined_put_data[ticker_key][date_str] += value
                
                time.sleep(1)
            
            return {"call_data": combined_call_data, "put_data": combined_put_data}, "success"
        else:
            call_params = {**base_params, 'callput': 'call', 'size': size}
            put_params = {**base_params, 'callput': 'put', 'size': size}
            
            call_data = self.force_api_call(url, call_params)
            time.sleep(0.5)
            put_data = self.force_api_call(url, put_params)
            
            return {"call_data": call_data, "put_data": put_data}, "success"
    
    def force_api_call(self, url, params):
        """Make API call with error handling"""
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data if data else {}
            else:
                return {}
        except Exception:
            return {}
    
    def calculate_net_premium_multi(self, call_data, put_data, ticker_list):
        """Calculate net premium for multiple tickers"""
        net_records = []
        
        for target_ticker in ticker_list:
            target_upper = target_ticker.upper()
            
            ticker_call_data = {}
            for ticker_key, date_values in call_data.items():
                if isinstance(date_values, dict):
                    base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                    
                    if (base_ticker.upper() == target_upper or 
                        ticker_key.upper() == target_upper or
                        ticker_key.upper().endswith(f"_{target_upper}") or
                        ticker_key.upper().startswith(f"{target_upper}_")):
                        
                        for date_str, value in date_values.items():
                            if date_str not in ticker_call_data:
                                ticker_call_data[date_str] = 0
                            ticker_call_data[date_str] += value
            
            ticker_put_data = {}
            for ticker_key, date_values in put_data.items():
                if isinstance(date_values, dict):
                    base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                    
                    if (base_ticker.upper() == target_upper or 
                        ticker_key.upper() == target_upper or
                        ticker_key.upper().endswith(f"_{target_upper}") or
                        ticker_key.upper().startswith(f"{target_upper}_")):
                        
                        for date_str, value in date_values.items():
                            if date_str not in ticker_put_data:
                                ticker_put_data[date_str] = 0
                            ticker_put_data[date_str] += value
            
            all_dates = set(ticker_call_data.keys()) | set(ticker_put_data.keys())
            
            for date_str in all_dates:
                call_value = ticker_call_data.get(date_str, 0)
                put_value = ticker_put_data.get(date_str, 0)
                net_premium = call_value - put_value
                
                net_records.append({
                    'date': pd.to_datetime(date_str),
                    'ticker': target_ticker,
                    'value': net_premium,
                    'call_value': call_value,
                    'put_value': put_value
                })
        
        return net_records
    
    def calculate_z_scores(self, data_series, window=None):
        """Calculate z-scores"""
        if len(data_series) <= 1:
            return pd.Series([0] * len(data_series), index=data_series.index)
        
        if window and len(data_series) >= window:
            rolling_mean = data_series.rolling(window=window, min_periods=1).mean()
            rolling_std = data_series.rolling(window=window, min_periods=1).std()
            z_scores = (data_series - rolling_mean) / rolling_std
            z_scores = z_scores.fillna(0)
            return z_scores
        else:
            mean_val, std_val = data_series.mean(), data_series.std()
            if std_val == 0:
                return pd.Series([0] * len(data_series), index=data_series.index)
            return (data_series - mean_val) / std_val
    
    def classify_activity_level(self, z_score):
        """Classify activity level based on Z-score"""
        if z_score < -1.5:
            return "Extreme Light", "🔴"
        elif -1.5 <= z_score < -0.5:
            return "Light", "🟡"
        elif -0.5 <= z_score < 0.5:
            return "Neutral", "🟢"
        elif 0.5 <= z_score < 1.5:
            return "Elevated", "🟠"
        else:
            return "Crowded", "🔥"
