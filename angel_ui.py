import tkinter as tk
from tkinter import messagebox, simpledialog
import csv
import threading
import pyotp
import json
import requests
import hashlib
from SmartApi import SmartConnect
from logzero import logger, logfile

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
            if exchange.upper() == "NSE" and "-EQ" in symbol:
                trading_symbol = symbol
                symbol_token = item.get("token", None)
                return trading_symbol, symbol_token
            elif exchange.upper() == "BSE" and "-EQ" not in symbol:
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
        self.master.geometry("800x600")

        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_frame = tk.Frame(self.main_frame, bg="lightgray")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.stock_label = tk.Label(self.left_frame, text="Stock Name:")
        self.stock_label.pack()
        self.stock_entry = tk.Entry(self.left_frame)
        self.stock_entry.pack()

        self.transaction_label = tk.Label(self.left_frame, text="Transaction Type:")
        self.transaction_label.pack()
        self.transaction_var = tk.StringVar(value="BUY")
        self.transaction_buy_radio = tk.Radiobutton(self.left_frame, text="BUY", variable=self.transaction_var, value="BUY")
        self.transaction_buy_radio.pack()
        self.transaction_sell_radio = tk.Radiobutton(self.left_frame, text="SELL", variable=self.transaction_var, value="SELL")
        self.transaction_sell_radio.pack()

        self.product_label = tk.Label(self.left_frame, text="Product Type:")
        self.product_label.pack()
        self.product_var = tk.StringVar(value="DELIVERY")
        self.product_delivery_radio = tk.Radiobutton(self.left_frame, text="DELIVERY", variable=self.product_var, value="DELIVERY")
        self.product_intraday_radio = tk.Radiobutton(self.left_frame, text="INTRADAY", variable=self.product_var, value="INTRADAY")
        self.product_delivery_radio.pack()
        self.product_intraday_radio.pack()

        self.exchange_label = tk.Label(self.left_frame, text="Exchange:")
        self.exchange_label.pack()
        self.exchange_var = tk.StringVar(value="NSE")
        self.exchange_nse_radio = tk.Radiobutton(self.left_frame, text="NSE", variable=self.exchange_var, value="NSE")
        self.exchange_bse_radio = tk.Radiobutton(self.left_frame, text="BSE", variable=self.exchange_var, value="BSE")
        self.exchange_nse_radio.pack()
        self.exchange_bse_radio.pack()

        self.order_label = tk.Label(self.left_frame, text="Order Type:")
        self.order_label.pack()

        self.order_var = tk.StringVar(value="MARKET")
        self.order_market_radio = tk.Radiobutton(self.left_frame, text="MARKET", variable=self.order_var, value="MARKET", command=self.toggle_price_entry)
        self.order_market_radio.pack()

        self.order_limit_radio = tk.Radiobutton(self.left_frame, text="LIMIT", variable=self.order_var, value="LIMIT", command=self.toggle_price_entry)
        self.order_limit_radio.pack()

        self.price_label = tk.Label(self.left_frame, text="Price (if LIMIT order):")
        self.price_label.pack()
        self.price_entry = tk.Entry(self.left_frame)
        self.price_entry.pack()

        self.quantity_label = tk.Label(self.left_frame, text="Quantity:")
        self.quantity_label.pack()
        self.quantity_entry = tk.Entry(self.left_frame)
        self.quantity_entry.pack()

        self.accounts_frame = tk.Frame(self.right_frame, bg="lightgray")
        self.accounts_frame.pack(fill=tk.BOTH, expand=True)

        self.accounts = []
        # Read data.csv file
        try:
            with open('data.csv', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    account_var = tk.BooleanVar()
                    account_checkbox = tk.Checkbutton(self.accounts_frame, text=row['username'], variable=account_var)
                    account_checkbox.pack(anchor="w")
                    self.accounts.append((row, account_var))
        except FileNotFoundError:
            messagebox.showerror("Error", "data.csv file not found.")

        self.select_all_var = tk.BooleanVar()
        self.select_all_checkbox = tk.Checkbutton(self.right_frame, text="Select All", variable=self.select_all_var, command=self.toggle_select_all)
        self.select_all_checkbox.pack()

        self.output_text = tk.Text(self.right_frame, height=10, width=50)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        self.submit_button = tk.Button(self.right_frame, text="Submit", command=self.submit)
        self.submit_button.pack()

        # Initially, hide the price entry
        self.toggle_price_entry()

    def toggle_price_entry(self):
        if self.order_var.get() == "LIMIT":
            self.price_label.pack()
            self.price_entry.pack(side="left")
            # Enable price entry when order type is LIMIT
            self.price_entry.config(state="normal")
        else:
            self.price_label.pack_forget()
            self.price_entry.pack_forget()

    def toggle_select_all(self):
        select_all_state = self.select_all_var.get()
        for _, account_var in self.accounts:
            account_var.set(select_all_state)

    def submit(self):
        stock_name = self.stock_entry.get()
        transaction_type = self.transaction_var.get()
        product_type = self.product_var.get()
        exchange = self.exchange_var.get()
        order_type = self.order_var.get()
        price = self.price_entry.get()
        quantity = self.quantity_entry.get()

        if not stock_name or not quantity:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        # Set price to 0 for market order and disable price entry
        if order_type == "MARKET":
            price = "0"
            self.price_entry.config(state="disabled")

        # Load JSON data
        check_json_update()

        # Clear the output text before submitting new orders
        self.output_text.delete(1.0, tk.END)

        # Read data.csv file
        try:
            threads = []
            for row, account_var in self.accounts:
                if account_var.get():  # Only process selected accounts
                    api_key = row['api_key']
                    username = row['username']
                    password = row['password']
                    demo_token = row['demo_token']
                    available_funds = float(row['available_funds'])

                    # Print user info
                    print_user_info(username, available_funds, self.output_text)

                    # Create a thread for each account and start it
                    thread = threading.Thread(target=self.place_order_for_account, args=(api_key, username, password, demo_token, stock_name, transaction_type, product_type, exchange, available_funds, order_type, price, quantity))
                    threads.append(thread)
                    thread.start()

                    # Schedule a function to check thread status periodically
                    self.check_thread_status(thread, username)

            # Schedule a function to update GUI after a delay
            self.master.after(1000, self.update_gui, threads)

        except FileNotFoundError:
            messagebox.showerror("Error", "data.csv file not found.")

    def place_order_for_account(self, api_key, username, password, demo_token, stock_name, transaction_type, product_type, exchange, available_funds, order_type, price, quantity):
        place_order(api_key, username, password, demo_token, stock_name, transaction_type, product_type, exchange, available_funds, order_type, price, quantity, self.output_text)

    def check_thread_status(self, thread, username):
        if not thread.is_alive():
            logger.info(f"Thread for {username} has completed.")
        else:
            # Reschedule the function to check thread status after a delay
            self.master.after(1000, self.check_thread_status, thread, username)

    def update_gui(self, threads):
        # Check if any thread is still alive
        if any(thread.is_alive() for thread in threads):
            # Reschedule the function to update GUI after a delay
            self.master.after(1000, self.update_gui, threads)
        else:
            # All threads have completed, update GUI accordingly
            messagebox.showinfo("Info", "All orders have been placed.")

            # Reset the price entry field
            self.price_entry.delete(0, tk.END)
            self.toggle_price_entry()

def main():
    root = tk.Tk()
    app = TradingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()