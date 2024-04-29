import tkinter as tk
from tkinter import messagebox, Toplevel
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

class PredictionWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Stock Price Prediction")
        self.master.geometry("600x400")

        self.label = tk.Label(master, text="Enter Symbol for Prediction:")
        self.label.pack()
        self.entry = tk.Entry(master)
        self.entry.pack()

        self.button = tk.Button(master, text="Predict", command=self.predict_price)
        self.button.pack()

        self.output = tk.Text(master, height=10, width=50)
        self.output.pack()

    def predict_price(self):
        symbol = self.entry.get()
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

        predicted_price = forecast.iloc[-1]['yhat']
        percentage_change = ((predicted_price - current_price) / current_price) * 100

        recommendation = 'Buy' if predicted_price > current_price else 'Sell'
        self.output.insert(tk.END, f"Prediction: {recommendation}\nChange: {percentage_change:.2f}%\nCurrent: {current_price:.2f}\nPredicted: {predicted_price:.2f}\n")

        # Plotting
        fig = plot_plotly(model, forecast)
        plot_url = 'temp-plot.html'
        py.plot(fig, filename=plot_url, auto_open=False)
        webbrowser.open('file://' + os.path.realpath(plot_url))

class TradingApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Trading Application")
        self.master.geometry("800x600")

        self.label = tk.Label(master, text="Welcome to the Trading App")
        self.label.pack()

        self.open_prediction_window_button = tk.Button(master, text="Open Prediction Window", command=self.open_prediction_window)
        self.open_prediction_window_button.pack()

        # Additional components like trading order setup
        self.order_frame = tk.Frame(master)
        self.order_frame.pack()

        self.stock_label = tk.Label(self.order_frame, text="Stock Name:")
        self.stock_label.pack()
        self.stock_entry = tk.Entry(self.order_frame)
        self.stock_entry.pack()

        self.quantity_label = tk.Label(self.order_frame, text="Quantity:")
        self.quantity_label.pack()
        self.quantity_entry = tk.Entry(self.order_frame)
        self.quantity_entry.pack()

        self.place_order_button = tk.Button(self.order_frame, text="Place Order", command=self.place_order_from_gui)
        self.place_order_button.pack()

        self.output_text = tk.Text(master, height=10, width=50)
        self.output_text.pack()

    def open_prediction_window(self):
        new_window = Toplevel(self.master)
        pred_window = PredictionWindow(new_window)

    def place_order_from_gui(self):
        # Assuming all details for an order are set up similarly
        stock_name = self.stock_entry.get()
        quantity = int(self.quantity_entry.get())
        place_order("api_key", "username", "password", "demo_token", stock_name, "BUY", "INTRADAY", "NSE", 10000, "MARKET", None, quantity, self.output_text)

def main():
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()