# File Name: oci_ampere_hunter.py
import oci
import time
import json
import os
import requests
from dotenv import load_dotenv # 추가
from tracker_exe import log_app_usage


# 1. Get the absolute path of the directory containing this script
# This ensures it works regardless of where you run it from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 3. Use absolute path for the key file to avoid "FileNotFoundError"
KEY_FILE_PATH = os.path.join(BASE_DIR, "oci_private_key.pem")

# 2. Add the parent directory (AI_profit_hunter) to sys.path
# This allows 'import tracker_exe' to work even if the script is in 'src/'.
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

# Check if the key file exists before initializing the client
if not os.path.exists(KEY_FILE_PATH):
    print(f"❌ Error: Key file not found at {KEY_FILE_PATH}")
    exit(1)

# --- OCI Configuration ---
config = {
    "user": "ocid1.user.oc1..aaaaaaaauullmvotspnykrv5la4b2pqzaea4b37cxcy7jr57v6uz2g5r74pa",
    "key_file": KEY_FILE_PATH, # Now using the absolute path
    "fingerprint": "ce:b0:11:1a:f3:12:76:ca:de:17:35:35:f6:a3:8a:6b",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaaz44gcwihvfpgevc7btgw6gy63qcvihww5scvqfo3nd7uylvtwmna",
    "region": "us-phoenix-1"
}

# config = {
#     "user": "ocid1.user.oc1..aaaaaaaauullmvotspnykrv5la4b2pqzaea4b37cxcy7jr57v6uz2g5r74pa",
#     "key_file": os.path.join(BASE_DIR, "oci_private_key.pem"), # Path to your API private key
#     "fingerprint": "ce:b0:11:1a:f3:12:76:ca:de:17:35:35:f6:a3:8a:6b", # Your API key fingerprint
#     "tenancy": "ocid1.tenancy.oc1..aaaaaaaaz44gcwihvfpgevc7btgw6gy63qcvihww5scvqfo3nd7uylvtwmna", # Your Tenancy OCID
#     "region": "us-phoenix-1"
# }

# --- Telegram Settings ---
# Ensure these environment variables are set in your shell
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

# --- Resource OCIDs (Replace with the IDs you found) ---
COMPARTMENT_ID = "ocid1.tenancy.oc1..aaaaaaaaz44gcwihvfpgevc7btgw6gy63qcvihww5scvqfo3nd7uylvtwmna"
SUBNET_ID = "ocid1.subnet.oc1.phx.aaaaaaaa4mkbwqc4y7sd5d54a7kdvdkoizqcikdz7pq5c4dluhcg3erznghq"
IMAGE_ID = "ocid1.image.oc1.phx.aaaaaaaa6m3airkzbr4zy6t3paptakqvluxgsqmgw45li3jfzwcbog2ginva" # The ID we found yesterday
AD_NAME = "HrRu:PHX-AD-2" # Your Availability Domain

compute_client = oci.core.ComputeClient(config)

def send_telegram_msg(message):
    """Sends a notification message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def attempt_provisioning():
    instance_details = oci.core.models.LaunchInstanceDetails(
        display_name="Ampere_Always_Free",
        compartment_id=COMPARTMENT_ID,
        availability_domain=AD_NAME,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(ocpus=4, memory_in_gbs=24),
        source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=IMAGE_ID),
        create_vnic_details=oci.core.models.CreateVnicDetails(subnet_id=SUBNET_ID, assign_public_ip=True)
    )

    try:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Attempting to create instance...")
        response = compute_client.launch_instance(instance_details)
        
        # Success logging
        log_app_usage("oci_hunter", "provision_success", details={"status": "success", "instance_id": response.data.id})
        print("Success! Instance is being provisioned.")

        msg = "🎯 찾기 성공 OCI Ampere Instance!"
        send_telegram_msg(msg)

        return True
    except oci.exceptions.ServiceError as e:
        # Failure logging
        details = {"error_code": e.code, "message": e.message}
        log_app_usage("oci_hunter", "provision_retry", details=details)
        print(f"Retry: {e.message}")
        return False

if __name__ == "__main__":
    log_app_usage("oci_hunter", "app_opened") # Track app start
    while not attempt_provisioning():
        time.sleep(60) # Wait for 1 minute before next attempt