from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)  # Allow all origins — required for github.io

# ── Symbol maps ─────────────────────────────────────────────────
# Your stooq-style symbols → Yahoo Finance symbols
INDICES_MAP = {
    # Indian indices
    '^nsei':     '^NSEI',
    '^bsesn':    '^BSESN',
    '^nsebank':  '^NSEBANK',
    '^cnxit':    '^CNXIT',
    '^cnxpharma':'^CNXPHARMA',
    '^cnxauto':  '^CNXAUTO',
    '^cnxfmcg':  '^CNXFMCG',
    '^cnxmetal': '^CNXMETAL',
    '^cnxpsubn': '^CNXPSUBN',
    '^indiavix': '^INDIAVIX',
    # Global indices
    '^spx':      '^GSPC',
    '^ndx':      '^NDX',
    '^dji':      '^DJI',
    '^n225':     '^N225',
    '^hsi':      '^HSI',
    '^dax':      '^GDAXI',
    '^ftse':     '^FTSE',
    '^ssec':     '000001.SS',
    '^fchi':     '^FCHI',
    # Currencies & commodities
    'usd/inr':   'USDINR=X',
    'eur/inr':   'EURINR=X',
    'gbp/inr':   'GBPINR=X',
    'xau/usd':   'GC=F',
    'xag/usd':   'SI=F',
    'cl.f':      'CL=F',
    'btc/usd':   'BTC-USD',
}

def safe_float(val):
    try:
        v = float(val)
        return round(v, 4) if v == v else None  # NaN check
    except:
        return None

# ── /indices ────────────────────────────────────────────────────
@app.route('/indices')
def indices():
    syms_param = request.args.get('s', '')
    if not syms_param:
        return jsonify({'ok': False, 'error': 'Missing s= parameter'}), 400

    requested = [s.strip().lower() for s in syms_param.split(',') if s.strip()]
    yahoo_syms = [INDICES_MAP.get(s, s) for s in requested]

    try:
        tickers = yf.Tickers(' '.join(yahoo_syms))
        data = []
        for i, req_sym in enumerate(requested):
            yahoo_sym = yahoo_syms[i]
            try:
                info = tickers.tickers[yahoo_sym].fast_info
                price      = safe_float(info.last_price)
                prev_close = safe_float(info.previous_close)
                if price is None or price <= 0:
                    continue
                base = prev_close if prev_close and prev_close > 0 else price
                chg  = round(price - base, 4)
                pct  = round((price - base) / base * 100, 4) if base > 0 else 0
                data.append({
                    'sym':       req_sym,
                    'val':       price,
                    'chg':       chg,
                    'pct':       pct,
                    'prevClose': base,
                })
            except Exception as e:
                print(f'[INDICES] Skip {req_sym}: {e}')
                continue

        if not data:
            return jsonify({'ok': False, 'error': 'No data from yfinance'})

        return jsonify({'ok': True, 'source': 'yfinance', 'count': len(data), 'data': data})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ── /prices ─────────────────────────────────────────────────────
# Called with selected client's symbols only (10-20 max)
@app.route('/prices')
def prices():
    syms_param = request.args.get('s', '')
    if not syms_param:
        return jsonify({'ok': False, 'error': 'Missing s= parameter'}), 400

    symbols = [s.strip() for s in syms_param.split(',') if s.strip()]
    if not symbols:
        return jsonify({'ok': False, 'error': 'No symbols'}), 400

    # Ensure .NS suffix for NSE stocks
    yahoo_syms = []
    for s in symbols:
        if '.' not in s:
            yahoo_syms.append(s + '.NS')
        else:
            yahoo_syms.append(s)

    try:
        tickers = yf.Tickers(' '.join(yahoo_syms))
        data = []
        for i, orig in enumerate(symbols):
            yahoo_sym = yahoo_syms[i]
            try:
                info = tickers.tickers[yahoo_sym].fast_info
                price      = safe_float(info.last_price)
                prev_close = safe_float(info.previous_close)
                if price is None or price <= 0:
                    continue
                base      = prev_close if prev_close and prev_close > 0 else price
                change    = round(price - base, 4)
                change_pct = round((price - base) / base * 100, 4) if base > 0 else 0
                data.append({
                    'symbol':    yahoo_sym,
                    'price':     price,
                    'prevClose': base,
                    'changeAbs': change,
                    'changePct': change_pct,
                })
            except Exception as e:
                print(f'[PRICES] Skip {orig}: {e}')
                continue

        if not data:
            return jsonify({'ok': False, 'error': 'No data from yfinance'})

        return jsonify({'ok': True, 'source': 'yfinance', 'count': len(data), 'data': data})

    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ── /health ──────────────────────────────────────────────────────
@app.route('/health')
def health():
    return jsonify({'ok': True, 'service': 'autus-yfinance', 'version': 1})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
