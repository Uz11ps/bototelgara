import requests
import json
import sys

TOKEN = "eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_qL03hAj8ycXK41y3q3EeFz_hM1o"
BOARD_ID = "uXjVGGNIgGQ="

def verify_miro():
    url = f"https://api.miro.com/v2/boards/{BOARD_ID}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Access successful!")
        else:
            print("❌ Access failed.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_miro()
