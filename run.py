#!/usr/bin/env python
"""BrianRAG — Enterprise Knowledge Engine"""
import sys, os, webbrowser, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    host = os.getenv("BRIAN_HOST", "0.0.0.0")
    port = int(os.getenv("BRIAN_PORT", "8000"))
    url = f"http://localhost:{port}"

    print(f"""
  ╔══════════════════════════════════════════╗
  ║           BrianRAG v1.0.0                ║
  ║     Enterprise Knowledge Engine          ║
  ╠══════════════════════════════════════════╣
  ║  Local  : {url:<30} ║
  ║  API    : {url}/api/health{'':<22} ║
  ║  Ctrl+C : stop                          ║
  ╚══════════════════════════════════════════╝
""")

    def _open():
        time.sleep(1.5)
        try: webbrowser.open(url)
        except: pass
    threading.Thread(target=_open, daemon=True).start()

    import uvicorn
    from api.main import app
    uvicorn.run(app, host=host, port=port, log_level="warning")
