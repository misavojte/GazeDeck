"""Simple HTML GUI for GazeDeck using pywebview"""

import webview
import os
from pathlib import Path


def get_html_content():
    """Return the HTML content for the GUI window"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GazeDeck Control Panel</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }
            
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 40px;
                text-align: center;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            h1 {
                margin: 0 0 20px 0;
                font-size: 2.5em;
                font-weight: 300;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            }
            
            .subtitle {
                font-size: 1.2em;
                opacity: 0.8;
                margin-bottom: 30px;
            }
            
            .status {
                background: rgba(255, 255, 255, 0.2);
                padding: 15px 25px;
                border-radius: 25px;
                display: inline-block;
                font-size: 1.1em;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>GazeDeck</h1>
            <div class="subtitle">Plane-relative gaze bridge control panel</div>
            <div class="status">Ready to configure</div>
        </div>
    </body>
    </html>
    """


def create_gui():
    """Create and show the GUI window"""
    html_content = get_html_content()
    
    # Create the webview window
    webview.create_window(
        title="GazeDeck Control Panel",
        html=html_content,
        width=800,
        height=600,
        min_size=(600, 400),
        resizable=True,
        shadow=True,
        on_top=False
    )
    
    # Start the webview
    webview.start(debug=False)


if __name__ == "__main__":
    create_gui()
