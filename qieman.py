from playwright.sync_api import sync_playwright
import json

def get_data_with_auto_headers():
    with sync_playwright() as p:
        # 启动 Chromium 浏览器
        browser = p.chromium.launch(headless=True) # 改为 False 可以看到浏览器操作
        context = browser.new_context()
        page = context.new_page()

        # 定义一个变量来存储捕获到的数据
        captured_data = {"headers": None, "json": None}

        # 监听所有的网络响应
        def handle_response(response):
            # 匹配目标 API 路径
            if "pmdj/v2/idx-eval/latest" in response.url:
                print(f"检测到目标请求: {response.url}")
                # 提取该请求发送时携带的 Headers
                captured_data["headers"] = response.request.headers
                # 直接获取响应内容
                captured_data["json"] = response.json()

        page.on("response", handle_response)

        # 访问首页触发请求
        page.goto("https://qieman.com/idx-eval", wait_until="networkidle")

        browser.close()
        return captured_data

if __name__ == "__main__":
    result = get_data_with_auto_headers()
    
    if result["headers"]:
        print("\n--- 自动化提取的关键 Header ---")
        print(f"x-sign: {result['headers'].get('x-sign')}")
        print(f"x-request-id: {result['headers'].get('x-request-id')}")
        
        print("\n--- 获取到的数据预览 ---")
        print(result["json"])
        with open('qieman.json', 'w') as f:
            json.dump(result['json'], f)
    else:
        print("未能捕获到目标请求，请检查 URL 是否正确。")
