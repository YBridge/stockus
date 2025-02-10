# Stock Analysis Application

一个基于 Streamlit 和 Perplexity API 的股票分析应用程序，支持美股和 A 股市场。

## 功能特点

- 支持美股和 A 股市场
- 实时股票数据获取和显示
- K线图可视化
- 技术指标分析（MA5、MA20、MA60、RSI等）
- 基本面分析
- 自定义问题分析
- 数据缓存和会话管理

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/YBridge/stockus.git
cd stockus
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
创建 `.env` 文件并添加您的 Perplexity API 密钥：
```
PERPLEXITY_API_KEY=your_api_key_here
```

## 运行

```bash
streamlit run app.py
```

## 使用说明

1. 选择市场（美股/A股）
2. 选择时间范围
3. 输入股票代码（例如：AAPL、600519）
4. 查看基础分析报告
5. 输入自定义问题获取针对性分析

## 依赖

- streamlit==1.31.0
- yfinance==0.2.36
- plotly==5.18.0
- python-dotenv==1.0.1
- requests==2.31.0

## 注意事项

- 需要有效的 Perplexity API 密钥
- A股代码会自动添加市场后缀（.SS或.SZ）
- 建议使用稳定的网络连接
