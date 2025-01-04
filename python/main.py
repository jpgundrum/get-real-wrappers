import os
import json
from sdk import peaq_service_sdk
import h160_to_ss58
import get_attribute

from did_serialization import peaq_py_proto

from eth_account.messages import encode_defunct

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

# If each user on your app owns a machine   



off_chain_storage = {EOA_PUBLIC_KEY: "did:peaq:0xe18c79cF1e6C2AB5f955086b78d7cEeECB1F04e0/peaq"}

def verify_mapping(resolveable_did, eoa):
    # Split the string into parts
    parts = resolveable_did.split("/")
    address = parts[0].split(":")[-1]
    name = parts[1]
    print(address)
    print(name)
    
    # This below code does work if you want to convert h160 to ss58.
    # substrate_wallet = h160_to_ss58.evm_to_address(address)
    # print(substrate_wallet)
    # get_attribute.create_storage_keys(substrate_wallet, name)
    calldata = get_attribute.generate_read_attribute_calldata(address, name)

    # # Call the precompile
    result = eoa["provider"].eth.call({
        'to': PRECOMPILE_ADDRESS_DID,
        'data': calldata
    })
    #decoded_value = result[256:].decode("utf-8")  # Example argument, adjust as needed
    decoded_value = result[256:].rstrip(b'\x00').decode("utf-8")
    
    byte_data = bytes.fromhex(decoded_value)
    deserialized_doc = peaq_py_proto.Document()
    deserialized_doc.ParseFromString(byte_data)

    # Print the deserialized document
    print("Deserialized Document:\n", deserialized_doc)

    # Extract message that was signed and convert to bytes
    id = deserialized_doc.id
    message = id.encode('utf-8')
    hash = encode_defunct(message)
    
    # Get the signature
    signature = deserialized_doc.signature.hash
    # Obtain the address that created the signature
    recovered_address = eoa["provider"].eth.account.recover_message(hash, signature=signature)

    # Verify signature is the same as found in the issuer field of the signature
    issuer = deserialized_doc.signature.issuer
    if recovered_address == issuer:
        print("Signature is valid!")
    else:
        print("Signature is invalid.")
    
    

# The format of the machine_address can be used to resolve a did document to verify if the eoa_address did in fact create the signature 
# in the machine_address's did document
def store_off_chain(eoa_address, machine_address):
    off_chain_storage[eoa_address] = f"did:peaq:${machine_address}/${DID_NAME}"
    

# Read off-chain mappping solution to see if a eoa_account already has a machine_address
def read_peaq_storage(eoa_address, eoa):
    if eoa_address in off_chain_storage:
        print("hi")
        verify_mapping(off_chain_storage[eoa_address], eoa)
        return


# User creates account with email. Check if a machine_address contract was linked already.
# Mocked data to show an example of what a user registration event could look like.
def new_eoa_event():
    w3 = Web3(Web3.HTTPProvider(AGUNG_RPC_URL))
    eoa_account = w3.eth.account.from_key(EOA_PRIVATE_KEY)
    eoa = {
        "provider": w3,
        "account": eoa_account,
        "email": USER_EMAIL,
        "tag": TAG
    }
    return eoa

# Create a smart account based on the external account wallet address that was triggered the action.
# Add machine_address to the eoa object that will be used when creating the DID Document for the user.
def create_smart_account(service_sdk, eoa, nonce):
    eoa_address = eoa["account"].address
    # Read peaq storage to see if a machine_address was returned; if not then there is none present so we can create one. 
    # This will reduce the amount of redundant machine address on-chain.
    # - if one is found read the the uri to get the resolved did machine document and verify that the
    read_peaq_storage(eoa_address, eoa)
    
    # # Perform this once per eoa... will need to link machine address to eoa address
    # deploy_signature = service_sdk.generate_owner_deploy_signature(eoa_address, nonce)
    # machine_address = service_sdk.deploy_machine_smart_account(eoa_address, nonce, deploy_signature)
    # eoa["machine_address"] = machine_address
    # return eoa

# Get-real service function calls to generate an email signature and did calldata to send that is funded.
# by the GasStationFactory contract. 
# - peaq storage will be used to map the eoa public key to the did uri of the machine address
# 
# TODO How to track what eoa_accounts own what machine_addresses? Do quests/tags define this? 
def register_did(service_sdk, eoa):
    email_signature = service_sdk.generate_email_signature(eoa["email"], eoa["machine_address"], eoa["tag"])
    did_hash = service_sdk.create_did_hash(eoa["account"], email_signature, eoa["machine_address"])
    did_calldata = service_sdk.create_did_calldata(DID_NAME, did_hash, eoa["machine_address"])
    return did_calldata

# Reward a user for using your app by the DID Creation event trigger.
# 
# 1. User registration event trigger.
# 2. User creates deployment signature & then creates a machine smart account after verification.
def user_signup(service_sdk, nonce):
    eoa = new_eoa_event()
    eoa = create_smart_account(service_sdk, eoa, nonce)
    return eoa

# Generates the eoa signature and owner signature that allows the machine to execute the transaction
def generate_signatures(service_sdk, eoa, did_calldata, nonce):
    eoa_signature = service_sdk.generate_eoa_signature(eoa["account"], eoa["machine_address"], PRECOMPILE_ADDRESS_DID, did_calldata, nonce)
    owner_signature = service_sdk.generate_owner_signature(EOA_PUBLIC_KEY, PRECOMPILE_ADDRESS_DID, did_calldata, nonce)
    return eoa_signature, owner_signature

# when a user completes quests data is generated on chain
def data_generated():
    pass

def main():
    # After each transaction on the GasStation Smart contract the nonce must be different. Simply can increase by 1 each time.
    nonce = 89
    
    # The following creates a DID and stores it on chain funded by the Gas Station
    
    # service_sdk contains so much private information... have to be very careful that it is never exposed
    service_sdk = peaq_service_sdk(
        AGUNG_RPC_URL,
        PEAQ_SERVICE_URL, 
        SERVICE_API_KEY, 
        PROJECT_API_KEY, 
        GAS_STATION_ADDRESS, 
        GAS_STATION_OWNER_PUBLIC_KEY, 
        GAS_STATION_OWNER_PRIVATE_KEY
    )
    
    
    # Just need to do one addAttribute() execution per eoa to be rewarded for signup.
    eoa = user_signup(service_sdk, nonce)
    # did_calldata = register_did(service_sdk, eoa)
    # nonce += 1
    # eoa_signature, owner_signature = generate_signatures(service_sdk, eoa, did_calldata, nonce)
    
    # # EACH ONE OF THESE COST 0.5 peaq from the gas station contract.
    # receipt = service_sdk.execute_funded_transaction(
    #     eoa["account"].address,
    #     eoa["machine_address"],
    #     PRECOMPILE_ADDRESS_DID,
    #     did_calldata,
    #     nonce,
    #     owner_signature,
    #     eoa_signature
    # )
    # # add machine_address to offchain storage after a successful transaction.
    # store_off_chain(eoa["account"].address, eoa["machine_address"])
    # nonce += 1
    # print("Set next nonce to be: ", nonce)
    
    
    
    
    
    # # user_signup executes 2 transactions on the smart contract
    # nonce+=2 

    
    # # # The following completes the flow for data storage using get-real service
    # response = service_sdk.store_data_key(USER_EMAIL, ITEM_TYPE, TAG)
    # storage_calldata = service_sdk.add_storage_calldata(ITEM_TYPE, ITEM)
    # eoa_account = get_eoa()
    # eoa_signature = service_sdk.generate_eoa_signature(eoa_account, machine_address, PRECOMPILE_ADDRESS_STORAGE, storage_calldata, nonce)
    # owner_signature = service_sdk.generate_owner_signature(EOA_PUBLIC_KEY, PRECOMPILE_ADDRESS_STORAGE, storage_calldata, nonce)
    # receipt = service_sdk.execute_funded_transaction(
    #     EOA_PUBLIC_KEY,
    #     machine_address,
    #     PRECOMPILE_ADDRESS_STORAGE,
    #     storage_calldata,
    #     nonce,
    #     owner_signature,
    #     eoa_signature
    # )
    # nonce += 1
    # print("Next nonce to use: ", nonce)
    
    # TODO How to bunch transactions efficiently?
    # IDEA: running in batches, on a schedule
    # 1. Listener looking to data store 
    
    
    # # verify DATA
    # # WIP
    # # Maybe not working because I am using 'TEST' and it is getting overloaded.
    # # 
    # # It only returns true if it has been verified and that it has not been claimed. Then it will go to false after it has been claimed. Storage not appearing to work.
    # result = service_sdk.verify_did(USER_EMAIL, TAG)
    # print(result)
    # result = service_sdk.verify_storage(USER_EMAIL, TAG)
    # print(result)
    # result = service_sdk.verify_storage_count(USER_EMAIL, 1, TAG)
    # print(result)
    
    
main()