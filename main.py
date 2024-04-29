import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import LSTM, Dense
import matplotlib.pyplot as plt

def fetch_data(stock_name, start_date='2010-01-01', end_date='2023-01-01'):
    data = yf.download(stock_name, start=start_date, end=end_date)
    return data['Close'].values.reshape(-1, 1)  # We use only the closing prices

def prepare_data(data, n_steps=50):
    scaler = MinMaxScaler(feature_range=(0, 1))
    data_scaled = scaler.fit_transform(data)
    
    X, y = [], []
    for i in range(n_steps, len(data_scaled)):
        X.append(data_scaled[i-n_steps:i, 0])
        y.append(data_scaled[i, 0])
    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))
    return X, y, scaler

def build_model(input_shape):
    model = Sequential([
        LSTM(50, return_sequences=True, input_shape=input_shape),
        LSTM(50, return_sequences=False),
        Dense(25),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

def predict_future_prices(model, data, scaler, future_months=3, steps_per_month=20):
    test_inputs = data[-50:].reshape(-1, 1)
    test_inputs = scaler.transform(test_inputs)

    predictions = []
    for _ in range(future_months * steps_per_month):
        X_test = np.array([test_inputs[-50:]])
        X_test = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], 1))
        pred_price = model.predict(X_test)
        test_inputs = np.append(test_inputs, pred_price)
        predictions.append(scaler.inverse_transform(pred_price))

    return np.array(predictions).reshape(-1, 1)

# Example usage
stock_name = "AAPL"
data = fetch_data(stock_name)
X_train, y_train, scaler = prepare_data(data)
model = build_model((X_train.shape[1], 1))
model.fit(X_train, y_train, epochs=20, batch_size=32)

# Predict future prices
future_prices = predict_future_prices(model, data, scaler)
plt.plot(future_prices)
plt.title('Future Stock Prices')
plt.xlabel('Time')
plt.ylabel('Price')
plt.show()