import os
import sdk
from dotenv import load_dotenv
load_dotenv()

from web3 import Web3
from eth_abi import encode, decode

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

def get_eoa():
    w3 = Web3(Web3.HTTPProvider(AGUNG_RPC_URL))
    return w3.eth.account.from_key(EOA_PRIVATE_KEY)


def main():
    # After each transaction on the GasStation Smart contract the nonce must be different. Simply can increase by 1 each time.
    nonce = 1
    
    # The following creates a DID and stores it on chain funded by the Gas Station
    test = sdk.Sdk(AGUNG_RPC_URL, PEAQ_SERVICE_URL, SERVICE_API_KEY, PROJECT_API_KEY, GAS_STATION_ADDRESS, GAS_STATION_OWNER_PUBLIC_KEY, GAS_STATION_OWNER_PRIVATE_KEY)
    
    # Perform this once per eoa... will need to link machine address to eoa address
    deploy_signature = test.generate_owner_deploy_signature(EOA_PUBLIC_KEY, nonce)
    machine_address = test.deploy_machine_smart_account(EOA_PUBLIC_KEY, nonce, deploy_signature)
    nonce += 1
    
    email_signature = test.generate_email_signature(USER_EMAIL, machine_address, TAG)
    did_hash = test.create_did_hash(email_signature, machine_address)
    did_calldata = test.create_did_calldata(DID_NAME, did_hash, machine_address)
    eoa_account = get_eoa()
    eoa_signature = test.generate_eoa_signature(eoa_account, machine_address, PRECOMPILE_ADDRESS_DID, did_calldata, nonce)
    owner_signature = test.generate_owner_signature(EOA_PUBLIC_KEY, PRECOMPILE_ADDRESS_DID, did_calldata, nonce)
    
    receipt = test.execute_funded_transaction(
        EOA_PUBLIC_KEY,
        machine_address,
        PRECOMPILE_ADDRESS_DID,
        did_calldata,
        nonce,
        owner_signature,
        eoa_signature
    )
    nonce += 1
    
    # # The following completes the flow for data storage using get-real service
    response = test.store_data_key(USER_EMAIL, ITEM_TYPE, TAG)
    storage_calldata = test.add_storage_calldata(ITEM_TYPE, ITEM)
    eoa_account = get_eoa()
    eoa_signature = test.generate_eoa_signature(eoa_account, machine_address, PRECOMPILE_ADDRESS_STORAGE, storage_calldata, nonce)
    owner_signature = test.generate_owner_signature(EOA_PUBLIC_KEY, PRECOMPILE_ADDRESS_STORAGE, storage_calldata, nonce)
    receipt = test.execute_funded_transaction(
        EOA_PUBLIC_KEY,
        machine_address,
        PRECOMPILE_ADDRESS_STORAGE,
        storage_calldata,
        nonce,
        owner_signature,
        eoa_signature
    )
    nonce += 1
    print("Next nonce to use: ", nonce)
    
    
    # # verify DATA
    # # WIP
    # # It only returns true if it has been verified and that it has not been claimed. Then it will go to false after it has been claimed. Storage not appearing to work.
    # result = test.verify_did(USER_EMAIL, TAG)
    # print(result)
    # result = test.verify_storage(USER_EMAIL, TAG)
    # print(result)
    # result = test.verify_storage_count(USER_EMAIL, 1, TAG)
    # print(result)
    
    
main()