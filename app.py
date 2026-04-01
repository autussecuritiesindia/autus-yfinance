from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

# Stooq-style symbol → Yahoo Finance symbol
INDICES_MAP = {
    '^nsei':      '^NSEI',
    '^bsesn':     '^BSESN',
    '^nsebank':   '^NSEBANK',
    '^cnxit':     '^CNXIT',
    '^cnxpharma': '^CNXPHARMA',
    '^cnxauto':   '^CNXAUTO',
    '^cnxfmcg':   '^CNXFMCG',
    '^cnxmetal':  '^CNXMETAL',
    '^cnxpsubn':  '^CNXPSUBN',
    '^indiavix':  '^INDIAVIX',
    '^spx':       '^GSPC',
    '^ndx':       '^NDX',
    '^dji':       '^DJI',
    '^n225':      '^N225',
    '^hsi':       '^HSI',
    '^dax':       '^GDAXI',
    '^ftse':      '^FTSE',
    '^ssec':      '000001.SS',
    '^fchi':      '^FCHI',
    'usd/inr':    'USDINR=X',
    'eur/inr':    'EURINR=X',
    'gbp/inr':    'GBPINR=X',
    'xau/usd':    'GC=F',
    'xag/usd':    'SI=F',
    'cl.f':       'CL=F',
    'btc/usd':    'BTC-USD',
}

def safe_float(val):
    try:
        v = float(val)
        return round(v, 4) if v == v else None
    except:
        return None

def fetch_info(yahoo_sym):
    """Fetch fast_info for a single symbol, returns dict or None."""
    try:
        t = yf.Ticker(yahoo_sym)
        info = t.fast_info
        price = safe_float(info.last_price)
        prev  = safe_float(info.previous_close)
        if not price or price <= 0:
            return None
        base = prev if prev and prev > 0 else price
        return {
            'price':     price,
            'prevClose': base,
            'changeAbs': round(price - base, 4),
            'changePct': round((price - base) / base * 100, 4) if base > 0 else 0,
        }
    except Exception as e:
        print(f'[WARN] {yahoo_sym}: {e}')
        return None


@app.route('/health')
def health():
    return jsonify({'ok': True, 'service': 'autus-yfinance', 'version': 2})


@app.route('/indices')
def indices():
    syms_param = request.args.get('s', '').strip()
    if not syms_param:
        return jsonify({'ok': False, 'error': 'Missing s='}), 400

    requested = [s.strip().lower() for s in syms_param.split(',') if s.strip()]
    data = []

    for req_sym in requested:
        yahoo_sym = INDICES_MAP.get(req_sym)
        if not yahoo_sym:
            print(f'[INDICES] No mapping for {req_sym}')
            continue
        result = fetch_info(yahoo_sym)
        if result:
            data.append({
                'sym':       req_sym,
                'val':       result['price'],
                'chg':       result['changeAbs'],
                'pct':       result['changePct'],
                'prevClose': result['prevClose'],
            })
        else:
            print(f'[INDICES] No data for {req_sym} ({yahoo_sym})')

    if not data:
        return jsonify({'ok': False, 'error': 'No data returned from yfinance'})

    return jsonify({'ok': True, 'source': 'yfinance', 'count': len(data), 'data': data})


@app.route('/prices')
def prices():
    syms_param = request.args.get('s', '').strip()
    if not syms_param:
        return jsonify({'ok': False, 'error': 'Missing s='}), 400

    symbols = [s.strip() for s in syms_param.split(',') if s.strip()]
    data = []

    for sym in symbols:
        # Add .NS suffix for NSE stocks if no exchange suffix present
        yahoo_sym = sym if '.' in sym or '=' in sym or sym.startswith('^') else sym + '.NS'
        result = fetch_info(yahoo_sym)
        if result:
            data.append({
                'symbol':    yahoo_sym,
                'price':     result['price'],
                'prevClose': result['prevClose'],
                'changeAbs': result['changeAbs'],
                'changePct': result['changePct'],
            })

    if not data:
        return jsonify({'ok': False, 'error': 'No data returned from yfinance'})

    return jsonify({'ok': True, 'source': 'yfinance', 'count': len(data), 'data': data})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
