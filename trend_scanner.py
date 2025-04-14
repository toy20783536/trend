import requests
import pandas as pd
from tqdm import tqdm

# ========== Telegram 通知功能 ==========
def send_telegram_message(message):
    TOKEN = '7942922543:AAFQUVrbpAlGVNyj50r0NdpEO5syhWp0weQ'
    CHAT_ID = '6274372358'  # 整數或字串都可
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ 傳送 Telegram 失敗：{e}")

# ========== 幣安資料處理 ==========
def get_symbols():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    symbols = [item['symbol'] for item in data['symbols']
               if item['contractType'] == 'PERPETUAL' and item['status'] == 'TRADING']
    return symbols

def get_24h_volumes():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return {item['symbol']: float(item['quoteVolume']) for item in data}
    except Exception as e:
        print(f"Error fetching 24H volumes: {e}")
        return {}

def get_klines(symbol, interval='4h', limit=200):
    try:
        url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        response = requests.get(url)
        response.raise_for_status()
        klines = response.json()
        if len(klines) == 0:
            return None
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        return df if df.shape[0] >= 80 else None
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def calculate_indicators(df, ema_windows=[20, 60, 80]):
    for window in ema_windows:
        df[f'EMA_{window}'] = df['close'].ewm(span=window, adjust=False).mean()
    return df

# ========== 篩選條件 ==========
def is_converging(df, threshold_ratio=0.005):
    if df.isnull().values.any():
        return False
    recent = df.iloc[-1]
    ema_20, ema_80, close = recent['EMA_20'], recent['EMA_80'], recent['close']
    return abs(ema_20 - ema_80) / close < threshold_ratio

def is_bullish(df, tight_threshold=0.03):
    recent = df.iloc[-1]
    ema20, ema60, ema80 = recent['EMA_20'], recent['EMA_60'], recent['EMA_80']
    close = recent['close']
    return ema20 > ema60 > ema80 and close > ema20 and close > ema60 and close > ema80 and \
           (max(ema20, ema60, ema80) - min(ema20, ema60, ema80)) / close < tight_threshold

def is_bearish(df, tight_threshold=0.03):
    recent = df.iloc[-1]
    ema20, ema60, ema80 = recent['EMA_20'], recent['EMA_60'], recent['EMA_80']
    close = recent['close']
    return ema20 < ema60 < ema80 and close < ema20 and close < ema60 and close < ema80 and \
           (max(ema20, ema60, ema80) - min(ema20, ema60, ema80)) / close < tight_threshold

# ========== 主邏輯 ==========
def run_all_filters():
    symbols = get_symbols()
    volume_map = get_24h_volumes()
    bullish, bearish, converging = [], [], []

    for symbol in tqdm(symbols, desc="篩選中", ncols=80):
        if symbol not in volume_map or volume_map[symbol] < 50000000:
            continue  # ➤ 排除成交量小於 5,000萬 USDT 的幣種

        df = get_klines(symbol)
        if df is not None:
            df = calculate_indicators(df)
            if is_bullish(df):
                bullish.append(symbol)
            if is_bearish(df):
                bearish.append(symbol)
            if is_converging(df):
                converging.append(symbol)

    # 終端輸出
    print("\n✅ 多頭排列 + 密集 + 收盤價站上：")
    print(bullish if bullish else "無符合的交易對")
    print("\n🔻 空頭排列 + 密集 + 收盤價站下：")
    print(bearish if bearish else "無符合的交易對")
    print("\n📉 EMA20 與 EMA80 差距小（可能即將出方向）：")
    print(converging if converging else "無符合的交易對")

    # 傳送到 Telegram
    message = "📊 [4H 趨勢掃描結果 - 成交量過濾]\n"
    message += "\n✅ 多頭：\n" + (', '.join(bullish) if bullish else "無")
    message += "\n🔻 空頭：\n" + (', '.join(bearish) if bearish else "無")
    message += "\n📉 收斂：\n" + (', '.join(converging) if converging else "無")
    send_telegram_message(message)

# 執行
run_all_filters()
