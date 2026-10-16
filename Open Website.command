#!/bin/bash
# Double-click this file to start the website and open it in your browser (Mac).

cd "$(dirname "$0")"

# Check for Flask
if ! python3 -c "import flask" 2>/dev/null; then
  echo "Installing Flask (one-time)..."
  python3 -m pip install --user flask 2>/dev/null || pip3 install --user flask 2>/dev/null || {
    echo "Please run in Terminal: pip3 install flask"
    echo "Then double-click this file again."
    read -p "Press Enter to close..."
    exit 1
  }
fi

echo "Starting website..."
python3 app.py &
SERVER_PID=$!
sleep 3
echo ""
echo ">>> OPEN IN BROWSER: http://127.0.0.1:5000 <<<"
echo "    (You MUST have :5000 in the address bar — not just 127.0.0.1)"
echo ""
open "http://127.0.0.1:5000/" 2>/dev/null || open "http://localhost:5000/"
echo "Website should open. If you see a BLANK page:"
echo "  -> Click the address bar and type:  http://127.0.0.1:5000"
echo "  -> Press Enter"
echo ""
echo "To STOP the server: close this window or press Ctrl+C"
echo ""
wait $SERVER_PID
