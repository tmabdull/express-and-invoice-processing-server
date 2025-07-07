from flask import Flask, request

app = Flask(__name__)

# This will store the full redirect URL for use in your OAuth flow
last_redirect_url = None

@app.route("/callback")
def oauth_callback():
    global last_redirect_url
    # Capture the full redirect URL (including ?code=...)
    last_redirect_url = request.url
    return (
        "<h2>Authorization received!</h2>"
        "<p>You can close this window and return to your terminal.</p>"
    )

def wait_for_callback():
    """
    Runs the Flask server and waits until a redirect is received.
    Returns the full redirect URL.
    """
    import threading
    import time

    # Start Flask server in a background thread
    server = threading.Thread(target=app.run, kwargs={"port": 8080})
    server.daemon = True
    server.start()

    print("Waiting for Google OAuth callback on http://localhost:8080/callback ...")
    while True:
        if last_redirect_url:
            return last_redirect_url
        time.sleep(1)
