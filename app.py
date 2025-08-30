# app.py  — eine einzige FastAPI-App (Agno) + statische UI
import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from agno.app.fastapi.app import FastAPIApp

from trainer_agent_with_tools import trainer  # dein vorhandener Agent

# Agent-ID setzen, damit wir ihn per ?agent_id=... adressieren können
trainer.agent_id = "sprachtrainer"

fastapi_app = FastAPIApp(
    agents=[trainer],
    name="Sprachtrainer",
    app_id="sprachtrainer_app",
    description="Agno FastAPI App für den Sprachtrainer",
)

# 👉 Das ist unsere EINZIGE FastAPI-App
app = fastapi_app.get_app()  # Prefix default: /v1

# Statische Dateien (UI)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    # Optional auch: fastapi_app.serve(app="app:app", port=3000, reload=True)
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=3000, reload=True)
