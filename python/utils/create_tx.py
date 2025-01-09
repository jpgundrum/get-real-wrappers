from utils.sdk import peaq_service_sdk
from web3 import Web3, Account
import requests
from eth_account.messages import encode_defunct


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

# TODO should did name be set by user or admin/gasStation??
DID_NAME="peaq"

# TODO THINK ABOUT
# How can the backend user know it is the DID call data they are signing? Could a malicious entity encode a transfer call data and take their funds?
def generate_eoa_data_hash(service_sdk, eoa, target, calldata, nonce):    
    message = service_sdk.generate_eoa_signature(eoa["machine_address"], target, calldata, nonce)
    return message
    

def register_did(service_sdk, eoa, did_signature):
    email_signature = service_sdk.generate_email_signature(eoa["email"], eoa["machine_address"], eoa["tag"])
    did_hash = service_sdk.create_did_hash(eoa["eoa_address"], did_signature, email_signature, eoa["machine_address"])
    did_calldata = service_sdk.create_did_calldata(DID_NAME, did_hash, eoa["machine_address"])
    return did_calldata

def store_data_service(service_sdk, eoa, quest_data):
    response = service_sdk.store_data_key(eoa["email"], quest_data["item_type"], eoa["tag"])
    storage_calldata = service_sdk.add_storage_calldata(quest_data["item_type"], quest_data["item"])
    return storage_calldata
    

def create_tx(eoa, signature, target, nonce, quest_data):
    service_sdk = peaq_service_sdk(
        AGUNG_RPC_URL,
        PEAQ_SERVICE_URL, 
        SERVICE_API_KEY, 
        PROJECT_API_KEY, 
        GAS_STATION_ADDRESS, 
        GAS_STATION_OWNER_PUBLIC_KEY, 
        GAS_STATION_OWNER_PRIVATE_KEY
    )
    
    if target == PRECOMPILE_ADDRESS_DID:
        calldata = register_did(service_sdk, eoa, signature)
        
    elif target == PRECOMPILE_ADDRESS_STORAGE:
        calldata = store_data_service(service_sdk, eoa, quest_data)
    else:
        raise TypeError("Target is not known")
    
    # first need to register did 
    message = generate_eoa_data_hash(service_sdk, eoa, target, calldata, nonce)
    
    return {"status": "success", "message": message, "calldata": calldata}
        
        # uvicorn python_server.event_listener:app --reload
