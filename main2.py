import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from prophet import Prophet
import datetime
from prophet.plot import plot_plotly, plot_components

def fetch_data(ticker, start_date, end_date):
    data = yf.download(ticker, start=start_date, end=end_date)
    return data

def plot_data(data, title):
    plt.figure(figsize=(10, 5))
    plt.plot(data['Close'], label='Close Price')
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    plt.legend()
    plt.grid(True)
    plt.show()

def stock_performance_comparison(tickers, start, end):
    data = yf.download(tickers, start=start, end=end)
    return data['Adj Close']

def real_time_stock_price(ticker, start, end):
    return fetch_data(ticker, start, end)

def stock_price_prediction(ticker, start, end, periods):
    data = real_time_stock_price(ticker, start, end)
    df_train = data.reset_index()[['Date', 'Close']]
    df_train.rename(columns={'Date': 'ds', 'Close': 'y'}, inplace=True)
    
    m = Prophet()
    m.fit(df_train)
    future = m.make_future_dataframe(periods=periods)
    forecast = m.predict(future)
    
    fig1 = plot_plotly(m, forecast)
    plot_components(m, forecast)
    
    return forecast, fig1

# Main Script
print("Welcome to StockStream Console App")
print("1. Stock Performance Comparison")
print("2. Real-Time Stock Price")
print("3. Stock Price Prediction")

choice = input("Enter your choice (1-3): ")

stock_df = pd.read_csv("StockStreamTickersData.csv")
tickers = stock_df["Company Name"].tolist()
symbols = stock_df.set_index("Company Name")["Ticker"].to_dict()

if choice == '1':
    selected_tickers = input("Enter tickers separated by comma: ").split(',')
    symbols_list = [symbols[ticker.strip()] for ticker in selected_tickers if ticker.strip() in symbols]
    start_date = input("Enter start date (YYYY-MM-DD): ")
    end_date = input("Enter end date (YYYY-MM-DD): ")
    data = stock_performance_comparison(symbols_list, start_date, end_date)
    plot_data(data, "Stock Performance Comparison")

elif choice == '2':
    ticker = input("Enter a ticker name: ").strip()
    if ticker in symbols:
        start_date = input("Enter start date (YYYY-MM-DD): ")
        end_date = input("Enter end date (YYYY-MM-DD): ")
        data = real_time_stock_price(symbols[ticker], start_date, end_date)
        plot_data(data, f"Real-Time Stock Price for {ticker}")

elif choice == '3':
    ticker = input("Enter a ticker name: ").strip()
    if ticker in symbols:
        start_date = input("Enter start date (YYYY-MM-DD): ")
        end_date = input("Enter end date (YYYY-MM-DD): ")
        periods = int(input("Enter the number of days for prediction: "))
        forecast, fig1 = stock_price_prediction(symbols[ticker], start_date, end_date, periods)
        print(forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']])
        fig1.show()