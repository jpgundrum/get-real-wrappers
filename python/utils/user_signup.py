from utils.sdk import peaq_service_sdk
from web3 import Web3
import requests

import os

from dotenv import load_dotenv
load_dotenv()

# import env keys that will need to be sent to the sdk to perform operations
AGUNG_RPC_URL=os.getenv('AGUNG_RPC_URL')

PEAQ_SERVICE_URL=os.getenv('PEAQ_SERVICE_URL')
SERVICE_API_KEY=os.getenv('SERVICE_API_KEY')
PROJECT_API_KEY=os.getenv('PROJECT_API_KEY')

GAS_STATION_ADDRESS =os.getenv('GAS_STATION_ADDRESS')
GAS_STATION_OWNER_PUBLIC_KEY=os.getenv('GAS_STATION_OWNER_PUBLIC_KEY')
GAS_STATION_OWNER_PRIVATE_KEY=os.getenv('GAS_STATION_OWNER_PRIVATE_KEY')


PRECOMPILE_ADDRESS_DID='0x0000000000000000000000000000000000000800'
PRECOMPILE_ADDRESS_STORAGE='0x0000000000000000000000000000000000000801'

# represents a user email and their externally owned account.
USER_EMAIL='user_email@gmail.com'
TAG='TEST'
ITEM_TYPE='ITEM_TYPE'
ITEM='MY_ITEM'
EOA_PUBLIC_KEY=os.getenv('EOA_PUBLIC_KEY')
EOA_PRIVATE_KEY=os.getenv('EOA_PRIVATE_KEY')

DID_NAME="peaq"

def create_smart_account(service_sdk, eoa_event, nonce):
    eoa_address = Web3.to_checksum_address(eoa_event["eoa_address"])
    # Read peaq storage to see if a machine_address was returned; if not then there is none present so we can create one. 
    # This will reduce the amount of redundant machine address on-chain.
    # - if one is found read the the uri to get the resolved did machine document and verify that the
    # read_peaq_storage(eoa_address, eoa)
    
    # Perform this once per eoa... will need to link machine address to eoa address
    deploy_signature = service_sdk.generate_owner_deploy_signature(eoa_address, nonce)
    machine_address = service_sdk.deploy_machine_smart_account(eoa_address, nonce, deploy_signature)
    eoa_event["machine_address"] = machine_address
    return eoa_event

# Reward a user for using your app by the DID Creation event trigger.
# 
# 1. Received user registration event trigger.
# 2. User creates deployment signature & then creates a machine smart account after verification.
def user_signup(eoa_event, nonce):
    service_sdk = peaq_service_sdk(
        AGUNG_RPC_URL,
        PEAQ_SERVICE_URL, 
        SERVICE_API_KEY, 
        PROJECT_API_KEY, 
        GAS_STATION_ADDRESS, 
        GAS_STATION_OWNER_PUBLIC_KEY, 
        GAS_STATION_OWNER_PRIVATE_KEY
    )
    
    eoa = create_smart_account(service_sdk, eoa_event, nonce)
    message = service_sdk.create_id_to_sign(eoa["machine_address"])
    
    return {"status": "success", "message": message}
    
