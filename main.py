from typing import Any
from fastapi import FastAPI
from playwright.async_api import async_playwright
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局缓存
cache: dict[str, Any] = {"qieman_data": None, "last_updated": None}

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 启动时立即获取一次数据
    logger.info("应用启动，开始首次数据获取...")
    try:
        initial_data = await fetch_qieman_data()
        if initial_data:
            cache["qieman_data"] = initial_data
            logger.info("首次数据获取成功")
    except Exception as e:
        logger.error(f"首次数据获取失败: {e}")
    
    # 启动后台更新任务
    task = asyncio.create_task(update_data_loop())
    yield
    # 关闭时取消后台任务
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请改为具体域名，如 ["https://yourdomain.com"]
    allow_methods=["GET"],
    allow_headers=["*"],
)

async def fetch_qieman_data():
    result = {"data": None}
    
    async with async_playwright() as p:
        browser = None
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            async def handle_response(response):
                if "pmdj/v2/idx-eval/latest" in response.url:
                    try:
                        result["data"] = await response.json()
                    except Exception as e:
                        logger.error(f"解析响应失败: {e}")

            page.on("response", handle_response)
            
            await page.goto("https://qieman.com/idx-eval", wait_until="networkidle")
            # 给一点时间确保响应被捕获
            await asyncio.sleep(1)
            
        finally:
            if browser:
                await browser.close()
                
    return result["data"]

async def update_data_loop():
    """后台循环任务，每小时更新一次数据"""
    while True:
        try:
            logger.info("正在后台更新数据...")
            new_data = await fetch_qieman_data()
            if new_data:
                cache["qieman_data"] = new_data
                cache["last_updated"] = asyncio.get_event_loop().time()
                logger.info("数据更新成功！")
            else:
                logger.warning("获取到的数据为空")
        except Exception as e:
            logger.error(f"更新失败: {e}")
        
        await asyncio.sleep(36000)

@app.get("/api/slides")
async def get_slides():
    if cache["qieman_data"] is None:
        return {
            "error": "数据准备中，请稍后再试",
            "status": "loading"
        }
    
    return {
        "data": cache["qieman_data"],
        "last_updated": cache["last_updated"],
        "status": "ok"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "has_data": cache["qieman_data"] is not None,
        "last_updated": cache["last_updated"]
    }
