#!/bin/bash
# Start the Live Stock Picks website and open it in your browser.

cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"

# Ensure Flask is installed
if ! python3 -c "import flask" 2>/dev/null; then
  echo "Flask is not installed. Install it with one of:"
  echo "  pip3 install flask"
  echo "  pip3 install -r \"$ROOT/requirements.txt\""
  echo "  python3 -m pip install flask"
  echo ""
  echo "If pip fails with SSL errors, fix your Python/SSL setup or use a virtualenv."
  exit 1
fi

PORT="${PORT:-5001}"
echo "Starting website at http://127.0.0.1:$PORT"
echo "Press Ctrl+C to stop the server."
echo ""

# Open browser after a short delay (gives server time to start)
(sleep 2 && open "http://127.0.0.1:$PORT" 2>/dev/null || true) &

export PORT

python3 app.py
