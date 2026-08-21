import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import init_db
from services.scheduler import start_scheduler, stop_scheduler

from routers import stocks, funds, market, settings, wxwork, auth, admin

app = FastAPI(title="股票基金监控系统 API", version="1.0.0")

# Initialize database
init_db()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(stocks.router)
app.include_router(funds.router)
app.include_router(market.router)
app.include_router(settings.router)
app.include_router(wxwork.router)

# Mount static frontend (must be last)
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.exists(frontend_dist):
    # Serve SPA: catch-all fallback to index.html
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        # Don't catch API and WxWork routes
        if full_path.startswith("api/") or full_path.startswith("swx/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index_file = os.path.join(frontend_dist, "index.html")
        return FileResponse(index_file)
else:
    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "股票基金监控系统运行中，前端尚未构建。请运行 npm run build"}

from services.market_service import auto_fix_fund_names_in_db

@app.on_event("startup")
async def on_startup():
    print("="*50)
    print("  股票基金监控系统 启动完成")
    print("  访问地址: http://0.0.0.0:8888")
    print("  企业微信接收: http://<服务器IP>:8888/swx/receive")
    print("="*50)
    await auto_fix_fund_names_in_db()
    start_scheduler()

@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8888, reload=False)
