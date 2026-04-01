from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf

app = Flask(__name__)
CORS(app)

# Stooq-style symbol → Yahoo Finance symbol
INDICES_MAP = {
    '^nsei':       '^NSEI',
    '^bsesn':      '^BSESN',
    '^nsebank':    '^NSEBANK',
    '^cnxit':      '^CNXIT',
    '^cnxpharma':  '^CNXPHARMA',
    '^cnxauto':    '^CNXAUTO',
    '^cnxfmcg':    '^CNXFMCG',
    '^cnxmetal':   '^CNXMETAL',
    '^cnxpsubn':   '^CNXPSUBN',
    '^cnxsc':      '^CNXSC',        # NIFTY SmallCap 100
    '^cnxmidcap':  '^CNXMIDCAP',    # NIFTY MidCap 100
    '^indiavix':   '^INDIAVIX',
    '^spx':        '^GSPC',
    '^ndx':        '^NDX',
    '^dji':        '^DJI',
    '^n225':       '^N225',
    '^hsi':        '^HSI',
    '^dax':        '^GDAXI',
    '^ftse':       '^FTSE',
    '^ssec':       '000001.SS',
    '^fchi':       '^FCHI',
    'usd/inr':     'USDINR=X',
    'eur/inr':     'EURINR=X',
    'gbp/inr':     'GBPINR=X',
    'xau/usd':     'GC=F',
    'xag/usd':     'SI=F',
    'cl.f':        'CL=F',
    'btc/usd':     'BTC-USD',
}

# NSE symbols that need special handling
SYMBOL_FIXES = {
    'GVT&D':    'GETD.NS',
    'GET&D':    'GETD.NS',
    'GVT&D.NS': 'GETD.NS',
    'GET&D.NS': 'GETD.NS',
}

def safe_float(val):
    try:
        v = float(val)
        return round(v, 4) if v == v else None  # NaN check
    except:
        return None

def fetch_info(yahoo_sym):
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
    return jsonify({'ok': True, 'service': 'autus-yfinance', 'version': 3})

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
            print(f'[INDICES] No data: {req_sym} ({yahoo_sym})')

    if not data:
        return jsonify({'ok': False, 'error': 'No data from yfinance'})
    return jsonify({'ok': True, 'source': 'yfinance', 'count': len(data), 'data': data})

@app.route('/prices')
def prices():
    syms_param = request.args.get('s', '').strip()
    if not syms_param:
        return jsonify({'ok': False, 'error': 'Missing s='}), 400

    symbols = [s.strip() for s in syms_param.split(',') if s.strip()]
    data = []

    for sym in symbols:
        # Apply known symbol fixes first
        fixed = SYMBOL_FIXES.get(sym, sym)
        # Add .NS suffix for bare NSE symbols
        if '.' not in fixed and '=' not in fixed and not fixed.startswith('^'):
            yahoo_sym = fixed + '.NS'
        else:
            yahoo_sym = fixed

        result = fetch_info(yahoo_sym)
        if result:
            data.append({
                'symbol':    yahoo_sym,
                'price':     result['price'],
                'prevClose': result['prevClose'],
                'changeAbs': result['changeAbs'],
                'changePct': result['changePct'],
            })
        else:
            # Try BSE fallback for NSE failures
            bse_sym = yahoo_sym.replace('.NS', '.BO')
            result2 = fetch_info(bse_sym)
            if result2:
                data.append({
                    'symbol':    yahoo_sym,  # return original symbol for frontend mapping
                    'price':     result2['price'],
                    'prevClose': result2['prevClose'],
                    'changeAbs': result2['changeAbs'],
                    'changePct': result2['changePct'],
                })
                print(f'[PRICES] BSE fallback OK: {bse_sym}')

    if not data:
        return jsonify({'ok': False, 'error': 'No data from yfinance'})
    return jsonify({'ok': True, 'source': 'yfinance', 'count': len(data), 'data': data})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
