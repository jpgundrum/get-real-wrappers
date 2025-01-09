import json
import os
import logging
import requests

from did_serialization import peaq_py_proto

from web3 import Web3
from eth_abi.packed import encode_packed
from eth_utils import keccak, to_hex
from eth_account.messages import encode_defunct
from eth_abi import encode


# PRECOMPILE CONSTANTS
PRECOMPILE_ADDRESS_DID='0x0000000000000000000000000000000000000800'
PRECOMPILE_ADDRESS_STORAGE='0x0000000000000000000000000000000000000801'
ABI_GAS_STATION='gas_station_abi'

# Configure the logger to write to a file
logging.basicConfig(
    level=logging.DEBUG,
    filename='./python_server/logs/peaq_sdk.log',  # Log file name
    filemode='a',        # Append mode
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

# Create a logger for SDK
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logging.getLogger('web3').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('web3.manager.RequestManager').setLevel(logging.WARNING)
logging.getLogger('web3.providers.HTTPProvider').setLevel(logging.WARNING)

_abi_cache = {}

class peaq_service_sdk:
    def __init__(self, rpc_url, peaq_service_url, service_api_key, project_api_key, gas_station_address, gas_station_public, gas_station_private):
        """
        Initializes the SDK class, encapsulating GetRealService and GasStation functionalities.
        """
        # Set class vars
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.peaq_service_url = peaq_service_url
        self.service_api_key = service_api_key
        self.project_api_key = project_api_key
        self.gas_station_address = gas_station_address
        self.gas_station_public = gas_station_public
        
        # Create a wallet to perform transactions
        self.owner_account = self.w3.eth.account.from_key(gas_station_private)
        
        # Create an instance of the gas station contract to perform operation
        gas_station_abi = self._load_abi(ABI_GAS_STATION)
        self.gas_station = self.w3.eth.contract(
            address=self.gas_station_address,
            abi=gas_station_abi
        )
        
    def generate_owner_deploy_signature(self, eoa, nonce):
        """
        Generates an owner signature for deploying a Machine Smart Account.
        """
        packed = encode_packed(
            ['address', 'address', 'uint256'],
            [
                self.gas_station_address,
                eoa,
                nonce
            ]
        )

        message_hash = keccak(packed)
        message = encode_defunct(primitive=message_hash)
        owner_signature = self.owner_account.sign_message(message).signature.hex()
        logger.debug("Gas Station owner signature used during Machine Smart Account Deployment: {}".format(repr(owner_signature)))
        return owner_signature
    
    def deploy_machine_smart_account(self, eoa, nonce, signature):
        """
        Deploys a Machine Smart Account by calling the deployMachineSmartAccount() function.
        """
        deploy_tx = self.gas_station.functions.deployMachineSmartAccount(
            eoa,
            nonce,
            bytes.fromhex(signature)
        )

        receipt = self.send_transaction(deploy_tx)
        event_signature = keccak(text="MachineSmartAccountDeployed(address)").hex()
        
        for log in receipt["logs"]:
            if log["topics"][0].hex() == event_signature and len(log["topics"]) > 1:
                machine_address = Web3.to_checksum_address(log["topics"][1].hex()[24:])
                logger.debug("Contract Address of the deployed Machine Smart Account: {}".format(repr(machine_address)))
                return machine_address

        raise ValueError("MachineSmartAccountDeployed event not found in logs")
    
    def generate_email_signature(self, email, machine_address, tag):
        """
        Generates an email signature using the PEAQ service API for the get-real service
        """
        try:
            data = {
                "email": email,
                "did_address": machine_address,
                "tag": tag
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "APIKEY": self.service_api_key,
                "P-APIKEY": self.project_api_key
            }

            response = requests.post(f"{self.peaq_service_url}/v1/sign", json=data, headers=headers)
            response.raise_for_status()
            email_signature = response.json()["data"]["signature"]
            logger.debug("Data sent to service endpoint: ".format(repr(data)))
            logger.debug("Returned email signature for get-real service: ".format(repr(email_signature)))
            return email_signature

        except requests.exceptions.RequestException as e:
            print("Error creating email signature:", e)
            raise
        
    def store_data_key(self, email, item_type, tag):
        """
        Stores a data key using the PEAQ service API.
        """
        try:
            data = {
                "email": email,
                "item_type": item_type,
                "tag": tag
            }

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "APIKEY": self.service_api_key,
                "P-APIKEY": self.project_api_key
            }

            response = requests.post(f"{self.peaq_service_url}/v1/data/store", json=data, headers=headers)
            response.raise_for_status()
            logger.debug("Data sent to service endpoint: ".format(repr(data)))
            logger.debug("Returned response object after storing data key: ".format(repr(response.json())))

            return response.json()

        except requests.exceptions.RequestException as e:
            print("Error storing data key:", e)
            raise
        
        
    def create_id_to_sign(self, smart_accoout_address):
        doc = peaq_py_proto.Document()
        doc.id = f"did:peaq:{smart_accoout_address}"
        return doc.id
        
    def create_did_hash(self, eoa_address, did_signature, email_signature, machine_address):
        """
        Creates a DID hash from an email signature using protobuf serialization.
        """
        # print("test")
        doc = peaq_py_proto.Document()
        doc.id = f"did:peaq:{machine_address}"
        doc.controller = f"did:peaq:{machine_address}"

        service = doc.services.add()
        service.id = "#emailSignature"
        service.type = "emailSignature"
        service.data = email_signature
        
        # eoa account signs the id and stores in did doc to prove which can be used to prove ownership
        
        # request frontend for user to sign the message (id) by sending it's prehashed value
        # - this will tie ownership from eoa to the machine address
        # - frontend sends the signature to this backend to store in DID Document that can be verified (DePINs on peaq verify each other?)
        # id_signature = self._local_sign(eoa_account, doc.id) 

        signature = doc.signature
        signature.type = "ECDSA"
        signature.issuer = eoa_address
        signature.hash = did_signature

        serialized_data = doc.SerializeToString()
        # print(serialized_data)
        serialized_hex = serialized_data.hex()
        
        logger.debug("Serialized DID Hash created with value of: ".format(serialized_hex))
        deserialized_did = self._deserialize_did(serialized_data)
        logger.debug("Deserialized Document: \n{}".format(deserialized_did))
        return serialized_hex

    def create_did_calldata(self, name, did_hash, machine_address):
        """
        Creates a DID transaction using the precompile to be sent on-chain through the Gas Station.
        """
        did_function_signature = "addAttribute(address,bytes,bytes,uint32)"
        did_function_selector = self.w3.keccak(text=did_function_signature)[:4].hex()
        
        logger.debug("Name of DID being stored: {}".format(name))
        logger.debug("Address at which the DID is being stored: {}".format(machine_address))
        # convert to bytes
        name = name.encode("utf-8").hex()
        did_hash = did_hash.encode("utf-8").hex()
        encoded_params = encode(
            ['address', 'bytes', 'bytes', 'uint32'],
            [machine_address, bytes.fromhex(name), bytes.fromhex(did_hash), 0]
        ).hex()
        
        calldata = did_function_selector + encoded_params
        logger.debug("Create DID calldata: {}".format(calldata))
        return calldata
    
    def add_storage_calldata(self, item_type, item):
        """
        Creates a storage transaction using the precompile to be sent on-chain through the Gas Station.
        """
        add_item_function_signature = "addItem(bytes,bytes)"
        add_item_function_selector = self.w3.keccak(text=add_item_function_signature)[:4].hex()
        
        logger.debug("Name of item type being stored: ".format(repr(item_type)))
        logger.debug("Name of item being stored: ".format(repr(item)))
        item_type = item_type.encode("utf-8").hex()
        item = item.encode("utf-8").hex()
        # Create the encoded parameters to create calldata
        encoded_params = encode(
            ['bytes', 'bytes'],
            [bytes.fromhex(item_type), bytes.fromhex(item)]
        ).hex()
        
        calldata = add_item_function_selector + encoded_params
        logger.debug("peaq storage calldata: ".format(repr(calldata)))
        return calldata
    
    def generate_eoa_signature(self, machine_address, target, data, nonce):
        """
        Generates an EOA signature for a transaction. Needs the externally a
        """
        
        packed = encode_packed(
            ['address', 'address', 'bytes', 'uint256'],
            [
                machine_address,
                target,
                bytes.fromhex(data),
                nonce
            ]
        )

        message_hash = keccak(packed)
        message_hash_hex = "0x" + message_hash.hex()
        return message_hash_hex

        logger.debug("Externally Owner Account signature: {}".format(repr(eoa_signature)))
        # return eoa_signature
    
    def generate_owner_signature(self, eoa, target, data, nonce):
        """
        Generates an owner signature for a transaction.
        """
        packed = encode_packed(
            ['address', 'address', 'address', 'bytes', 'uint256'],
            [
                self.gas_station_address,
                eoa,
                target,
                bytes.fromhex(data),
                nonce
            ]
        )

        message_hash = keccak(packed)
        message = encode_defunct(primitive=message_hash)
        owner_signature = self.owner_account.sign_message(message).signature.hex()
        logger.debug("Gas Station Owner Signature used for sending a funded tx: {}".format(repr(owner_signature)))
        return owner_signature

    def execute_funded_transaction(self, eoa, machine_address, target, data, nonce, signature, eoa_signature):
        """
        Executes a transaction using the executeTransaction() function in the Gas Station contract.
        """
        if eoa_signature.startswith("0x"):
            new = eoa_signature[2:]  # Remove the "0x" prefix
        tx = self.gas_station.functions.executeTransaction(
            Web3.to_checksum_address(eoa),
            Web3.to_checksum_address(machine_address),
            target,
            bytes.fromhex(data),
            nonce,
            bytes.fromhex(signature),
            bytes.fromhex(new)
        )

        return self.send_transaction(tx)

    # Calls the smart contract to perform the transaction
    def send_transaction(self, tx):
        """
        Builds, signs, and sends a transaction to the peaq/agung network.
        """
        # print("before", self.owner_account.address)
        checksum_address = Web3.to_checksum_address(self.owner_account.address)
        # print("after", self.owner_account.address)
        estimated_gas = tx.estimate_gas({'from': checksum_address})
        logger.debug("Estimated Gas: {}".format(estimated_gas))
        chain_data = self._get_chain_data(self.owner_account, checksum_address)

        tx = tx.build_transaction({
            'nonce': chain_data["nonce"],
            'gas': estimated_gas,
            'gasPrice': chain_data["gas_price"],
            'chainId': chain_data["chain_id"]
        })
        logger.debug("Transaction to Send: {}".format(tx))

        signed_tx = self.owner_account.sign_transaction(tx)
        tx_receipt = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = self.w3.to_hex(tx_receipt)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        logger.debug("Transaction receipt: {}".format(tx))
        return receipt
    
    
    def verify(self, endpoint, data):
        """
        Generic function to send verification requests.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "APIKEY": self.service_api_key,
            "P-APIKEY": self.project_api_key
        }

        response = requests.post(f"{self.peaq_service_url}/{endpoint}", json=data, headers=headers)
        response.raise_for_status()
        return response.json()

    def verify_did(self, email, tag):
        """
        Verifies a DID.
        """
        data = {
            "address": email,
            "tag": tag
        }
        return self.verify("v1/verify/did", data)

    def verify_storage(self, email, tag):
        """
        Verifies storage.
        """
        data = {
            "address": email,
            "tag": tag
        }
        return self.verify("v1/data/verify", data)

    def verify_storage_count(self, email, expected_count, tag):
        """
        Verifies storage count.
        """
        data = {
            "address": email,
            "expected_count": expected_count,
            "tag": tag
        }
        return self.verify("v1/data/verify-count", data)


    def _local_sign(self, account, message):
        message = message.encode('utf-8')
        signable_message = encode_defunct(message)
        eoa_signature = account.sign_message(signable_message).signature.hex()
        return eoa_signature

    def _deserialize_did(self, data):
        deserialized_doc = peaq_py_proto.Document()
        deserialized_doc.ParseFromString(data)  # ParseFromString modifies deserialized_doc in place
        return deserialized_doc
    
    def _get_chain_data(self, from_account, checksum_address):
        chain_id = self.w3.eth.chain_id  # rpc_url chain id that is connected to web3
        gas_price = self.w3.eth.gas_price  # get current gas price from the connected network
        nonce = self.w3.eth.get_transaction_count(checksum_address)  # obtain nonce from your account address
        logger.debug("Chain ID: {}".format(chain_id))
        logger.debug("Gas Price: {}".format(gas_price))
        logger.debug("Account Nonce: {}".format(nonce))
        return {"chain_id": chain_id, "gas_price": gas_price, "nonce": nonce}

    def _load_abi(self, filename):
        result = _abi_cache.get(filename)
        if result is None:    
            project_root = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir))
            # Construct the path to the sibling directory
            sibling_path = os.path.join(project_root, "precompile_abi", f"{filename}.json")
            with open(sibling_path) as f:
                result = json.load(f)['output']['abi']
            _abi_cache[filename] = result
        return result

    def _call_service(self, relative_url, data):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "APIKEY": self.api_key,
            "P-APIKEY": self.project_api_eky
        }
        # Send the POST request
        response = requests.post(f"{self.peaq_service_url}/v1/{relative_url}", json=data, headers=headers)
        response.raise_for_status()
        return response.json()
