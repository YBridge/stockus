import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import os

# 设置页面配置
st.set_page_config(page_title="全球股市行情", page_icon="📈", layout="wide")

# 加载环境变量
load_dotenv()

# 获取API密钥
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

# 页面标题
st.title("📊 全球股市行情")

# 创建两列布局
col1, col2 = st.columns([2, 1])

with col1:
    market = st.selectbox(
        "选择市场",
        options=["美股市场", "A股市场"],
        index=0
    )

with col2:
    time_range = st.selectbox(
        "选择时间范围",
        options=[7, 14, 30, 60, 90, 180, 365],
        format_func=lambda x: f"{x}天",
        index=2
    )

def get_stock_data(symbol, days):
    try:
        # 对于A股，需要添加市场后缀
        if market == "A股市场" and not (symbol.endswith('.SS') or symbol.endswith('.SZ')):
            if symbol.startswith('6'):
                symbol += '.SS'
            else:
                symbol += '.SZ'
        
        # 使用yfinance获取数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=f"{days}d")
        
        # 重置索引，将日期变为列
        df = df.reset_index()
        
        # 重命名列
        df = df.rename(columns={
            'Date': 'date',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        return ticker, df
        
    except Exception as e:
        st.error(f"获取数据时出错: {str(e)}")
        return None, None

def analyze_stock(symbol, info, df, custom_question=None):
    """生成股票分析报告"""
    try:
        if not info:
            return "错误：无法获取公司信息。请检查股票代码是否正确。"

        company_name = info.get('longName', symbol)
        
        # 计算技术指标
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        
        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 获取最新指标值
        latest_close = df['close'].iloc[-1]
        latest_ma5 = df['MA5'].iloc[-1]
        latest_ma20 = df['MA20'].iloc[-1]
        latest_ma60 = df['MA60'].iloc[-1]
        latest_rsi = df['RSI'].iloc[-1]
        
        # 构建提示
        prompt = f"""
        请对{company_name}（{symbol}）进行全面分析，包括以下方面：

        1. 技术指标分析：
        - 当前股价：${latest_close:.2f}
        - MA5：${latest_ma5:.2f}
        - MA20：${latest_ma20:.2f}
        - MA60：${latest_ma60:.2f}
        - RSI：{latest_rsi:.2f}

        2. 公司基本面分析：
        - 市值：{info.get('marketCap', 'N/A')}
        - 市盈率：{info.get('trailingPE', 'N/A')}
        - 52周最高价：{info.get('fiftyTwoWeekHigh', 'N/A')}
        - 52周最低价：{info.get('fiftyTwoWeekLow', 'N/A')}

        请提供：
        1. 技术面分析：基于均线、RSI等指标的走势分析
        2. 基本面分析：基于公司财务指标的分析
        3. 投资建议：根据以上分析给出明确的投资建议

        要求：
        1. 分析要客观专业
        2. 使用清晰的标题和段落结构
        3. 给出具体的数据支持
        4. 用中文回答
        """
        
        # 准备 API 请求
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的金融分析师。请提供客观、专业的分析和建议。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
            "top_p": 0.9,
            "stream": False
        }
        
        # 调用 Perplexity API
        try:
            response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_message += f"\n响应内容：{e.response.text}"
            return f"API 调用失败: {error_message}"
            
        # 解析响应
        try:
            result = response.json()
        except ValueError:
            return "API 返回的数据格式无效"
            
        if 'choices' not in result or not result['choices']:
            return "API 返回的数据结构不正确"
            
        analysis = result['choices'][0]['message']['content']
        
        # 如果有引用来源，添加到分析结果中
        if 'citations' in result and result['citations']:
            analysis += "\n\n**数据来源：**\n"
            for citation in result['citations']:
                analysis += f"- {citation}\n"
        
        return analysis
        
    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.text
            except:
                error_detail = "无法获取详细错误信息"
        else:
            error_detail = "无详细错误信息"
        
        return f"分析过程中出错: {error_message}\n\n详细错误信息：{error_detail}"

def analyze_custom_question(symbol, info, df, question):
    """专门处理自定义问题的分析"""
    try:
        if not info:
            return "错误：无法获取公司信息。请检查股票代码是否正确。"

        company_name = info.get('longName', symbol)
        
        # 构建提示
        prompt = f"""
        关于{company_name}（{symbol}）的具体问题分析：

        问题：{question}

        请提供详细的分析和见解，要求：
        1. 基于最新的市场数据和公司信息
        2. 给出具体的数据支持
        3. 提供明确的结论或建议
        4. 用中文回答
        5. 使用清晰的标题和段落结构
        """
        
        # 准备 API 请求
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一位专业的金融分析师。请针对用户的具体问题提供深入的分析和建议。保持专业、简洁和客观。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "max_tokens": 4096,
            "top_p": 0.9,
            "stream": False
        }
        
        # 调用 Perplexity API
        try:
            response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_message += f"\n响应内容：{e.response.text}"
            return f"API 调用失败: {error_message}"
            
        # 解析响应
        try:
            result = response.json()
        except ValueError:
            return "API 返回的数据格式无效"
            
        if 'choices' not in result or not result['choices']:
            return "API 返回的数据结构不正确"
            
        analysis = result['choices'][0]['message']['content']
        
        # 如果有引用来源，添加到分析结果中
        if 'citations' in result and result['citations']:
            analysis += "\n\n**数据来源：**\n"
            for citation in result['citations']:
                analysis += f"- {citation}\n"
        
        return analysis
        
    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.text
            except:
                error_detail = "无法获取详细错误信息"
        else:
            error_detail = "无详细错误信息"
        
        return f"分析过程中出错: {error_message}\n\n详细错误信息：{error_detail}"

def plot_candlestick(df, symbol):
    fig = go.Figure(data=[go.Candlestick(x=df['date'],
                                        open=df['open'],
                                        high=df['high'],
                                        low=df['low'],
                                        close=df['close'])])
    
    fig.update_layout(
        title=f'{symbol} 股票K线图',
        yaxis_title='价格',
        xaxis_title='日期',
        template='plotly_dark',
        xaxis_rangeslider_visible=False
    )
    
    return fig

def main():
    # 初始化会话状态
    if 'custom_question' not in st.session_state:
        st.session_state.custom_question = ""
    if 'custom_analysis_result' not in st.session_state:
        st.session_state.custom_analysis_result = None
    if 'symbol' not in st.session_state:
        st.session_state.symbol = ""
    if 'basic_analysis' not in st.session_state:
        st.session_state.basic_analysis = None
    if 'stock_data' not in st.session_state:
        st.session_state.stock_data = None
    if 'stock_info' not in st.session_state:
        st.session_state.stock_info = None
    
    # 页面标题
    st.title("股票分析助手 📈")
    
    # 创建两列布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 股票代码输入
        symbol = st.text_input("输入股票代码（例如：AAPL）", value=st.session_state.symbol).upper()
        if symbol != st.session_state.symbol:
            st.session_state.symbol = symbol
            st.session_state.custom_analysis_result = None  # 清除之前的分析结果
            st.session_state.basic_analysis = None  # 清除之前的基础分析
            st.session_state.stock_data = None  # 清除之前的股票数据
            st.session_state.stock_info = None  # 清除之前的股票信息
    
    # 当输入股票代码时
    if symbol:
        # 获取股票数据
        if st.session_state.stock_data is None:
            ticker, df = get_stock_data(symbol, time_range)
            if df is not None:
                st.session_state.stock_data = df
                st.session_state.stock_info = ticker.info
        
        if st.session_state.stock_data is not None:
            # 显示K线图
            st.plotly_chart(plot_candlestick(st.session_state.stock_data, symbol), use_container_width=True)
            
            # 显示基本信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("最新收盘价", f"${st.session_state.stock_data['close'].iloc[-1]:.2f}")
            with col2:
                price_change = st.session_state.stock_data['close'].iloc[-1] - st.session_state.stock_data['close'].iloc[0]
                price_change_pct = (price_change / st.session_state.stock_data['close'].iloc[0]) * 100
                st.metric("价格变动", f"${price_change:.2f} ({price_change_pct:.2f}%)")
            with col3:
                st.metric("平均成交量", f"{st.session_state.stock_data['volume'].mean():,.0f}")
            
            # 显示基础分析
            if st.session_state.basic_analysis is None:
                with st.spinner('正在生成基础分析报告...'):
                    st.session_state.basic_analysis = analyze_stock(symbol, st.session_state.stock_info, st.session_state.stock_data, None)
            
            st.markdown(st.session_state.basic_analysis)
            
            # 添加自定义问题输入
            st.markdown("---")
            st.subheader("自定义分析问题")
            
            def on_analyze_click():
                if st.session_state.custom_question.strip():
                    with st.spinner('正在分析您的问题...'):
                        st.session_state.custom_analysis_result = analyze_custom_question(
                            symbol, 
                            st.session_state.stock_info, 
                            st.session_state.stock_data, 
                            st.session_state.custom_question
                        )
                else:
                    st.session_state.custom_analysis_result = "请先输入您想要分析的问题"
            
            # 使用列布局
            col1, col2 = st.columns([3, 1])
            
            # 自定义问题输入
            with col1:
                st.text_area(
                    "输入您想了解的具体问题",
                    value=st.session_state.custom_question,
                    placeholder="例如：\n1. 请分析该公司在人工智能领域的发展前景\n2. 详细分析公司的现金流情况\n3. 分析公司的市场份额和主要竞争对手",
                    help="您可以输入任何关于这支股票的具体问题，AI 将为您提供专业的分析",
                    height=100,
                    key="custom_question"
                )
            
            # 分析按钮
            with col2:
                st.write("")  # 添加一些空间使按钮对齐
                st.write("")
                st.button(
                    "分析自定义问题",
                    on_click=on_analyze_click,
                    type="primary",
                    use_container_width=True,
                    key="analyze_button"
                )
            
            # 显示自定义分析结果
            if st.session_state.custom_analysis_result:
                if st.session_state.custom_analysis_result.startswith("请先输入"):
                    st.warning(st.session_state.custom_analysis_result)
                else:
                    st.markdown(st.session_state.custom_analysis_result)
            
            # 显示交易数据表格
            st.subheader("最近交易数据")
            st.dataframe(st.session_state.stock_data.tail(10))
        else:
            st.error("无法获取数据，请检查股票代码是否正确")

if __name__ == "__main__":
    main()
