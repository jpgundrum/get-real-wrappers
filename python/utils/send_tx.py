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

    

def generate_owner_signature(service_sdk, eoa, target, nonce):
    owner_signature = service_sdk.generate_owner_signature(eoa["eoa_address"], target, eoa["calldata"], nonce)
    return owner_signature

def send_tx(eoa, eoa_signature, target, nonce):
    service_sdk = peaq_service_sdk(
        AGUNG_RPC_URL,
        PEAQ_SERVICE_URL, 
        SERVICE_API_KEY, 
        PROJECT_API_KEY, 
        GAS_STATION_ADDRESS, 
        GAS_STATION_OWNER_PUBLIC_KEY, 
        GAS_STATION_OWNER_PRIVATE_KEY
    )
    
    # first need to register did 
    owner_signature = generate_owner_signature(service_sdk, eoa, target, nonce)
    
    receipt = service_sdk.execute_funded_transaction(
        eoa["eoa_address"],
        eoa["machine_address"],
        target,
        eoa["calldata"],
        nonce,
        owner_signature,
        eoa_signature
    )
    
    # Check the status of the transaction
    if receipt.get("status") == 1:
        return {"status": "success", "message": "Transaction executed successfully", "receipt": receipt}
    else:
        return {"status": "failure", "message": "Transaction failed", "receipt": receipt}
