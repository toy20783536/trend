from flask import Flask
from trend_scanner import run_all_filters
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Flask 首頁啟動成功（Render 部署版）"

@app.route("/run")
def run():
    try:
        print("🚀 正在執行 run_all_filters()...")
        result = run_all_filters()
        return result or "⚠️ 沒有回傳內容"
    except Exception as e:
        print(f"❌ 執行錯誤：{e}")
        return f"❌ 執行錯誤：{e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
