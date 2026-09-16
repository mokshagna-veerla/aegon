"""AEGON – Secure Digital Evidence Management Platform
Flask entry point.
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Ensure vault and key directories exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "vault", "encrypted"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "keys"), exist_ok=True)

    app.run(debug=True, host="127.0.0.1", port=5000)
