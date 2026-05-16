from fastapi import FastAPI

from crew.routes import auth as auth_routes
from crew.routes import invites as invite_routes
from crew.routes import workspaces as workspace_routes


app = FastAPI(title="crew")
app.include_router(auth_routes.router)
app.include_router(workspace_routes.router)
app.include_router(invite_routes.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
