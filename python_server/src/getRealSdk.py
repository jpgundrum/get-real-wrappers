import os
import json
import logging
import requests
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_hex
from eth_abi import encode

from web3 import Web3
from dotenv import load_dotenv

from logs.logger import sdk_logger
from did_serialization import peaq_py_proto



class GetRealSdk:
    """
    A Python equivalent of your 'getRealSdk' class in JavaScript.
    """

    def __init__(
        self,
        rpc_url: str,
        chain_id: int,
        peaq_service_url: str,
        service_api_key: str,
        project_api_key: str,
        gas_station_address: str,
        gas_station_owner_private: str,
        eoa_private: str,
    ):
        """
        Initialize the Python version of getRealSdk.
        :param rpc_url: The RPC URL for your network (e.g. Peaq).
        :param chain_id: Chain ID (e.g. 9990 for Agung).
        :param peaq_service_url: URL for the Get-Real (peaq) service.
        :param service_api_key: Your service API key for the peaq service.
        :param project_api_key: The project-specific API key.
        :param gas_station_address: The address of your Gas Station contract.
        :param gas_station_owner_private: Private key for the Gas Station owner account.
        :param eoa_private: Private key for the EOA account (if needed).
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.chain_id = chain_id
        self.peaq_service_url = peaq_service_url
        self.service_api_key = service_api_key
        self.project_api_key = project_api_key
        self.gas_station_address = gas_station_address
        self.gas_station_owner_private = gas_station_owner_private
        self.eoa_private = eoa_private

        # Create a wallet to perform transactions
        self.owner_account = Account.from_key(gas_station_owner_private)
        self.eoa_account = Account.from_key(eoa_private)
        
        # self.owner_account = self.w3.eth.account.from_key(gas_station_owner_private)
        # self.eoaAccount = self.w3.eth.account.from_key(eoa_private)
        
        
        # Create an instance of the gas station contract to perform operation
        self.gas_station_abi = self._load_abi("gas_station_abi.json")
        self.gas_station = self.w3.eth.contract(
            address=self.gas_station_address,
            abi=self.gas_station_abi["abi"]
        )

        sdk_logger.debug(f"Initialized GetRealSdk with chain_id={chain_id}, gas_station_address={gas_station_address}")


    # source: https://eth-account.readthedocs.io/en/stable/eth_account.html#eth_account.messages.encode_typed_data
    #
    # Next ... functions are used to signed typed data
    def owner_sign_typed_data_deploy_machine_smart_account(self, eoa_address: str, nonce: int) -> str:
        """
        Example placeholder method for generating an EIP-712 typed-data signature
        for deploying a machine smart account.
        """
        try:
            domain = {
                "name": "MachineStationFactory",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": self.gas_station_address
            }
            types = {
                "DeployMachineSmartAccount": [
                    {"name": "machineOwner", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                ],
            }
            message = {
                "machineOwner": eoa_address,
                "nonce": nonce
            }
            
            signable_message = encode_typed_data(domain, types, message)
            signature = self.owner_account.sign_message(signable_message).signature.hex()
            sdk_logger.debug("Successfully generated the machine account deployment signature")
            return "0x" + signature
        except Exception as e:
            sdk_logger.error(f"Error generating deployment signature: {str(e)}")
            raise
        
    def owner_sign_typed_data_transfer_machine_station_balance(self, new_machine_station_address, nonce):
        try: 
            domain = {
                "name": "MachineStationFactory",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": self.gas_station_address
            }
            types = {
                "TransferMachineStationBalance": [
                    {"name": "newMachineStationAddress", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                ],
            }
            message = {
                "newMachineStationAddress": new_machine_station_address,
                "nonce": nonce
            }
            
            signable_message = encode_typed_data(domain, types, message)
            signature = self.owner_account.sign_message(signable_message).signature.hex()
            sdk_logger.debug("Successfully generated the transfer machine station balance signature.")
            return "0x" + signature
        except Exception as e:
            sdk_logger.error(f"Error generating the transfer machine station balance signature: {str(e)}")
            raise
        
    def owner_sign_typed_data_execute_transaction(self, target, calldata, nonce):
        try:
            domain = {
                "name": "MachineStationFactory",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": self.gas_station_address
            }
            types = {
                "ExecuteTransaction": [
                    {"name": "target", "type": "address"},
                    {"name": "data", "type": "bytes"},
                    {"name": "nonce", "type": "uint256"},
                ],
            }
            message = {
                "target": target,
                "data": calldata,
                "nonce": nonce
            }
            
            signable_message = encode_typed_data(domain, types, message)
            signature = self.owner_account.sign_message(signable_message).signature.hex()
            sdk_logger.debug("Successfully generated the execute transaction signature.")
            return "0x" + signature
        except Exception as e:
            sdk_logger.error(f"Error generating the execute transaction signature: {str(e)}")
            raise
        
    def machine_sign_typed_data_execute_machine_transaction(self, machineAddress, target, calldata, nonce):
        try:
            domain = {
                "name": "MachineSmartAccount",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": machineAddress
            }
            types = {
                "Execute": [
                    {"name": "target", "type": "address"},
                    {"name": "data", "type": "bytes"},
                    {"name": "nonce", "type": "uint256"},
                ],
            }
            message = {
                "target": target,
                "data": calldata,
                "nonce": nonce
            }
            
            signable_message = encode_typed_data(domain, types, message)
            signature = self.eoa_account.sign_message(signable_message).signature.hex()
            sdk_logger.debug("Successfully generated the execute transaction signature.")
            return "0x" + signature
        
        except Exception as e:
            sdk_logger.error(f"Error generating the execute machine transaction signature from the eoa account: {str(e)}")
            raise
        
    def owner_sign_typed_data_execute_machine_transaction(self, machineAddress, target, calldata, nonce):
        try:
            domain = {
                "name": "MachineStationFactory",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": self.gas_station_address
            }
            types = {
                "ExecuteMachineTransaction": [
                    {"name": "machineAddress", "type": "address"},
                    {"name": "target", "type": "address"},
                    {"name": "data", "type": "bytes"},
                    {"name": "nonce", "type": "uint256"},
                ],
            }
            message = {
                "machineAddress": machineAddress,
                "target": target,
                "data": calldata,
                "nonce": nonce
            }
            
            signable_message = encode_typed_data(domain, types, message)
            signature = self.owner_account.sign_message(signable_message).signature.hex()
            sdk_logger.debug("Successfully generated the execute transaction signature.")
            return "0x" + signature
        
        except Exception as e:
            sdk_logger.error(f"Error generating the execute machine transaction signature from the owner account {str(e)}")
            raise
        
    def owner_sign_typed_data_execute_machine_batch_transaction(self, machineAddresses, targets, calldata, nonce, machineNonces):
        try:
            domain = {
                "name": "MachineStationFactory",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": self.gas_station_address
            }
            types = {
                "ExecuteMachineBatchTransactions": [
                    {"name": "machineAddresses", "type": "address[]"},
                    {"name": "targets", "type": "address[]"},
                    {"name": "data", "type": "bytes[]"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "machineNonces", "type": "uint256[]"},
                ],
            }
            message = {
                "machineAddresses": machineAddresses,
                "targets": targets,
                "data": calldata,
                "nonce": nonce,
                "machineNonces": machineNonces
            }
            
            signable_message = encode_typed_data(domain, types, message)
            signature = self.owner_account.sign_message(signable_message).signature.hex()
            sdk_logger.debug("Successfully generated the execute transaction signature.")
            return "0x" + signature
        
        except Exception as e:
            sdk_logger.error(f"Error generating the execute machine batch transactions signature from the owner account {str(e)}")
            raise
        
    def machine_sign_typed_data_transfer_machine_balance(self, machineAddress, recipientAddress, nonce):
        try:
            domain = {
                "name": "MachineSmartAccount",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": machineAddress
            }
            types = {
                "TransferMachineBalance": [
                    {"name": "recipientAddress", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                ],
            }
            message = {
                "recipientAddress": recipientAddress,
                "nonce": nonce
            }
            
            signable_message = encode_typed_data(domain, types, message)
            signature = self.eoa_account.sign_message(signable_message).signature.hex()
            sdk_logger.debug("Successfully generated the execute transaction signature.")
            return "0x" + signature
        except Exception as e:
            sdk_logger.error(f"Error generating the transfer machine balance signature from the eoa account: {str(e)}")
            raise
        
    def owner_sign_typed_data_transfer_machine_balance(self, machineAddress, recipientAddress, nonce):
        try: 
            domain = {
                "name": "MachineStationFactory",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": self.gas_station_address
            }
            types = {
                "ExecuteMachineTransferBalance": [
                    {"name": "machineAddress", "type": "address"},
                    {"name": "recipientAddress", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                ],
            }
            message = {
                "machineAddress": machineAddress,
                "recipientAddress": recipientAddress,
                "nonce": nonce
            }
            signable_message = encode_typed_data(domain, types, message)
            signature = self.owner_account.sign_message(signable_message).signature.hex()
            return "0x" + signature
        except Exception as e:
            sdk_logger.error(f"Error generating owner Transfer Machine Station Balance signature: {str(e)}")
            raise
        
    
        
    # Next ... functions are used to send transactions
    def deploy_machine_smart_account(self, eoaAddress, nonce, signature):
        try: 
            deploy_tx = self.gas_station.functions.deployMachineSmartAccount(
                eoaAddress,
                nonce,
                signature
            )
            receipt = self.send_transaction(deploy_tx)
            event_signature = keccak(text="MachineSmartAccountDeployed(address)").hex()
            
            for log in receipt["logs"]:
                if log["topics"][0].hex() == event_signature and len(log["topics"]) > 1:
                    machine_address = Web3.to_checksum_address(log["topics"][1].hex()[24:])
                    sdk_logger.debug("Contract Address of the deployed Machine Smart Account: {}".format(repr(machine_address)))
                    return machine_address

            raise ValueError("MachineSmartAccountDeployed event not found in logs")
        except Exception as e:
            sdk_logger.error(f"Error deploying machine smart account: {str(e)}")
            raise
    
    def transfer_machine_station_balance(self, new_machine_station_address, nonce, signature):
        try:
            deploy_tx = self.gas_station.functions.transferMachineStationBalance(
                new_machine_station_address,
                nonce,
                signature
            )
            self.send_transaction(deploy_tx)
        except Exception as e:
            sdk_logger.error(f"Error transferring the machine station balance: {str(e)}")
            raise
        
    def execute_transaction(self, target, calldata, nonce, ownerSignature):
        try:
            deploy_tx = self.gas_station.functions.executeTransaction(
                target,
                calldata,
                nonce,
                ownerSignature
            )
            self.send_transaction(deploy_tx)
        except Exception as e:
            sdk_logger.error(f"Error executing the generic transaction: {str(e)}")
            raise
    
    def execute_machine_transaction(self, machineAddress, target, calldata, nonce, ownerSignature, eoaSignature):
        try:
            deploy_tx = self.gas_station.functions.executeMachineTransaction(
                machineAddress,
                target,
                calldata,
                nonce,
                ownerSignature,
                eoaSignature
            )
            self.send_transaction(deploy_tx)
        except Exception as e:
            sdk_logger.error(f"Error executing the machine transaction: {str(e)}")
            raise
        
    def execute_machine_batch_transaction(self, machineAddresses, targets, calldata, nonce, machineNonces, ownerSignature, machineOwnerSignatures):
        try:
            deploy_tx = self.gas_station.functions.executeMachineBatchTransactions(
                machineAddresses,
                targets,
                calldata,
                nonce,
                machineNonces,
                ownerSignature,
                machineOwnerSignatures
            )
            self.send_transaction(deploy_tx)
        except Exception as e:
            sdk_logger.error(f"Error executing the batch transactions: {str(e)}")
            raise
        
    def execute_machine_transfer_balance(self, machineAddress, recipientAddress, nonce, ownerSignature, machineOwnerSignature):
        try:
            deploy_tx = self.gas_station.functions.executeMachineTransferBalance(
                machineAddress,
                recipientAddress,
                nonce,
                ownerSignature,
                machineOwnerSignature
            )
            self.send_transaction(deploy_tx)
        except Exception as e:
            sdk_logger.error(f"Error executing the generic transaction: {str(e)}")
            raise
        
    # Calls the smart contract to perform the transaction
    def send_transaction(self, tx):
        """
        Builds, signs, and sends a transaction to the peaq/agung network.
        """
        checksum_address = Web3.to_checksum_address(self.owner_account.address)
        estimated_gas = tx.estimate_gas({'from': checksum_address})
        sdk_logger.debug("Estimated Gas: {}".format(estimated_gas))
        chain_data = self._get_chain_data(self.owner_account, checksum_address)

        tx = tx.build_transaction({
            'nonce': chain_data["nonce"],
            'gas': estimated_gas,
            'gasPrice': chain_data["gas_price"],
            'chainId': chain_data["chain_id"]
        })
        sdk_logger.debug("Transaction to Send: {}".format(tx))

        signed_tx = self.owner_account.sign_transaction(tx)
        tx_receipt = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = self.w3.to_hex(tx_receipt)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        sdk_logger.debug("Transaction receipt: {}".format(tx))
        return receipt
    
    
    

    
    # Next 2 functions are used in the get real service
    def store_data_key(self, email, item_type, tag):
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

            sdk_logger.debug("Data sent to service endpoint: {}".format(data))
            response = requests.post(f"{self.peaq_service_url}/v1/data/store", json=data, headers=headers)
            response.raise_for_status()
            sdk_logger.debug("Returned response object after storing data key:  {}".format(response.json()))
            return response.json()
        except Exception as e:
            sdk_logger.error(f"Error generating the store data key: {str(e)}")
            raise
        
    def generate_email_signature(self, email, machine_address, tag):
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
            sdk_logger.debug("Data sent to service endpoint: {}".format(data))
            response = requests.post(f"{self.peaq_service_url}/v1/sign", json=data, headers=headers)
            response.raise_for_status()
            email_signature = response.json()["data"]["signature"]
            sdk_logger.debug("Returned email signature for get-real service: {}".format(email_signature))
            return email_signature
        except Exception as e:
            sdk_logger.error(f"Error generating the email signature: {str(e)}")
            raise
    
    
    
    
    
    # future functions to be offered in the peaq python sdk for evm
    def create_storage_calldata(self, item_type, item):
        try:
            add_item_function_signature = "addItem(bytes,bytes)"
            add_item_function_selector = self.w3.keccak(text=add_item_function_signature)[:4].hex()
            
            sdk_logger.debug("Name of item type being stored: {}".format(item_type))
            sdk_logger.debug("Name of item being stored: {}".format(item))
            item_type = item_type.encode("utf-8").hex()
            item = item.encode("utf-8").hex()
            # Create the encoded parameters to create calldata
            encoded_params = encode(
                ['bytes', 'bytes'],
                [bytes.fromhex(item_type), bytes.fromhex(item)]
            ).hex()
            
            calldata = "0x" + add_item_function_selector + encoded_params
            sdk_logger.debug("peaq storage calldata: {}".format(calldata))
            print(calldata)
            return calldata
        except Exception as e:
            sdk_logger.error(f"Error creating the storage calldata: {str(e)}")
            raise
    
    def create_did_serialization(self, eoa_address, email_signature, machine_address):
        try: 
            doc = peaq_py_proto.Document()
            doc.id = f"did:peaq:{machine_address}"
            doc.controller = f"did:peaq:{machine_address}"

            service = doc.services.add()
            service.id = "#emailSignature"
            service.type = "emailSignature"
            service.data = email_signature
            
            service = doc.services.add()
            service.id = "#owner"
            service.type = "owner"
            service.data = eoa_address

            serialized_data = doc.SerializeToString()
            serialized_hex = serialized_data.hex()
            
            sdk_logger.debug("Serialized DID Hash created with value of: {}".format(serialized_hex))
            
            deserialized_did = self._deserialize_did(serialized_data)
            sdk_logger.debug("Deserialized Document: \n{}".format(deserialized_did))
            return serialized_hex
        except Exception as e:
            sdk_logger.error(f"Error generating did serialization: {str(e)}")
            raise
            
    def create_did_calldata(self, userAddress, company, serialized_did):
        try:
            did_function_signature = "addAttribute(address,bytes,bytes,uint32)"
            did_function_selector = self.w3.keccak(text=did_function_signature)[:4].hex()
            
            nameString = f"did:peaq:${userAddress}#${company}"
            sdk_logger.debug("Name of DID being stored: {}".format(nameString))
            sdk_logger.debug("Address at which the DID is being stored: {}".format(userAddress))
            # convert to bytes
            name = nameString.encode("utf-8").hex()
            did_hex = serialized_did.encode("utf-8").hex()
            encoded_params = encode(
                ['address', 'bytes', 'bytes', 'uint32'],
                [userAddress, bytes.fromhex(name), bytes.fromhex(did_hex), 0]
            ).hex()
            
            calldata = "0x" + did_function_selector + encoded_params
            sdk_logger.debug("Create DID calldata: {}".format(calldata))
            return calldata
        except Exception as e:
            sdk_logger.error(f"Error generating did calldata: {str(e)}")
            raise  
    
  
  
  
    
    # helper functions
    def _get_chain_data(self, from_account, checksum_address):
        chain_id = self.w3.eth.chain_id  # rpc_url chain id that is connected to web3
        gas_price = self.w3.eth.gas_price  # get current gas price from the connected network
        nonce = self.w3.eth.get_transaction_count(checksum_address)  # obtain nonce from your account address
        sdk_logger.debug("Chain ID: {}".format(chain_id))
        sdk_logger.debug("Gas Price: {}".format(gas_price))
        sdk_logger.debug("Account Nonce: {}".format(nonce))
        return {"chain_id": chain_id, "gas_price": gas_price, "nonce": nonce}
    
    def _load_abi(self, filename: str) -> list:
        """
        Loads an ABI JSON file located in ../abi relative to this script.
        Returns the parsed JSON as a Python object (list/dict).
        """
        current_dir = os.path.dirname(os.path.realpath(__file__))
        abi_dir = os.path.join(current_dir, "../abi")
        abi_path = os.path.join(abi_dir, filename)
        with open(abi_path, "r", encoding="utf-8") as f:
            return json.load(f)
        
    def _deserialize_did(self, data):
        deserialized_doc = peaq_py_proto.Document()
        deserialized_doc.ParseFromString(data)  # ParseFromString modifies deserialized_doc in place
        return deserialized_doc
    
    def _convert_to_bytes(self, hex_strings):
        test = [bytes.fromhex(data) for data in hex_strings]
        print(test)
        return test