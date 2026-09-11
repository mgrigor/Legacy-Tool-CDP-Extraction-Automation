"""
extract_payload.py

Attaches to a running Chrome instance via the Chrome DevTools Protocol (CDP)
and passively listens for the internal network request a legacy reporting
tool fires when it generates a report. The legacy tool has no public API,
so this captures the request shape (payload) and the session's auth token
directly from the browser's own network traffic -- enabling the requests
to be replayed programmatically instead of clicked through the UI by hand.

Usage:
    1. Launch Chrome with remote debugging enabled, e.g.:
       chrome --remote-debugging-port=9222 --remote-allow-origins=*
    2. Log into the legacy tool in that Chrome window as you normally would.
    3. Run this script, then trigger one "generate report" action in the UI.
    4. The script saves payload.json (request body) and token.txt (auth
       header) to the current directory, then keeps listening for more.
"""

import json
import requests
import websocket
import threading

CDP_URL = "http://localhost:9222"

# Substrings identifying the internal "generate report" endpoint.
# Replace with whatever uniquely identifies your target tool's request.
TARGET_TAB_HOSTNAME = "your-legacy-tool.internal"
TARGET_PATH_MARKERS = ("/report/", "generate")


def is_target_request(url: str) -> bool:
    u = url.lower()
    return all(marker in u for marker in TARGET_PATH_MARKERS)


def connect_to_cdp():
    """Find the browser tab pointed at the legacy tool and open a CDP
    WebSocket connection to it."""
    resp = requests.get(f"{CDP_URL}/json")
    targets = resp.json()

    ws_url = None
    for t in targets:
        url = t.get("url", "").lower()
        if TARGET_TAB_HOSTNAME in url:
            ws_url = t["webSocketDebuggerUrl"]
            print(f"Attached to target tab: {t['url']}")
            break

    if not ws_url:
        raise Exception("Could not find the target tool's tab in CDP targets")

    return websocket.create_connection(ws_url)


def on_message(ws, message):
    try:
        msg = json.loads(message)

        if msg.get("method") != "Network.requestWillBeSent":
            return

        request = msg["params"]["request"]
        url = request["url"]

        if is_target_request(url):
            print("\n=== Captured target request! ===")
            print(f"URL: {url}")

            # Save the POST body -- this becomes the reusable payload template.
            post_data = request.get("postData", "")
            with open("payload.json", "w") as f:
                try:
                    f.write(json.dumps(json.loads(post_data), indent=2))
                except Exception:
                    f.write(post_data)
            print("Saved payload.json")

            # Save the session's Authorization header for reuse.
            headers = request.get("headers", {})
            token = headers.get("Authorization", "")
            with open("token.txt", "w") as f:
                f.write(token)
            print("Saved token.txt")
            print("====================================\n")

    except Exception as e:
        print("Error processing message:", e)


def listen(ws):
    while True:
        msg = ws.recv()
        on_message(ws, msg)


def main():
    print("Connecting to Chrome via CDP...")
    ws = connect_to_cdp()
    print("Listening for target requests...")

    ws.send(json.dumps({"id": 1, "method": "Network.enable"}))

    thread = threading.Thread(target=listen, args=(ws,))
    thread.daemon = True
    thread.start()

    while True:
        pass


if __name__ == "__main__":
    main()
