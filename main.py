from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import delivery, points, rectification, resident, user

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="垃圾分类督导积分 API 服务",
    description="垃圾分类督导积分管理系统，支持扫码登记、分类判定、积分流水、整改通知、申诉处理等功能",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(delivery.router)
app.include_router(points.router)
app.include_router(rectification.router)
app.include_router(resident.router)


@app.get("/", summary="健康检查")
async def root():
    return {
        "code": 200,
        "message": "垃圾分类督导积分 API 服务运行中",
        "data": {
            "service": "garbage-sorting-points-api",
            "version": "1.0.0",
            "docs": "/docs",
        },
    }


@app.get("/health", summary="健康检查")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
