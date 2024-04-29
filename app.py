from flask import Flask, render_template, request, url_for
import yfinance as yf
from prophet import Prophet
import pandas as pd
from prophet.plot import plot_plotly
import json
import plotly

app = Flask(__name__)

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Real-Time Stock Price
@app.route('/real_time', methods=['GET', 'POST'])
def real_time():
    if request.method == 'POST':
        symbol = request.form['symbol']
        data = yf.download(symbol, period='1d', interval='5m')
        return render_template('real_time.html', symbol=symbol, data=data.to_html())
    else:
        return render_template('real_time.html')

# Stock Price Prediction
@app.route('/prediction', methods=['GET', 'POST'])
def prediction():
    if request.method == 'POST':
        symbol = request.form['symbol']
        period = int(request.form['period'])
        data = yf.download(symbol, period='5y')['Close']
        df = pd.DataFrame(data).reset_index()
        df.columns = ['ds', 'y']

        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=period)
        forecast = model.predict(future)

        fig = plot_plotly(model, forecast)
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

        return render_template('prediction.html', plot=graph_json)
    else:
        return render_template('prediction.html')

if __name__ == '__main__':
    app.run(debug=True)