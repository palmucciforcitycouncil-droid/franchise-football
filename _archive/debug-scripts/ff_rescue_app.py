from fastapi import FastAPI
from fastapi.responses import HTMLResponse
app = FastAPI(title="FF Rescue")
@app.get("/", response_class=HTMLResponse)
def home():
    return "<h2>Rescue Server</h2><p>If you can see this, port 8000 is fine. Next we point uvicorn at your real app module.</p><ul><li><a href='/roster'>/roster</a></li></ul>"
@app.get("/roster", response_class=HTMLResponse)
def roster():
    rows=[("Alex Carter","QB",74),("Miles Stone","RB",71),("Jay Banks","WR",73),("D. Clark","TE",69),("K. Hale","K",68)]
    body="".join(f"<tr><td style='padding:6px;border-bottom:1px solid #ddd'>{n}</td><td>{p}</td><td style='text-align:center'>{o}</td></tr>" for n,p,o in rows)
    return f"<h3>Roster (Rescue)</h3><table border='1' cellspacing='0' cellpadding='4'><tr><th>Name</th><th>Pos</th><th>OVR</th></tr>{body}</table>"
