import oci
import time
import os
import sys
import requests
from dotenv import load_dotenv

# 트래커 임포트를 위해 src 폴더도 인식하게 만듭니다.
sys.path.append("/home/ubuntu/AI_profit_hunter/src")
from tracker_exe import log_app_usage 

load_dotenv()

# 아까 1716바이트로 존재를 확인했던 그 진짜 파일 경로!
KEY_FILE_PATH = "/home/ubuntu/AI_profit_hunter/src/oci_private_key.pem"

# 실행 전 파일이 진짜로 있는지 파이썬이 먼저 검사합니다.
if not os.path.exists(KEY_FILE_PATH):
    print(f"❌ [치명적 에러] 파이썬이 키 파일을 읽지 못합니다: {KEY_FILE_PATH}")
    exit(1)

config = {
    "user": "ocid1.user.oc1..aaaaaaaauullmvotspnykrv5la4b2pqzaea4b37cxcy7jr57v6uz2g5r74pa",
    "key_file": KEY_FILE_PATH,
    "fingerprint": "ce:b0:11:1a:f3:12:76:ca:de:17:35:35:f6:a3:8a:6b",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaaz44gcwihvfpgevc7btgw6gy63qcvihww5scvqfo3nd7uylvtwmna",
    "region": "us-phoenix-1"
}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("CHAT_ID")

COMPARTMENT_ID = "ocid1.tenancy.oc1..aaaaaaaaz44gcwihvfpgevc7btgw6gy63qcvihww5scvqfo3nd7uylvtwmna"
SUBNET_ID = "ocid1.subnet.oc1.phx.aaaaaaaa4mkbwqc4y7sd5d54a7kdvdkoizqcikdz7pq5c4dluhcg3erznghq"
IMAGE_ID = "ocid1.image.oc1.phx.aaaaaaaa6m3airkzbr4zy6t3paptakqvluxgsqmgw45li3jfzwcbog2ginva"
AD_NAME = "HrRu:PHX-AD-2"

compute_client = oci.core.ComputeClient(config)

def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message})

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
        
        instance_id = response.data.id
        log_app_usage("oci_hunter", "provision_success", details={"status": "success", "instance_id": instance_id})
        
        send_telegram_msg("🎯 찾기 성공 OCI Ampere Instance!")
        
        return True
    except oci.exceptions.ServiceError as e:
        log_app_usage("oci_hunter", "provision_retry", details={"error_code": e.code, "message": e.message})
        print(f"Retry: {e.message}")
        
        return False

if __name__ == "__main__":
    log_app_usage("oci_hunter", "app_opened")
    try:
        # 무한 반복 생성 요청 (자리가 날 때까지)
        while not attempt_provisioning():
            time.sleep(60) 
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")