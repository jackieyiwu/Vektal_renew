from playwright.sync_api import sync_playwright
import requests
import time
import os

# ================= 配置区 =================
SERVER_URL = "https://panel.vektalnodes.in/server/602306ee-8b39-4c02-a5fc-ee984940c43b"
PANEL_USER = os.environ.get('PANEL_USER')
PANEL_PASS = os.environ.get('PANEL_PASS')
RAW_COOKIE = os.environ.get('PANEL_COOKIE', '')
TG_TOKEN = os.environ.get('TG_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def save_screenshot(page, name):
    try:
        os.makedirs("screenshots", exist_ok=True)
        page.screenshot(path=f"screenshots/{name}.png")
        log(f"📸 现场已记录: {name}.png")
    except Exception as e:
        log(f"⚠️ 截图失败: {e}")

def send_telegram(title, summary):
    if not TG_TOKEN or not TG_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    text = f"🤖 <b>{title}</b>\n\n{summary}\n\n🕒 <i>{time.strftime('%Y-%m-%d %H:%M:%S')}</i>"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except: pass

def parse_cookies(cookie_string):
    cookies = []
    if not cookie_string: return cookies
    for item in cookie_string.split(';'):
        if '=' in item:
            k, v = item.strip().split('=', 1)
            cookies.append({"name": k, "value": v, "domain": "panel.vektalnodes.in", "path": "/"})
    return cookies

def run_server_starter():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled', '--no-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        if RAW_COOKIE:
            context.add_cookies(parse_cookies(RAW_COOKIE))
            log("🍪 Cookie 已注入")

        page = context.new_page()
        page.set_default_timeout(45000)

        try:
            log(f"🔗 正在访问: {SERVER_URL}")
            page.goto(SERVER_URL)
            page.wait_for_load_state("networkidle")

            log(f"📍 当前 URL: {page.url}")
            log(f"📍 当前标题: {page.title()}")

            # 1. 登录逻辑
            if "login" in page.url or page.locator("input[type='password']").is_visible():
                log("⚠️ 检测到需要登录，正在输入凭据...")
                page.locator("input[name='user']").first.fill(PANEL_USER or "")
                page.locator("input[type='password']").fill(PANEL_PASS or "")
                page.locator("button[type='submit']").click()
                page.wait_for_load_state("networkidle")
                log(f"📍 登录后跳转到: {page.url}")

            # 2. 启动服务器
            start_btn = page.locator("button[data-action='start'], button[aria-label='Start']").first
            if start_btn.is_visible():
                start_btn.click()
                log("▶️ 已点击启动按钮")

                # 等待广告或状态变更
                time.sleep(10)
            else:
                log("⚠️ 未找到启动按钮，可能服务器已经在运行或 Cookie 失效。")
                log(f"页面快照(前500字符): {page.content()[:500]}")

            # 3. 校验状态
            countdown = page.locator("text=/Auto Stop:/i").first.inner_text()
            log(f"🔎 状态捕获: {countdown}")
            send_telegram("🟢 运行反馈", f"状态: {countdown}")

        except Exception as e:
            error_msg = str(e)
            log(f"❌ 运行异常: {error_msg}")
            save_screenshot(page, "error_debug")
            send_telegram("🚨 唤醒失败", f"异常: {error_msg[:100]}\nURL: {page.url}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_server_starter()
