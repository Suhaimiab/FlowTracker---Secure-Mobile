"""
Single Security Analyzer Module
Handles Stock Retail Flow, Options Flow, and Z-Score Comparison
Enhanced: 60-day default, Z-score windows, MA Ratio Analysis
Updated: yfinance integration (no rate limits), Z-score window for Options & Combined Flow
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta

class SingleSecurityAnalyzer:
    def __init__(self, vandatrack_token):
        self.vandatrack_token = vandatrack_token
        self.price_cache = {}
    
    def analyze(self, ticker_list, from_date, to_date, data_source, 
                transaction_type=None, moneyness=None, size=None, call_put_selection=None, z_score_window=21):
        """Main analysis router"""
        
        if data_source == "Stock Retail Flow":
            self.analyze_stock_flow(ticker_list, from_date, to_date, transaction_type, z_score_window)
        elif data_source == "Options Flow":
            self.analyze_options_flow(ticker_list, from_date, to_date, moneyness, size, call_put_selection, z_score_window)
        elif data_source == "Combined Flow":
            self.analyze_combined_flow(ticker_list, from_date, to_date, z_score_window)
        elif data_source == "Z-Score Comparison":
            self.analyze_z_score_comparison(ticker_list, from_date, to_date, z_score_window)
        elif data_source == "MA Ratio Analysis - Retail":
            self.analyze_ma_ratio_retail(ticker_list, from_date, to_date, transaction_type, z_score_window)
        elif data_source == "MA Ratio Analysis - Options Small":
            self.analyze_ma_ratio_options(ticker_list, from_date, to_date, 'small', z_score_window)
        elif data_source == "MA Ratio Analysis - Options Large":
            self.analyze_ma_ratio_options(ticker_list, from_date, to_date, 'large', z_score_window)
        elif data_source == "MA Ratio Analysis - Combined":
            self.analyze_ma_ratio_combined(ticker_list, from_date, to_date, transaction_type, z_score_window)
    
    # ==========================================
    # STOCK RETAIL FLOW ANALYSIS
    # ==========================================
    
    def analyze_stock_flow(self, ticker_list, from_date, to_date, transaction_type, z_score_window=21):
        """Analyze stock retail flow"""
        
        stock_data, status = self.fetch_stock_flow_data(ticker_list, from_date, to_date, transaction_type)
        
        if status == "success" and stock_data:
            st.success("Stock flow data fetched successfully!")
            
            if transaction_type == 'combined':
                combined_data = stock_data.get('combined_data', {})
                buy_data = stock_data.get('buy_data', {})
                sell_data = stock_data.get('sell_data', {})
                
                records = []
                for data_dict, data_type in [(combined_data, 'Combined'), 
                                            (buy_data, 'Buy'), 
                                            (sell_data, 'Sell')]:
                    for ticker, date_values in data_dict.items():
                        if isinstance(date_values, dict):
                            for date_str, value in date_values.items():
                                records.append({
                                    'date': pd.to_datetime(date_str),
                                    'ticker': ticker,
                                    'net_flow': value,
                                    'type': data_type
                                })
            else:
                records = []
                for ticker, date_values in stock_data.items():
                    if isinstance(date_values, dict):
                        for date_str, value in date_values.items():
                            records.append({
                                'date': pd.to_datetime(date_str),
                                'ticker': ticker,
                                'net_flow': value,
                                'type': transaction_type.title()
                            })
            
            if records:
                df = pd.DataFrame(records).sort_values(['ticker', 'date'])
                for ticker in df['ticker'].unique():
                    self.display_stock_flow_chart(df, ticker, transaction_type, from_date, to_date, z_score_window)
            else:
                st.warning("No data records found after processing")
        else:
            st.error(f"Failed to fetch stock data: {status}")
    
    def display_stock_flow_chart(self, df, ticker, transaction_type, from_date, to_date, z_score_window=21):
        """Display stock flow chart with metrics"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        
        if transaction_type == 'combined':
            st.markdown(f'<div class="chart-title">{ticker} - Retail Flow Analysis (Z-Score: {z_score_window}d)</div>', 
                      unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chart-title">{ticker} - {transaction_type.title()} Flow Analysis (Z-Score: {z_score_window}d)</div>', 
                      unsafe_allow_html=True)
        
        ticker_data = df[df['ticker'] == ticker]
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        if transaction_type == 'combined':
            chart_title = f"{ticker} - Retail Flow Analysis"
            fig = self.create_dual_axis_chart(ticker_data, stock_prices, chart_title, "Net Flow ($)", ticker)
        else:
            chart_title = f"{ticker} - {transaction_type.title()} Flow Analysis"
            fig = self.create_dual_axis_chart(ticker_data, stock_prices, chart_title, 
                                             f"{transaction_type.title()} Flow ($)", ticker)
        
        st.plotly_chart(fig, use_container_width=True)
        
        if transaction_type == 'combined':
            combined_data_subset = ticker_data[ticker_data['type'] == 'Combined']
            if len(combined_data_subset) > 1:
                values = combined_data_subset['net_flow']
                metric_label = "Combined"
            else:
                values = ticker_data['net_flow']
                metric_label = "Flow"
        else:
            values = ticker_data['net_flow']
            metric_label = transaction_type.title()
        
        if len(values) > 1:
            self.display_flow_metrics(values, ticker, metric_label, z_score_window)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ==========================================
    # COMBINED FLOW ANALYSIS
    # ==========================================
    
    def analyze_combined_flow(self, ticker_list, from_date, to_date, z_score_window=21):
        """Analyze combined flow: Retail + OTM Small Net Premium + OTM Large Net Premium"""
        
        st.info("Fetching Retail + OTM Small + OTM Large flow data...")
        
        retail_data, retail_status = self.fetch_stock_flow_data(ticker_list, from_date, to_date, 'combined')
        options_small_data, small_status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'small')
        options_large_data, large_status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'large')
        
        if retail_status == "success" and small_status == "success" and large_status == "success":
            st.success("All flow data fetched successfully!")
            
            retail_flow = retail_data.get('combined_data', {})
            small_call = options_small_data.get('call_data', {})
            small_put = options_small_data.get('put_data', {})
            large_call = options_large_data.get('call_data', {})
            large_put = options_large_data.get('put_data', {})
            
            for ticker in ticker_list:
                self.display_combined_flow_chart(retail_flow, small_call, small_put, large_call, large_put,
                                                 ticker, from_date, to_date, z_score_window)
        else:
            st.error(f"Failed to fetch flow data. Retail: {retail_status}, Small: {small_status}, Large: {large_status}")
    
    def display_combined_flow_chart(self, retail_flow, small_call, small_put, large_call, large_put,
                                    ticker, from_date, to_date, z_score_window=21):
        """Display combined flow chart"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-title">{ticker} - Combined Flow Analysis (Retail + Options) (Z-Score: {z_score_window}d)</div>',
                   unsafe_allow_html=True)
        
        # Extract retail flow
        retail_records = {}
        for ticker_key, date_values in retail_flow.items():
            if ticker.upper() == ticker_key.upper() or ticker.upper() in ticker_key.upper():
                if isinstance(date_values, dict):
                    retail_records = date_values
                    break
        
        # Extract options small net premium
        target_upper = ticker.upper()
        small_call_records = {}
        small_put_records = {}
        
        for ticker_key, date_values in small_call.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        small_call_records[date_str] = small_call_records.get(date_str, 0) + value
        
        for ticker_key, date_values in small_put.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        small_put_records[date_str] = small_put_records.get(date_str, 0) + value
        
        # Extract options large net premium
        large_call_records = {}
        large_put_records = {}
        
        for ticker_key, date_values in large_call.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        large_call_records[date_str] = large_call_records.get(date_str, 0) + value
        
        for ticker_key, date_values in large_put.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        large_put_records[date_str] = large_put_records.get(date_str, 0) + value
        
        # Combine all flows
        all_dates = (set(retail_records.keys()) |
                    set(small_call_records.keys()) | set(small_put_records.keys()) |
                    set(large_call_records.keys()) | set(large_put_records.keys()))
        
        records = []
        for date_str in all_dates:
            retail_val = retail_records.get(date_str, 0)
            small_net = small_call_records.get(date_str, 0) - small_put_records.get(date_str, 0)
            large_net = large_call_records.get(date_str, 0) - large_put_records.get(date_str, 0)
            combined_flow = retail_val + small_net + large_net
            
            records.append({
                'date': pd.to_datetime(date_str),
                'combined_flow': combined_flow,
                'retail_flow': retail_val,
                'small_net': small_net,
                'large_net': large_net
            })
        
        if not records:
            st.warning(f"No combined flow data found for {ticker}")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        df = pd.DataFrame(records).sort_values('date')
        
        # Fetch stock prices
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        # Create chart
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add combined flow
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['combined_flow'],
            mode='lines+markers',
            name='Combined Flow',
            line=dict(color='#1a73e8', width=3),
            marker=dict(size=5),
            hovertemplate='<b>Combined Flow</b><br>Date: %{x}<br>Value: $%{y:,.0f}<extra></extra>'
        ), secondary_y=False)
        
        # Add stock price
        if stock_prices:
            price_dates = [pd.to_datetime(d) for d in stock_prices.keys()]
            price_values = list(stock_prices.values())
            if price_dates and price_values:
                fig.add_trace(go.Scatter(
                    x=price_dates,
                    y=price_values,
                    mode='lines',
                    name=f'{ticker} Stock Price',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    opacity=0.8,
                    hovertemplate='<b>Stock Price</b><br>Date: %{x}<br>Price: $%{y:.2f}<extra></extra>'
                ), secondary_y=True)
        
        fig.update_layout(
            title=f'{ticker} - Combined Flow (Retail + Options Small + Large) vs Stock Price',
            xaxis_title='Date',
            height=550,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        fig.update_yaxes(title_text='Combined Flow ($)', secondary_y=False)
        if stock_prices:
            fig.update_yaxes(title_text=f'{ticker} Stock Price ($)', secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display metrics
        if len(df) > 0:
            self.display_combined_flow_metrics(df, ticker, z_score_window)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_combined_flow_metrics(self, df, ticker, z_score_window=21):
        """Display metrics for combined flow analysis"""
        
        values = df['combined_flow']
        latest = values.iloc[-1]
        
        z_scores = self.calculate_z_scores(values, window=z_score_window)
        z_score = z_scores.iloc[-1]
        
        mean_flow = values.mean()
        activity_level, activity_emoji = self.classify_activity_level(z_score)
        percentile = (np.sum(values <= latest) / len(values)) * 100
        
        # Get breakdown of latest flow
        latest_retail = df['retail_flow'].iloc[-1]
        latest_small = df['small_net'].iloc[-1]
        latest_large = df['large_net'].iloc[-1]
        
        activity_color = {
            "Extreme Light": "#dc3545",
            "Light": "#ffc107",
            "Neutral": "#28a745",
            "Elevated": "#fd7e14",
            "Crowded": "#dc3545"
        }.get(activity_level, "#28a745")
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; background: #f8f9fa; 
                    padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid #e9ecef;">
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    {ticker} Activity
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: {activity_color};">
                    {activity_emoji} {activity_level}
                </div>
                <div style="color: #28a745; font-size: 0.75rem; font-weight: 500;">
                    Z: {z_score:.2f} ({z_score_window}d)
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Latest Combined
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    ${latest:,.0f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Average Combined
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    ${mean_flow:,.0f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Percentile
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    {percentile:.1f}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Flow breakdown
        st.markdown("### Flow Breakdown")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Retail Flow", f"${latest_retail:,.0f}")
        with col2:
            st.metric("Small Net Premium", f"${latest_small:,.0f}")
        with col3:
            st.metric("Large Net Premium", f"${latest_large:,.0f}")
        
        st.info("""
        **Combined Flow = Retail Flow + Small OTM Net Premium + Large OTM Net Premium**
        
        This metric provides the most comprehensive view of total market buying/selling pressure by combining:
        - Retail investor activity
        - Retail-sized options positions (small)
        - Institutional-sized options positions (large)
        """)
    
    # ==========================================
    # MA RATIO ANALYSIS - RETAIL
    # ==========================================
    
    def analyze_ma_ratio_retail(self, ticker_list, from_date, to_date, transaction_type, z_score_window=21):
        """Analyze 5-day MA / 21-day MA ratio for RETAIL flow vs stock price"""
        
        st.info("Calculating Retail MA Ratio Analysis...")
        
        stock_data, status = self.fetch_stock_flow_data(ticker_list, from_date, to_date, transaction_type)
        
        if status == "success" and stock_data:
            st.success("Retail flow data fetched successfully!")
            
            if transaction_type == 'combined':
                data_to_process = stock_data.get('combined_data', {})
            else:
                data_to_process = stock_data
            
            for ticker in ticker_list:
                self.display_ma_ratio_retail_chart(data_to_process, ticker, from_date, to_date, z_score_window)
        else:
            st.error(f"Failed to fetch retail flow data. Status: {status}")
    
    def display_ma_ratio_retail_chart(self, flow_data, ticker, from_date, to_date, z_score_window=21):
        """Display MA Ratio chart for retail flow"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-title">{ticker} - Retail MA Ratio Analysis (5d/21d)</div>', 
                  unsafe_allow_html=True)
        
        records = []
        for ticker_key, date_values in flow_data.items():
            if ticker.upper() == ticker_key.upper() or ticker.upper() in ticker_key.upper():
                if isinstance(date_values, dict):
                    for date_str, value in date_values.items():
                        records.append({
                            'date': pd.to_datetime(date_str),
                            'net_flow': value
                        })
                    break
        
        if not records:
            st.warning(f"No retail flow data found for {ticker}")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        df = pd.DataFrame(records).sort_values('date')
        
        df['ma_5'] = df['net_flow'].rolling(window=5, min_periods=1).mean()
        df['ma_21'] = df['net_flow'].rolling(window=21, min_periods=1).mean()
        df['ma_ratio'] = df['ma_5'] / df['ma_21'].replace(0, np.nan)
        df['ma_ratio'] = df['ma_ratio'].fillna(1)
        
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['ma_ratio'],
            mode='lines+markers',
            name='MA Ratio (5d/21d)',
            line=dict(color='#1a73e8', width=3),
            marker=dict(size=5)
        ), secondary_y=False)
        
        fig.add_hline(y=1.0, line_dash="dot", line_color="gray", 
                     annotation_text="Neutral (1.0)", secondary_y=False)
        
        if stock_prices:
            price_dates = [pd.to_datetime(d) for d in stock_prices.keys()]
            price_values = list(stock_prices.values())
            if price_dates and price_values:
                fig.add_trace(go.Scatter(
                    x=price_dates,
                    y=price_values,
                    mode='lines',
                    name=f'{ticker} Stock Price',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    opacity=0.8
                ), secondary_y=True)
        
        fig.update_layout(
            title=f'{ticker} - Retail MA Ratio vs Stock Price',
            xaxis_title='Date',
            height=550,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        fig.update_yaxes(title_text='MA Ratio (5d/21d)', secondary_y=False)
        if stock_prices:
            fig.update_yaxes(title_text=f'{ticker} Stock Price ($)', secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        if len(df) > 0:
            self.display_ma_ratio_metrics(df, ticker, z_score_window, "Retail")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_ma_ratio_metrics(self, df, ticker, z_score_window=21, flow_type="Retail"):
        """Display metrics for MA Ratio analysis with updated thresholds"""
        
        latest_ratio = df['ma_ratio'].iloc[-1]
        avg_ratio = df['ma_ratio'].mean()
        std_ratio = df['ma_ratio'].std()
        z_score = (latest_ratio - avg_ratio) / std_ratio if std_ratio > 0 else 0
        
        # Updated thresholds: <0.5 Strong Down, 0.5-1.0 Downtrend, 1.0-1.5 Uptrend, >1.5 Strong Up
        if latest_ratio > 1.5:
            signal, signal_color = "Strong Uptrend", "#28a745"
        elif latest_ratio >= 1.0:
            signal, signal_color = "Uptrend", "#28a745"
        elif latest_ratio >= 0.5:
            signal, signal_color = "Downtrend", "#dc3545"
        else:
            signal, signal_color = "Strong Downtrend", "#dc3545"
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; background: #f8f9fa; 
                    padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid #e9ecef;">
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Momentum Signal
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: {signal_color};">
                    {signal}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Latest MA Ratio
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    {latest_ratio:.3f}
                </div>
                <div style="color: #28a745; font-size: 0.75rem; font-weight: 500;">
                    Z-Score: {z_score:.2f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Average MA Ratio
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    {avg_ratio:.3f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Std Deviation
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    {std_ratio:.3f}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("""
        **MA Ratio Interpretation (Updated Thresholds):**
        - **> 1.5**: Strong uptrend (short-term accelerating rapidly)
        - **1.0 - 1.5**: Uptrend (short-term gaining momentum)
        - **0.5 - 1.0**: Downtrend (short-term losing momentum)
        - **< 0.5**: Strong downtrend (short-term decelerating rapidly)
        """)
    
    # ==========================================
    # MA RATIO ANALYSIS - OPTIONS
    # ==========================================
    
    def analyze_ma_ratio_options(self, ticker_list, from_date, to_date, size, z_score_window=21):
        """Analyze 5-day MA / 21-day MA ratio for OPTIONS flow vs stock price"""
        
        st.info(f"Calculating Options {size.title()} MA Ratio Analysis...")
        
        options_data, status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', size)
        
        if status == "success" and options_data:
            st.success(f"Options {size} flow data fetched successfully!")
            
            call_data = options_data.get('call_data', {})
            put_data = options_data.get('put_data', {})
            
            for ticker in ticker_list:
                self.display_ma_ratio_options_chart(call_data, put_data, ticker, from_date, to_date, size, z_score_window)
        else:
            st.error(f"Failed to fetch options {size} flow data. Status: {status}")
    
    def display_ma_ratio_options_chart(self, call_data, put_data, ticker, from_date, to_date, size, z_score_window=21):
        """Display MA Ratio chart for OPTIONS flow"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-title">{ticker} - Options {size.title()} MA Ratio Analysis (5d/21d)</div>', 
                  unsafe_allow_html=True)
        
        # Calculate net premium for this ticker
        ticker_call_data = {}
        ticker_put_data = {}
        target_upper = ticker.upper()
        
        for ticker_key, date_values in call_data.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        ticker_call_data[date_str] = ticker_call_data.get(date_str, 0) + value
        
        for ticker_key, date_values in put_data.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        ticker_put_data[date_str] = ticker_put_data.get(date_str, 0) + value
        
        # Calculate net premium
        all_dates = set(ticker_call_data.keys()) | set(ticker_put_data.keys())
        records = []
        for date_str in all_dates:
            call_value = ticker_call_data.get(date_str, 0)
            put_value = ticker_put_data.get(date_str, 0)
            net_premium = call_value - put_value
            
            records.append({
                'date': pd.to_datetime(date_str),
                'net_premium': net_premium
            })
        
        if not records:
            st.warning(f"No options {size} flow data found for {ticker}")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        df = pd.DataFrame(records).sort_values('date')
        
        df['ma_5'] = df['net_premium'].rolling(window=5, min_periods=1).mean()
        df['ma_21'] = df['net_premium'].rolling(window=21, min_periods=1).mean()
        df['ma_ratio'] = df['ma_5'] / df['ma_21'].replace(0, np.nan)
        df['ma_ratio'] = df['ma_ratio'].fillna(1)
        
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['ma_ratio'],
            mode='lines+markers',
            name=f'Options {size.title()} MA Ratio (5d/21d)',
            line=dict(color='#9333ea', width=3),
            marker=dict(size=5)
        ), secondary_y=False)
        
        fig.add_hline(y=1.0, line_dash="dot", line_color="gray", 
                     annotation_text="Neutral (1.0)", secondary_y=False)
        
        if stock_prices:
            price_dates = [pd.to_datetime(d) for d in stock_prices.keys()]
            price_values = list(stock_prices.values())
            if price_dates and price_values:
                fig.add_trace(go.Scatter(
                    x=price_dates,
                    y=price_values,
                    mode='lines',
                    name=f'{ticker} Stock Price',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    opacity=0.8
                ), secondary_y=True)
        
        fig.update_layout(
            title=f'{ticker} - Options {size.title()} MA Ratio vs Stock Price',
            xaxis_title='Date',
            height=550,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        fig.update_yaxes(title_text='MA Ratio (5d/21d)', secondary_y=False)
        if stock_prices:
            fig.update_yaxes(title_text=f'{ticker} Stock Price ($)', secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        if len(df) > 0:
            self.display_ma_ratio_metrics(df, ticker, z_score_window, f"Options {size.title()}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ==========================================
    # MA RATIO ANALYSIS - COMBINED
    # ==========================================
    
    def analyze_ma_ratio_combined(self, ticker_list, from_date, to_date, transaction_type, z_score_window=21):
        """Analyze 5-day MA / 21-day MA ratio for COMBINED (Retail + Options Small + Large) vs stock price"""
        
        st.info("Calculating Combined MA Ratio Analysis (Retail + Options Small + Large)...")
        
        retail_data, retail_status = self.fetch_stock_flow_data(ticker_list, from_date, to_date, transaction_type)
        options_small_data, small_status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'small')
        options_large_data, large_status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'large')
        
        if retail_status == "success" and small_status == "success" and large_status == "success":
            st.success("All flow data (Retail + Options Small + Large) fetched successfully!")
            
            if transaction_type == 'combined':
                retail_flow = retail_data.get('combined_data', {})
            else:
                retail_flow = retail_data
            
            small_call = options_small_data.get('call_data', {})
            small_put = options_small_data.get('put_data', {})
            large_call = options_large_data.get('call_data', {})
            large_put = options_large_data.get('put_data', {})
            
            for ticker in ticker_list:
                self.display_ma_ratio_combined_chart(retail_flow, small_call, small_put, large_call, large_put, 
                                                     ticker, from_date, to_date, z_score_window)
        else:
            st.error(f"Failed to fetch all data. Retail: {retail_status}, Small: {small_status}, Large: {large_status}")
    
    def display_ma_ratio_combined_chart(self, retail_flow, small_call, small_put, large_call, large_put, 
                                        ticker, from_date, to_date, z_score_window=21):
        """Display MA Ratio chart for COMBINED flow"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-title">{ticker} - Combined MA Ratio Analysis (Retail + Options) (5d/21d)</div>', 
                  unsafe_allow_html=True)
        
        # Extract retail flow
        retail_records = {}
        for ticker_key, date_values in retail_flow.items():
            if ticker.upper() == ticker_key.upper() or ticker.upper() in ticker_key.upper():
                if isinstance(date_values, dict):
                    retail_records = date_values
                    break
        
        # Extract options small net premium
        target_upper = ticker.upper()
        small_call_records = {}
        small_put_records = {}
        
        for ticker_key, date_values in small_call.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        small_call_records[date_str] = small_call_records.get(date_str, 0) + value
        
        for ticker_key, date_values in small_put.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        small_put_records[date_str] = small_put_records.get(date_str, 0) + value
        
        # Extract options large net premium
        large_call_records = {}
        large_put_records = {}
        
        for ticker_key, date_values in large_call.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        large_call_records[date_str] = large_call_records.get(date_str, 0) + value
        
        for ticker_key, date_values in large_put.items():
            if isinstance(date_values, dict):
                base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                if base_ticker.upper() == target_upper:
                    for date_str, value in date_values.items():
                        large_put_records[date_str] = large_put_records.get(date_str, 0) + value
        
        # Combine all flows
        all_dates = (set(retail_records.keys()) | 
                    set(small_call_records.keys()) | set(small_put_records.keys()) |
                    set(large_call_records.keys()) | set(large_put_records.keys()))
        
        combined_records = []
        for date_str in all_dates:
            retail_val = retail_records.get(date_str, 0)
            small_net = small_call_records.get(date_str, 0) - small_put_records.get(date_str, 0)
            large_net = large_call_records.get(date_str, 0) - large_put_records.get(date_str, 0)
            combined_flow = retail_val + small_net + large_net
            
            combined_records.append({
                'date': pd.to_datetime(date_str),
                'combined_flow': combined_flow
            })
        
        if not combined_records:
            st.warning(f"No combined flow data found for {ticker}")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        
        df = pd.DataFrame(combined_records).sort_values('date')
        
        df['ma_5'] = df['combined_flow'].rolling(window=5, min_periods=1).mean()
        df['ma_21'] = df['combined_flow'].rolling(window=21, min_periods=1).mean()
        df['ma_ratio'] = df['ma_5'] / df['ma_21'].replace(0, np.nan)
        df['ma_ratio'] = df['ma_ratio'].fillna(1)
        
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['ma_ratio'],
            mode='lines+markers',
            name='Combined MA Ratio (5d/21d)',
            line=dict(color='#dc2626', width=3),
            marker=dict(size=5)
        ), secondary_y=False)
        
        fig.add_hline(y=1.0, line_dash="dot", line_color="gray", 
                     annotation_text="Neutral (1.0)", secondary_y=False)
        
        if stock_prices:
            price_dates = [pd.to_datetime(d) for d in stock_prices.keys()]
            price_values = list(stock_prices.values())
            if price_dates and price_values:
                fig.add_trace(go.Scatter(
                    x=price_dates,
                    y=price_values,
                    mode='lines',
                    name=f'{ticker} Stock Price',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    opacity=0.8
                ), secondary_y=True)
        
        fig.update_layout(
            title=f'{ticker} - Combined (Retail + Options) MA Ratio vs Stock Price',
            xaxis_title='Date',
            height=550,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        fig.update_yaxes(title_text='MA Ratio (5d/21d)', secondary_y=False)
        if stock_prices:
            fig.update_yaxes(title_text=f'{ticker} Stock Price ($)', secondary_y=True)
        
        st.plotly_chart(fig, use_container_width=True)
        
        if len(df) > 0:
            self.display_ma_ratio_metrics(df, ticker, z_score_window, "Combined (Retail + Options)")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ==========================================
    # OPTIONS FLOW ANALYSIS
    # ==========================================
    
    def analyze_options_flow(self, ticker_list, from_date, to_date, moneyness, size, call_put_selection, z_score_window=21):
        """Analyze options flow with Z-score window support"""
        
        options_data, status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, moneyness, size)
        
        if status == "success" and options_data:
            st.success("Options flow data fetched successfully!")
            
            call_data = options_data.get('call_data', {})
            put_data = options_data.get('put_data', {})
            size_totals = options_data.get('size_totals', {})
            
            if size == 'combined' and size_totals:
                with st.expander("Size Breakdown Verification", expanded=False):
                    self.display_size_breakdown(size_totals)
            
            records = []
            for data_dict, data_type in [(call_data, 'Call'), (put_data, 'Put')]:
                for ticker_key, date_values in data_dict.items():
                    if isinstance(date_values, dict):
                        base_ticker = ticker_key.split('_')[-1] if '_' in ticker_key else ticker_key
                        for date_str, value in date_values.items():
                            records.append({
                                'date': pd.to_datetime(date_str),
                                'ticker': base_ticker,
                                'value': value,
                                'type': data_type
                            })
            
            if records:
                df = pd.DataFrame(records).sort_values(['ticker', 'type', 'date'])
                
                net_records = []
                for ticker in df['ticker'].unique():
                    net_df = self.calculate_net_premium(df, ticker)
                    net_records.extend(net_df.to_dict('records'))
                
                all_records = records + net_records
                df = pd.DataFrame(all_records).sort_values(['ticker', 'type', 'date'])
                
                for ticker in df['ticker'].unique():
                    self.display_options_flow_chart(df, ticker, moneyness, size, call_put_selection, 
                                                   from_date, to_date, z_score_window)
            else:
                st.warning("No options data records found")
        else:
            st.error(f"Failed to fetch options data: {status}")
    
    def display_options_flow_chart(self, df, ticker, moneyness, size, call_put_selection, from_date, to_date, z_score_window=21):
        """Display options flow chart with Z-score window"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-title">{ticker} - {moneyness} {size.title()} Options Flow (Z-Score: {z_score_window}d)</div>', 
                  unsafe_allow_html=True)
        
        ticker_data = df[df['ticker'] == ticker]
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        
        chart_title = f"{ticker} - {moneyness} {size.title()} Options Flow"
        if size == 'combined':
            chart_title += " (Fixed)"
        
        fig = self.create_dual_axis_chart(ticker_data, stock_prices, chart_title, "Premium ($)", ticker)
        st.plotly_chart(fig, use_container_width=True)
        
        if call_put_selection == 'net_premium':
            analysis_subset = ticker_data[ticker_data['type'] == 'Net_Premium']
            metric_label = "Net Premium"
        elif call_put_selection == 'call':
            analysis_subset = ticker_data[ticker_data['type'] == 'Call']
            metric_label = "Call Premium"
        else:
            analysis_subset = ticker_data[ticker_data['type'] == 'Put']
            metric_label = "Put Premium"
        
        if len(analysis_subset) > 1:
            values = analysis_subset['value']
            self.display_flow_metrics(values, ticker, metric_label, z_score_window)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ==========================================
    # Z-SCORE COMPARISON
    # ==========================================
    
    def analyze_z_score_comparison(self, ticker_list, from_date, to_date, z_score_window=21):
        """Analyze Z-Score comparison between retail and options"""
        
        st.info("Fetching both retail and options data for Z-Score comparison...")
        
        retail_data, retail_status = self.fetch_stock_flow_data(ticker_list, from_date, to_date, 'combined')
        options_data, options_status = self.fetch_options_data_fixed(ticker_list, from_date, to_date, 'OTM', 'combined')
        
        if retail_status == "success" and options_status == "success" and retail_data and options_data:
            st.success("Both retail and options data fetched successfully!")
            
            for ticker in ticker_list:
                self.display_z_score_comparison(retail_data, options_data, ticker, from_date, to_date, z_score_window)
        else:
            st.error("Failed to fetch data for Z-Score comparison")
    
    def display_z_score_comparison(self, retail_data, options_data, ticker, from_date, to_date, z_score_window=21):
        """Display Z-Score comparison chart with combined flow"""
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="chart-title">Z-Score Comparison: {ticker} ({z_score_window}d window)</div>', 
                  unsafe_allow_html=True)
        
        stock_prices = self.fetch_stock_price_data_improved(ticker, from_date, to_date)
        fig, comparison_df = self.create_z_score_comparison_chart(retail_data, options_data, ticker, stock_prices, z_score_window)
        
        if fig is not None and comparison_df is not None:
            st.plotly_chart(fig, use_container_width=True)
            
            if len(comparison_df) > 0:
                self.display_z_score_metrics(comparison_df, ticker)
        else:
            st.warning(f"Could not create Z-Score comparison for {ticker}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ==========================================
    # STOCK PRICE FETCHING (yfinance)
    # ==========================================
    
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
    
    # ==========================================
    # API FUNCTIONS
    # ==========================================
    
    def fetch_stock_flow_data(self, tickers, from_date, to_date, transaction_type):
        """Fetch stock retail flow data"""
        if not self.vandatrack_token:
            return {}, "No token provided"
        
        url = 'https://www.vandatrack.com/tickers/api/'
        ticker_list = tickers if isinstance(tickers, list) else [tickers]
        
        if transaction_type == 'combined':
            combined_data, buy_data, sell_data = {}, {}, {}
            
            for ticker in ticker_list:
                params = {'auth_token': self.vandatrack_token, 'tickers': ticker, 
                         'from_date': from_date.strftime('%Y-%m-%d'), 
                         'to_date': to_date.strftime('%Y-%m-%d')}
                
                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            combined_data.update(data)
                except:
                    pass
                
                time.sleep(0.5)
                
                params_buy = params.copy()
                params_buy['type'] = 'buy'
                try:
                    response = requests.get(url, params=params_buy, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            buy_data.update(data)
                except:
                    pass
                
                time.sleep(0.5)
                
                params_sell = params.copy()
                params_sell['type'] = 'sell'
                try:
                    response = requests.get(url, params=params_sell, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            sell_data.update(data)
                except:
                    pass
                
                time.sleep(0.5)
            
            return {'combined_data': combined_data, 'buy_data': buy_data, 'sell_data': sell_data}, "success"
        
        else:
            all_data = {}
            for ticker in ticker_list:
                params = {'auth_token': self.vandatrack_token, 'tickers': ticker, 
                         'from_date': from_date.strftime('%Y-%m-%d'), 
                         'to_date': to_date.strftime('%Y-%m-%d')}
                if transaction_type != 'combined':
                    params['type'] = transaction_type
                
                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            all_data.update(data)
                except:
                    pass
            
            return all_data, "success"
    
    def fetch_options_data_fixed(self, tickers, from_date, to_date, moneyness, size):
        """Fetch options data with fix for combined size"""
        if not self.vandatrack_token:
            return {}, "No token provided"
        
        url = 'https://www.vandatrack.com/option/api/'
        ticker_list = tickers if isinstance(tickers, list) else [tickers]
        
        base_params = {
            'auth_token': self.vandatrack_token,
            'tickers': ticker_list,
            'saved_list': 'false',
            'from_date': from_date.strftime('%Y-%m-%d'),
            'to_date': to_date.strftime('%Y-%m-%d'),
            'moneyness': moneyness
        }
        
        if size == 'combined':
            return self.fetch_combined_options_data(url, base_params)
        else:
            call_params = {**base_params, 'callput': 'call', 'size': size}
            put_params = {**base_params, 'callput': 'put', 'size': size}
            
            call_data = self.force_api_call(url, call_params)
            time.sleep(0.5)
            put_data = self.force_api_call(url, put_params)
            
            if call_data and put_data:
                return {"call_data": call_data, "put_data": put_data}, "success"
            else:
                return {}, "API failed"
    
    def fetch_combined_options_data(self, url, base_params):
        """Fetch and combine small + large options data"""
        small_call_data = {}
        small_put_data = {}
        large_call_data = {}
        large_put_data = {}
        
        size_totals = {
            'small': {'call': 0, 'put': 0},
            'large': {'call': 0, 'put': 0}
        }
        
        small_call_params = {**base_params, 'callput': 'call', 'size': 'small'}
        small_call_response = self.force_api_call(url, small_call_params)
        if small_call_response:
            small_call_data = small_call_response
            for ticker_key, date_values in small_call_data.items():
                if isinstance(date_values, dict):
                    size_totals['small']['call'] += sum(date_values.values())
        
        time.sleep(1)
        
        small_put_params = {**base_params, 'callput': 'put', 'size': 'small'}
        small_put_response = self.force_api_call(url, small_put_params)
        if small_put_response:
            small_put_data = small_put_response
            for ticker_key, date_values in small_put_data.items():
                if isinstance(date_values, dict):
                    size_totals['small']['put'] += sum(date_values.values())
        
        time.sleep(1)
        
        large_call_params = {**base_params, 'callput': 'call', 'size': 'large'}
        large_call_response = self.force_api_call(url, large_call_params)
        if large_call_response:
            large_call_data = large_call_response
            for ticker_key, date_values in large_call_data.items():
                if isinstance(date_values, dict):
                    size_totals['large']['call'] += sum(date_values.values())
        
        time.sleep(1)
        
        large_put_params = {**base_params, 'callput': 'put', 'size': 'large'}
        large_put_response = self.force_api_call(url, large_put_params)
        if large_put_response:
            large_put_data = large_put_response
            for ticker_key, date_values in large_put_data.items():
                if isinstance(date_values, dict):
                    size_totals['large']['put'] += sum(date_values.values())
        
        combined_call_data = self.combine_size_data(small_call_data, large_call_data)
        combined_put_data = self.combine_size_data(small_put_data, large_put_data)
        
        return {
            "call_data": combined_call_data,
            "put_data": combined_put_data,
            "size_totals": size_totals
        }, "success"
    
    def combine_size_data(self, small_data, large_data):
        """Combine small and large size data"""
        combined_data = {}
        
        all_tickers = set(small_data.keys()) | set(large_data.keys())
        for ticker_key in all_tickers:
            small_dates = small_data.get(ticker_key, {})
            large_dates = large_data.get(ticker_key, {})
            
            if isinstance(small_dates, dict) or isinstance(large_dates, dict):
                combined_data[ticker_key] = {}
                all_dates = set()
                if isinstance(small_dates, dict):
                    all_dates.update(small_dates.keys())
                if isinstance(large_dates, dict):
                    all_dates.update(large_dates.keys())
                
                for date_str in all_dates:
                    small_value = small_dates.get(date_str, 0) if isinstance(small_dates, dict) else 0
                    large_value = large_dates.get(date_str, 0) if isinstance(large_dates, dict) else 0
                    combined_data[ticker_key][date_str] = small_value + large_value
        
        return combined_data
    
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
    
    # ==========================================
    # HELPER FUNCTIONS
    # ==========================================
    
    def calculate_z_scores(self, data_series, window=None):
        """Calculate z-scores with configurable window"""
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
    
    def calculate_net_premium(self, df, ticker):
        """Calculate net premium for a ticker"""
        net_records = []
        ticker_data = df[df['ticker'] == ticker]
        
        call_data = ticker_data[ticker_data['type'] == 'Call']
        put_data = ticker_data[ticker_data['type'] == 'Put']
        
        all_dates = set(call_data['date'].dt.strftime('%Y-%m-%d')) | set(put_data['date'].dt.strftime('%Y-%m-%d'))
        
        for date_str in all_dates:
            date_obj = pd.to_datetime(date_str)
            call_value = call_data[call_data['date'] == date_obj]['value'].sum()
            put_value = put_data[put_data['date'] == date_obj]['value'].sum()
            net_premium = call_value - put_value
            
            net_records.append({
                'date': date_obj,
                'ticker': ticker,
                'value': net_premium,
                'type': 'Net_Premium'
            })
        
        return pd.DataFrame(net_records)
    
    def create_dual_axis_chart(self, flow_data, price_data, title, flow_label, ticker):
        """Create dual-axis chart with stock prices on right axis"""
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        if isinstance(flow_data, pd.DataFrame):
            color_map = {
                'Combined': '#1a73e8',
                'Buy': '#28a745',
                'Sell': '#dc3545',
                'Call': '#2E8B57',
                'Put': '#DC143C',
                'Net_Premium': '#1a73e8'
            }
            
            if 'type' in flow_data.columns:
                for flow_type in flow_data['type'].unique():
                    type_data = flow_data[flow_data['type'] == flow_type]
                    line_width = 3 if flow_type in ['Combined', 'Net_Premium'] else 2
                    
                    fig.add_trace(go.Scatter(
                        x=type_data['date'],
                        y=type_data.get('net_flow', type_data.get('value')),
                        mode='lines+markers',
                        name=f'{flow_type} Flow',
                        line=dict(color=color_map.get(flow_type, '#1a73e8'), width=line_width),
                        marker=dict(size=4)
                    ), secondary_y=False)
        
        if price_data:
            price_dates = [pd.to_datetime(d) for d in price_data.keys()]
            price_values = list(price_data.values())
            if price_dates and price_values:
                fig.add_trace(go.Scatter(
                    x=price_dates,
                    y=price_values,
                    mode='lines',
                    name=f'{ticker} Stock Price',
                    line=dict(color='#ff7f0e', width=2, dash='dash'),
                    opacity=0.8
                ), secondary_y=True)
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            height=500,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
            plot_bgcolor='white',
            paper_bgcolor='white',
            margin=dict(t=80, b=40, l=40, r=40)
        )
        
        fig.update_yaxes(title_text=flow_label, secondary_y=False, side="left")
        if price_data:
            fig.update_yaxes(title_text=f"{ticker} Stock Price ($)", secondary_y=True, side="right")
        
        return fig
    
    def create_z_score_comparison_chart(self, retail_data, options_data, ticker, price_data, z_score_window=21):
        """Create Z-Score comparison chart with combined flow"""
        try:
            retail_records = []
            combined_data = retail_data.get('combined_data', retail_data)
            
            for ticker_key, date_values in combined_data.items():
                if ticker_key.upper() == ticker.upper():
                    if isinstance(date_values, dict):
                        for date_str, value in date_values.items():
                            retail_records.append({'date': pd.to_datetime(date_str), 'value': value})
                    break
            
            options_records = []
            call_data = options_data.get('call_data', {})
            put_data = options_data.get('put_data', {})
            
            for ticker_key in list(call_data.keys()) + list(put_data.keys()):
                if ticker.upper() in ticker_key.upper():
                    dates = set()
                    if ticker_key in call_data and isinstance(call_data[ticker_key], dict):
                        dates.update(call_data[ticker_key].keys())
                    if ticker_key in put_data and isinstance(put_data[ticker_key], dict):
                        dates.update(put_data[ticker_key].keys())
                    
                    for date_str in dates:
                        call_val = call_data.get(ticker_key, {}).get(date_str, 0) if ticker_key in call_data else 0
                        put_val = put_data.get(ticker_key, {}).get(date_str, 0) if ticker_key in put_data else 0
                        net_premium = call_val - put_val
                        options_records.append({'date': pd.to_datetime(date_str), 'value': net_premium})
            
            if not retail_records or not options_records:
                return None, None
            
            retail_df = pd.DataFrame(retail_records).sort_values('date')
            options_df = pd.DataFrame(options_records).groupby('date')['value'].sum().reset_index().sort_values('date')
            
            retail_df['z_score'] = self.calculate_z_scores(retail_df['value'], window=z_score_window)
            options_df['z_score'] = self.calculate_z_scores(options_df['value'], window=z_score_window)
            
            merged_df = pd.merge(
                retail_df[['date', 'z_score', 'value']].rename(
                    columns={'z_score': 'retail_z_score', 'value': 'retail_value'}
                ),
                options_df[['date', 'z_score', 'value']].rename(
                    columns={'z_score': 'options_z_score', 'value': 'options_value'}
                ),
                on='date', how='outer'
            ).fillna(0)
            
            merged_df['combined_value'] = merged_df['retail_value'] + merged_df['options_value']
            merged_df = merged_df.sort_values('date')
            merged_df['combined_z_score'] = self.calculate_z_scores(merged_df['combined_value'], window=z_score_window)
            
            if merged_df.empty:
                return None, None
            
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            fig.add_trace(go.Scatter(
                x=merged_df['date'],
                y=merged_df['retail_z_score'],
                mode='lines+markers',
                name='Retail Flow Z-Score',
                line=dict(color='#2563eb', width=3),
                marker=dict(size=6)
            ), secondary_y=False)
            
            fig.add_trace(go.Scatter(
                x=merged_df['date'],
                y=merged_df['options_z_score'],
                mode='lines+markers',
                name='Options Flow Z-Score',
                line=dict(color='#dc2626', width=3),
                marker=dict(size=6)
            ), secondary_y=False)
            
            fig.add_trace(go.Scatter(
                x=merged_df['date'],
                y=merged_df['combined_z_score'],
                mode='lines+markers',
                name='Combined Flow Z-Score',
                line=dict(color='#16a34a', width=3),
                marker=dict(size=6)
            ), secondary_y=False)
            
            if price_data:
                price_dates = [pd.to_datetime(d) for d in price_data.keys()]
                price_values = list(price_data.values())
                if price_dates and price_values:
                    fig.add_trace(go.Scatter(
                        x=price_dates,
                        y=price_values,
                        mode='lines',
                        name=f'{ticker} Stock Price',
                        line=dict(color='#ff7f0e', width=2, dash='dash'),
                        opacity=0.8
                    ), secondary_y=True)
            
            fig.add_hline(y=0, line_dash="dot", line_color="gray", annotation_text="Mean")
            fig.add_hline(y=2, line_dash="dash", line_color="orange", opacity=0.7, annotation_text="±2σ")
            fig.add_hline(y=-2, line_dash="dash", line_color="orange", opacity=0.7)
            
            fig.update_layout(
                title=f'{ticker} - Retail vs Options Flow Z-Score Comparison ({z_score_window}d window)',
                xaxis_title='Date',
                height=600,
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="top", y=1.02, xanchor="left", x=0),
                plot_bgcolor='white',
                paper_bgcolor='white',
                margin=dict(t=80, b=40, l=40, r=40)
            )
            
            fig.update_yaxes(title_text='Z-Score (Standard Deviations from Mean)', secondary_y=False)
            if price_data:
                fig.update_yaxes(title_text=f'{ticker} Stock Price ($)', secondary_y=True)
            
            return fig, merged_df
            
        except Exception:
            return None, None
    
    def display_flow_metrics(self, values, ticker, metric_label, z_score_window=21):
        """Display flow metrics with configurable Z-score window"""
        latest = values.iloc[-1]
        
        z_scores = self.calculate_z_scores(values, window=z_score_window)
        z_score = z_scores.iloc[-1]
        
        mean_flow = values.mean()
        activity_level, activity_emoji = self.classify_activity_level(z_score)
        percentile = (np.sum(values <= latest) / len(values)) * 100
        
        activity_color = {
            "Extreme Light": "#dc3545",
            "Light": "#ffc107",
            "Neutral": "#28a745",
            "Elevated": "#fd7e14",
            "Crowded": "#dc3545"
        }.get(activity_level, "#28a745")
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; background: #f8f9fa; 
                    padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid #e9ecef;">
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    {ticker} Activity
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: {activity_color};">
                    {activity_emoji} {activity_level}
                </div>
                <div style="color: #28a745; font-size: 0.75rem; font-weight: 500;">
                    Z: {z_score:.2f} ({z_score_window}d)
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Latest {metric_label}
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    ${latest:,.0f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Average {metric_label}
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    ${mean_flow:,.0f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Percentile
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    {percentile:.1f}%
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def display_z_score_metrics(self, comparison_df, ticker):
        """Display Z-score metrics including combined flow"""
        latest_retail_z = comparison_df['retail_z_score'].iloc[-1]
        latest_options_z = comparison_df['options_z_score'].iloc[-1]
        latest_combined_z = comparison_df['combined_z_score'].iloc[-1]
        
        retail_level, retail_emoji = self.classify_activity_level(latest_retail_z)
        options_level, options_emoji = self.classify_activity_level(latest_options_z)
        combined_level, combined_emoji = self.classify_activity_level(latest_combined_z)
        
        correlation = comparison_df['retail_z_score'].corr(comparison_df['options_z_score'])
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; background: #f8f9fa; 
                    padding: 1rem; border-radius: 8px; margin-top: 1rem; border: 1px solid #e9ecef;">
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Retail Activity
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #2563eb;">
                    {retail_emoji} {retail_level}
                </div>
                <div style="color: #28a745; font-size: 0.75rem; font-weight: 500;">
                    Z: {latest_retail_z:.2f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Options Activity
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #dc2626;">
                    {options_emoji} {options_level}
                </div>
                <div style="color: #28a745; font-size: 0.75rem; font-weight: 500;">
                    Z: {latest_options_z:.2f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Combined Activity
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #16a34a;">
                    {combined_emoji} {combined_level}
                </div>
                <div style="color: #28a745; font-size: 0.75rem; font-weight: 500;">
                    Z: {latest_combined_z:.2f}
                </div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500; 
                            text-transform: uppercase; margin-bottom: 0.25rem;">
                    Flow Correlation
                </div>
                <div style="font-size: 1.25rem; font-weight: 600; color: #202124;">
                    {correlation:.3f}
                </div>
                <div style="color: #6c757d; font-size: 0.75rem; font-weight: 500;">
                    Retail vs Options
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    def display_size_breakdown(self, size_totals):
        """Display size breakdown for combined options"""
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Small Call Total", f"${size_totals.get('small', {}).get('call', 0):,.0f}")
            st.metric("Small Put Total", f"${size_totals.get('small', {}).get('put', 0):,.0f}")
        with col2:
            st.metric("Large Call Total", f"${size_totals.get('large', {}).get('call', 0):,.0f}")
            st.metric("Large Put Total", f"${size_totals.get('large', {}).get('put', 0):,.0f}")
        with col3:
            combined_call = size_totals.get('small', {}).get('call', 0) + size_totals.get('large', {}).get('call', 0)
            combined_put = size_totals.get('small', {}).get('put', 0) + size_totals.get('large', {}).get('put', 0)
            combined_net = combined_call - combined_put
            st.metric("Combined Call Expected", f"${combined_call:,.0f}")
            st.metric("Combined Put Expected", f"${combined_put:,.0f}")
            st.metric("Combined Net Expected", f"${combined_net:,.0f}")
