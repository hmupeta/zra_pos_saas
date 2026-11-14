from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
momo_path = BACKEND_PATH / "payments" / "momo_service.py"

# Overwrite the file with perfectly formatted code
clean_code = '''
import requests
import uuid
import base64

class MTNMoMoService:
    """Handles MTN MoMo API interactions."""
    
    def __init__(self, config):
        self.config = config
        self.base_url = "https://sandbox.momodeveloper.mtn.com" if config.mtn_target_env == "sandbox" else "https://proxy.momoapi.mtn.com"
        self.subscription_key = config.mtn_subscription_key
        self.api_user = config.mtn_api_user
        self.api_key = config.mtn_api_key
        self.target_env = config.mtn_target_env

    def get_access_token(self):
        url = f"{self.base_url}/collection/token/"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Authorization": "Basic " + base64.b64encode(f"{self.api_user}:{self.api_key}".encode()).decode()
        }
        try:
            res = requests.post(url, headers=headers)
            res.raise_for_status()
            return {"success": True, "token": res.json().get("access_token")}
        except requests.exceptions.HTTPError as e:
            error_msg = e.response.text if e.response else str(e)
            return {"success": False, "error": f"MTN API Error: {error_msg}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def request_to_pay(self, phone, amount, external_id, payer_message="Payment"):
        token_result = self.get_access_token()
        if not token_result.get('success'): 
            return {"error": token_result.get('error')}

        token = token_result.get('token')
        reference_id = str(uuid.uuid4())
        url = f"{self.base_url}/collection/v1_0/requesttopay"
        
        # Format phone to standard MTN format (e.g., 260971234567)
        phone_clean = str(phone).replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = "260" + phone_clean[1:]

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": self.target_env,
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json"
        }
        payload = {
            "amount": str(amount),
            "currency": "ZMW",
            "externalId": external_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_clean
            },
            "payerMessage": payer_message,
            "payeeNote": payer_message
        }
        
        try:
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code in (200, 202):
                return {"success": True, "reference_id": reference_id}
            else:
                return {"error": res.text}
        except Exception as e:
            return {"error": str(e)}

    def check_status(self, reference_id):
        token_result = self.get_access_token()
        if not token_result.get('success'): 
            return {"error": "Auth failed"}
            
        token = token_result.get('token')
        url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": self.target_env,
            "Ocp-Apim-Subscription-Key": self.subscription_key
        }
        try:
            res = requests.get(url, headers=headers)
            return res.json()
        except Exception as e:
            return {"error": str(e)}
'''

momo_path.write_text(clean_code.strip() + "\n", encoding="utf-8")
print("✅ Rebuilt payments/momo_service.py with perfect syntax.")

print("\n🎉 Done! Run 'python manage.py runserver'")