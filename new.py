import tkinter as tk
from tkinter import messagebox
import threading
import pyotp
import json
import requests
import hashlib
from SmartApi import SmartConnect
from logzero import logger, logfile
import yfinance as yf
import pandas as pd
from prophet import Prophet
from prophet.plot import plot_plotly
import plotly.offline as py
import webbrowser
import os
import csv

# Configure logging
logfile("trading_log.log", maxBytes=1e6, backupCount=3)

# Global variables
json_data = None
last_json_hash = None

def print_user_info(username, available_funds, output_text):
    logger.info(f"Username: {username}")
    logger.info(f"Available Funds: {available_funds}")
    output_text.insert(tk.END, f"Username: {username}\n")
    output_text.insert(tk.END, f"Available Funds: {available_funds}\n")

def fetch_symbol_token(stock_name, exchange):
    global json_data
    if json_data is None:
        logger.error("JSON data is not loaded.")
        return None, None
    for item in json_data:
        name = item.get("name", "").upper()
        symbol = item.get("symbol", "").upper()
        exch_seg = item.get("exch_seg", "").upper()
        if name == stock_name.upper() and exch_seg == exchange.upper():
            trading_symbol = symbol
            symbol_token = item.get("token", None)
            return trading_symbol, symbol_token
    logger.error(f"Symbol not found for stock name: {stock_name} and exchange: {exchange}")
    return None, None

def fetch_json_data(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Failed to fetch JSON data. Status code: {response.status_code}")
        return None

def calculate_hash(data):
    json_string = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_string.encode()).hexdigest()

def check_json_update():
    global last_json_hash, json_data
    json_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = fetch_json_data(json_url)
    if data:
        current_hash = calculate_hash(data)
        if current_hash != last_json_hash:
            logger.info("JSON data has been updated.")
            last_json_hash = current_hash
            json_data = data
        else:
            logger.info("JSON data has not been updated.")

def place_order(api_key, username, password, demo_token, tradingsymbol, transactiontype, producttype, exchange, available_funds, order_type, price, quantity, output_text):
    try:
        smartApi = SmartConnect(api_key)
        totp = pyotp.TOTP(demo_token).now()
        data = smartApi.generateSession(username, password, totp)
        if data['status'] == False:
            logger.error(data)
            return
        authToken = data['data']['jwtToken']
        refreshToken = data['data']['refreshToken']
        trading_symbol, symbol_token = fetch_symbol_token(tradingsymbol, exchange)
        if symbol_token:
            logger.info(f"Placing order for {quantity} shares of {trading_symbol} for account {username}...")
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": trading_symbol,
                "symboltoken": symbol_token,
                "transactiontype": transactiontype,
                "exchange": exchange.upper(),
                "ordertype": order_type.upper(),
                "producttype": producttype,
                "duration": "DAY",
                "price": str(price) if price is not None else "0",
                "squareoff": "0",
                "stoploss": "0",
                "quantity": quantity
            }
            response = smartApi.placeOrderFullResponse(orderparams)
            if isinstance(response, str):
                response = json.loads(response)
            logger.info(f"Order response: {response}")
            output_text.insert(tk.END, f"Order response for {username}: {response}\n")
            logout = smartApi.terminateSession('Your Client Id')
        else:
            logger.error("Symbol Token not found for the stock symbol.")
    except Exception as e:
        logger.exception(f"Error placing order for {username}: {e}")

class TradingApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Trading Application")
        self.master.geometry("1000x700")

        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_frame = tk.Frame(self.main_frame, bg="lightgray")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Existing UI setup omitted for brevity...
        self.prediction_frame = tk.Frame(self.left_frame)
        self.prediction_frame.pack(fill=tk.BOTH, expand=True)
        
        self.symbol_label = tk.Label(self.prediction_frame, text="Enter Symbol for Prediction:")
        self.symbol_label.pack()
        self.symbol_entry = tk.Entry(self.prediction_frame)
        self.symbol_entry.pack()
        
        self.predict_button = tk.Button(self.prediction_frame, text="Predict", command=self.predict_price)
        self.predict_button.pack()
        
        self.recommendation_label = tk.Label(self.prediction_frame, text="")
        self.recommendation_label.pack()

        # Other elements such as Radiobuttons, Entries, and Labels...

    def predict_price(self):
        symbol = self.symbol_entry.get()
        if not symbol:
            messagebox.showerror("Error", "Please enter a stock symbol.")
            return
        data = yf.download(symbol, period='5y')['Close']
        current_price = data.iloc[-1]
        df = pd.DataFrame(data).reset_index()
        df.columns = ['ds', 'y']
        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=365)
        forecast = model.predict(future)
        fig = plot_plotly(model, forecast)
        plot_url = 'temp-plot.html'
        py.plot(fig, filename=plot_url, auto_open=False)
        webbrowser.open('file://' + os.path.realpath(plot_url))

        predicted_price = forecast.iloc[-1]['yhat']
        percentage_change = ((predicted_price - current_price) / current_price) * 100
        recommendation = 'Buy' if predicted_price > current_price else 'Sell'
        self.recommendation_label.config(text=f"Recommendation: {recommendation}, Change: {percentage_change:.2f}%, Current: {current_price:.2f}, Predicted: {predicted_price:.2f}")

def main():
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()