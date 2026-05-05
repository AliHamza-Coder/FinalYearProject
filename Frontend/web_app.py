import eel
import main
import sys

# This script runs the Deceptron app in "Web Mode"
# Instead of a dedicated window, it runs as a local server
# and provides a link to open it in any web browser.

if __name__ == "__main__":
    port = 8000
    print("\n" + "="*60)
    print("🚀 DECEPTRON - WEB INTERFACE MODE")
    print("="*60)
    print(f"\n✅ Server is starting on port {port}")
    print(f"🔗 Click the link below to open the app in your browser:")
    print(f"\n    http://localhost:{port}/index.html")
    print("\n" + "="*60)
    print("Press Ctrl+C to stop the server\n")

    try:
        # mode=None prevents Eel from trying to open a browser window automatically.
        # block=False allows the script to continue so we can keep it alive manually.
        eel.start(
            'index.html', 
            mode=None, 
            port=port,
            block=False
        )
        
        # Keep the server alive
        while True:
            eel.sleep(1.0)
            
    except (SystemExit, KeyboardInterrupt):
        print("\n👋 Shutting down server...")
        sys.exit()
    except Exception as e:
        print(f"\n❌ Error: {e}")
