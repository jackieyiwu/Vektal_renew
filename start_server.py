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
        log(f"📸 截图已保存: {name}.png")
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
        # 启动浏览器 (无代理模式)
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled', '--no-sandbox'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        if RAW_COOKIE:
            context.add_cookies(parse_cookies(RAW_COOKIE))
            log("🍪 Cookie 已注入")

        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            page.goto(SERVER_URL)
            page.wait_for_load_state("networkidle")

            # 1. 登录处理
            if page.locator("input[type='password']").is_visible():
                log("⚠️ 需登录，输入账号密码...")
                page.locator("input[name='user']").first.fill(PANEL_USER)
                page.locator("input[type='password']").fill(PANEL_PASS)
                page.locator("button[type='submit']").click()
                page.wait_for_url("**/server/**")

            # 2. 点击启动按钮
            start_btn = page.locator("button[data-action='start'], button[aria-label='Start']").first
            if start_btn.is_visible():
                start_btn.click()
                log("▶️ 已触发启动")

                # 3. 处理广告
                try:
                    watch_ad = page.locator("button:has-text('Watch Ad')").first
                    if watch_ad.is_visible():
                        watch_ad.click()
                        log("📺 正在播放广告...")
                        page.wait_for_selector("text=/Auto Stop:/i", timeout=60000)
                except:
                    log("⏩ 未检测到广告或无需观看")

            # 4. 状态校验
            time.sleep(5)
            countdown = page.locator("text=/Auto Stop:/i").first.inner_text()
            log(f"🔎 状态捕获: {countdown}")

            if "Offline" in countdown:
                raise Exception("服务器仍为 Offline")

            save_screenshot(page, "success")
            send_telegram("🟢 成功唤醒", countdown)

        except Exception as e:
            log(f"❌ 异常: {e}")
            save_screenshot(page, "failed")
            send_telegram("🚨 唤醒失败", str(e))
        finally:
            browser.close()

if __name__ == "__main__":
    run_server_starter()
