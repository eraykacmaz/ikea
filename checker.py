import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def get_current_status():
    url = "https://www.ikea.com.tr/_ws/general.aspx/CheckStoreStocks"
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    payload = {"sprCode": "00330982"}
    
    try:
        start_time = datetime.now()
        response = requests.post(url, json=payload, headers=headers)
        response_time = (datetime.now() - start_time).total_seconds()
        response.raise_for_status()
        
        data = response.json()
        found = False
        
        for store in data['d']['Data']['StatusList']:
            if store['StoreCode'] == "253":
                result = {
                    'status': store['Status'],
                    'stock_text': store['StockText'],
                    'store_title': store['StoreTitle']
                }
                found = True
                break
        
        if not found:
            raise ValueError("Store 253 not found in response")
            
        return {
            'result': result,
            'response_time': f"{response_time:.2f}s",
            'http_status': response.status_code
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'http_status': getattr(response, 'status_code', None),
            'response_time': f"{response_time:.2f}s" if 'response_time' in locals() else 'N/A'
        }

def send_telegram(message):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def check_status():
    check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_report = f"🕒 Check initiated at {check_time}\n"
    
    # Get current status
    api_result = get_current_status()
    
    if 'error' in api_result:
        status_report += (
            "\n❌ <b>API Check Failed</b>\n"
            f"⏱ Response Time: {api_result['response_time']}\n"
            f"📡 HTTP Status: {api_result['http_status'] or 'N/A'}\n"
            f"📛 Error: {api_result['error']}"
        )
        send_telegram(status_report)
        return

    current = api_result['result']
    status_report += (
        "\n✅ <b>API Check Successful</b>\n"
        f"⏱ Response Time: {api_result['response_time']}\n"
        f"📡 HTTP Status: {api_result['http_status']}\n"
        f"\n🏪 Store: {current['store_title']}\n"
        f"📦 Current Status: {current['stock_text']} (Code: {current['status']})"
    )

    # Check previous status
    script_dir = os.path.dirname(os.path.realpath(__file__))
    last_status_path = os.path.join(script_dir, 'last_status.json')
    
    try:
        if os.path.exists(last_status_path) and os.path.getsize(last_status_path) > 0:
            with open(last_status_path, 'r') as f:
                last = json.load(f)
            status_changed = (last.get('status') != current.get('status'))
            status_report += f"\n🔄 Status Changed: {'Yes ✅' if status_changed else 'No ⏸️'}"
        else:
            status_report += "\n🆕 First run - no previous status to compare"
            status_changed = False
            
    except (json.JSONDecodeError, IOError) as e:
        status_report += f"\n⚠️ History Error: {str(e)}"
        status_changed = False

    # Send final report
    send_telegram(status_report)
    
    # Save current status
    try:
        with open(last_status_path, 'w') as f:
            json.dump(current, f, indent=2)
    except IOError as e:
        error_msg = f"\n⚠️ Save Error: Failed to update status history: {str(e)}"
        send_telegram(status_report + error_msg)

if __name__ == "__main__":
    check_status()