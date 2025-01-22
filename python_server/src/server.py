import os
import random
from getRealSdk import GetRealSdk
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize logging
from logs.logger import server_logger


# Load environment variables
PEAQ_RPC_URL = os.environ.get("PEAQ_RPC_URL")
CHAIN_ID = 9990
PEAQ_SERVICE_URL = os.environ.get("PEAQ_SERVICE_URL")
SERVICE_API_KEY = os.environ.get("SERVICE_API_KEY")
PROJECT_API_KEY = os.environ.get("PROJECT_API_KEY")
GAS_STATION_ADDRESS = os.environ.get("GAS_STATION_ADDRESS")
GAS_STATION_OWNER_PRIVATE_KEY = os.environ.get("GAS_STATION_OWNER_PRIVATE_KEY")
EOA_PRIVATE_KEY = os.environ.get("EOA_PRIVATE_KEY")

PRECOMPILE_ADDRESS_DID = "0x0000000000000000000000000000000000000800"
PRECOMPILE_ADDRESS_STORAGE = "0x0000000000000000000000000000000000000801"


serviceSdk = GetRealSdk(PEAQ_RPC_URL, CHAIN_ID, PEAQ_SERVICE_URL, SERVICE_API_KEY, PROJECT_API_KEY, GAS_STATION_ADDRESS, GAS_STATION_OWNER_PRIVATE_KEY, EOA_PRIVATE_KEY)


app = Flask(__name__)

@app.route('/create-smart-account', methods=['POST'])
def create_smart_account():
    """Mimics the /create-smart-account route from the JS server."""
    try:
        event_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        server_logger.debug("Creating signature for deploy machine smart account by the gas station factory owner")
        deploy_signature = serviceSdk.owner_sign_typed_data_deploy_machine_smart_account(event_data["eoaAddress"], nonce)
        machine_address = serviceSdk.deploy_machine_smart_account(event_data["eoaAddress"], nonce, deploy_signature)

        data = {
            "eoaAddress": event_data["eoaAddress"],
            "machineAddress": machine_address,
            "nonce": nonce + 1,
        }
        return jsonify({"success": True, "payload": data}), 200

    except Exception as e:
        server_logger.error(f"create smart account error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
    
@app.route('/transfer-machine-station-balance', methods=['POST'])
def transfer_machine_station_balance():
    try:
        event_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        server_logger.debug("Generating signature for a machine station balance transfer.")
        owner_function_signature = serviceSdk.owner_sign_typed_data_transfer_machine_station_balance(event_data["newMachineStationAddress"], nonce)
        server_logger.debug("Generated signature for a machine station balance transfer.")
        
        server_logger.debug(f"Transferring Machine StationBalance from ${event_data["oldMachineStationAddress"]} to ${event_data["newMachineStationAddress"]}")
        serviceSdk.transfer_machine_station_balance(event_data["newMachineStationAddress"], nonce, owner_function_signature)
        server_logger.debug(f"Successful Transfer from Machine StationBalance from ${event_data["oldMachineStationAddress"]} to ${event_data["newMachineStationAddress"]}")
        
        data = { "successfully": "executed"}
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"transfer machine station balance error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
    
@app.route('/generate-storage-tx', methods=['POST'])
def generate_storage_tx():
    try:
        event_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        server_logger.debug("Generating the Data Storage Key for your item type and tag")
        response = serviceSdk.store_data_key(event_data["email"], event_data["itemType"], event_data["tag"])
        server_logger.debug("Successfully created a data key with the response:\n {}".format(response))
        
        server_logger.debug("Generating storage Add Item calldata")
        storage_calldata = serviceSdk.create_storage_calldata(event_data["itemType"], event_data["item"])
        server_logger.debug("Generated storage Add Item calldata of: {}".format(storage_calldata))

        # now only sign with the gas station factory owner, since we are doing a generic storage tx (without machine account)
        owner_signature = serviceSdk.owner_sign_typed_data_execute_transaction(PRECOMPILE_ADDRESS_STORAGE, storage_calldata, nonce)
        
        
        data = {
            "target": PRECOMPILE_ADDRESS_STORAGE,
            "calldata": storage_calldata,
            "nonce": nonce,
            "ownerSignature": owner_signature,
        }
        return jsonify({"success": True, "payload": -1}), 200
    except Exception as e:
        server_logger.error(f"generate storage tx error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/generate-did-tx', methods=['POST'])
def generate_did_tx():
    try:
        event_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        server_logger.debug("Creating email signature from peaq get-real service endpoint")
        email_signature = serviceSdk.generate_email_signature(event_data["email"], event_data["userAddress"], event_data["tag"])
        server_logger.debug("Eemail signature generated.")
        
        server_logger.debug("Serializing DID to be sent on-chain")
        did_serialization = serviceSdk.create_did_serialization(event_data["userAddress"], email_signature, event_data["userAddress"])
        server_logger.debug("Did serialization completed with value: {}".format(did_serialization))

        server_logger.debug("Generating DID Add Attribute Transaction")
        did_calldata = serviceSdk.create_did_calldata(event_data["userAddress"], event_data["company"], did_serialization)
        server_logger.debug("Generated DID Add Attribute calldata of: {}".format(did_calldata))
        
        owner_signature = serviceSdk.owner_sign_typed_data_execute_transaction(PRECOMPILE_ADDRESS_DID, did_calldata, nonce)
        
        data = {
            "target": PRECOMPILE_ADDRESS_DID,
            "calldata": did_calldata,
            "nonce": nonce,
            "ownerSignature": owner_signature,
        }
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"generate did tx error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/execute-tx', methods=['POST'])
def execute_tx():
    try:
        event_data = request.json
        
        serviceSdk.execute_transaction(
            event_data["target"],
            event_data["calldata"],
            event_data["nonce"],
            event_data["ownerSignature"],
        )
        
        
        data = { "successfully": "executed"}
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"Execute Transaction Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    

@app.route('/generate-smart-account-storage-tx', methods=['POST'])
def generate_smart_account_storage_tx():
    try:
        event_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        server_logger.debug("Generating the Data Storage Key for your item type and tag")
        response = serviceSdk.store_data_key(event_data["email"], event_data["itemType"], event_data["tag"])
        server_logger.debug("Successfully created a data key with the response:\n {}".format(response))
        
        server_logger.debug("Generating storage Add Item calldata")
        storage_calldata = serviceSdk.create_storage_calldata(event_data["itemType"], event_data["item"])
        server_logger.debug("Generated storage Add Item calldata of: {}".format(storage_calldata))
        
        server_logger.debug("Generating signature from EOA account")
        machine_owner_signature = serviceSdk.machine_sign_typed_data_execute_machine_transaction(event_data["machineAddress"], PRECOMPILE_ADDRESS_STORAGE, storage_calldata, nonce)
        server_logger.debug("Generated signature from EOA account.")
        
        server_logger.debug("Generating signature for the owner of the Gas Station to give their approval for the machine transaction")
        owner_signature = serviceSdk.owner_sign_typed_data_execute_machine_transaction(event_data["machineAddress"], PRECOMPILE_ADDRESS_STORAGE, storage_calldata, nonce)
        server_logger.debug("Generated signature for the owner.")

        data = {
            "machineAddress": event_data["machineAddress"],
            "target": PRECOMPILE_ADDRESS_STORAGE,
            "calldata": storage_calldata,
            "nonce": nonce,
            "ownerSignature": owner_signature,
            "signature": machine_owner_signature,
    }
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"generate did tx error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/generate-smart-account-create-did-tx', methods=['POST'])
def generate_smart_account_create_did_tx():
    try:
        event_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        server_logger.debug("Creating email signature from peaq get-real service endpoint")
        email_signature = serviceSdk.generate_email_signature(event_data["email"], event_data["machineAddress"], event_data["tag"])
        server_logger.debug("Eemail signature generated.")
        
        server_logger.debug("Serializing DID to be sent on-chain")
        did_serialization = serviceSdk.create_did_serialization(event_data["eoaAddress"], email_signature, event_data["machineAddress"])
        server_logger.debug("Did serialization completed with value: {}".format(did_serialization))

        server_logger.debug("Generating DID Add Attribute Transaction")
        did_calldata = serviceSdk.create_did_calldata(event_data["machineAddress"], event_data["company"], did_serialization)
        server_logger.debug("Generated DID Add Attribute calldata of: {}".format(did_calldata))
        
        
        server_logger.debug("Generating signature from EOA account")
        machine_owner_signature = serviceSdk.machine_sign_typed_data_execute_machine_transaction(event_data["machineAddress"], PRECOMPILE_ADDRESS_DID, did_calldata, nonce)
        server_logger.debug("Generated signature from EOA account.")
        
        server_logger.debug("Generating signature for the owner of the Gas Station to give their approval for the machine transaction")
        owner_signature = serviceSdk.owner_sign_typed_data_execute_machine_transaction(event_data["machineAddress"], PRECOMPILE_ADDRESS_DID, did_calldata, nonce)
        server_logger.debug("Generated signature for the owner.")
        
        
        data = {
            "machineAddress": event_data["machineAddress"],
            "target": PRECOMPILE_ADDRESS_DID,
            "calldata": did_calldata,
            "nonce": nonce,
            "ownerSignature": owner_signature,
            "signature": machine_owner_signature
        }
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"generate did tx error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/execute-machine-tx', methods=['POST'])
def execute_machine_tx():
    try:
        event_data = request.json
        
        serviceSdk.execute_machine_transaction(
            event_data["machineAddress"],
            event_data["target"],
            event_data["calldata"],
            event_data["nonce"],
            event_data["ownerSignature"],
            event_data["signature"],
        )
        
        
        data = { "successfully": "executed"}
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"generate did tx error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/execute-machine-batch-txs', methods=['POST'])
def execute_machine_batch_txs():
    try:
        batch_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        machine_addresses = [tx["machineAddress"] for tx in batch_data]
        targets = [tx["target"] for tx in batch_data]
        calldata = [tx["calldata"] for tx in batch_data]
        machine_nonces = [tx["nonce"] for tx in batch_data]
        machine_owner_signatures = [tx["signature"] for tx in batch_data]
        
        owner_signature = serviceSdk.owner_sign_typed_data_execute_machine_batch_transaction(machine_addresses, targets, calldata, nonce, machine_nonces)
        
        
        serviceSdk.execute_machine_batch_transaction(
            machine_addresses,
            targets,
            calldata,
            nonce,
            machine_nonces,
            owner_signature,
            machine_owner_signatures
        )

        data = { "successfully": "executed"}
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"generate did tx error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route('/execute-machine-transfer-balance', methods=['POST'])
def execute_machine_transfer_balance():
    try:
        event_data = request.json
        nonce = random.randint(1, 1_000_000_000)
        
        machine_owner_signature = serviceSdk.machine_sign_typed_data_transfer_machine_balance(event_data["machineAddress"], event_data["recipientAddress"], nonce)
        owner_signature = serviceSdk.owner_sign_typed_data_transfer_machine_balance(event_data["machineAddress"], event_data["recipientAddress"], nonce)
        
        serviceSdk.execute_machine_transfer_balance(
            event_data["machineAddress"],
            event_data["recipientAddress"],
            nonce,
            owner_signature,
            machine_owner_signature
        )
        
        data = { "successfully": "executed"}
        return jsonify({"success": True, "payload": data}), 200
    except Exception as e:
        server_logger.error(f"generate did tx error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = 3000
    # Start the server
    app.run(host='0.0.0.0', port=port, debug=True)
    
    
    
    
# temp fix: export PYTHONPATH=$(pwd)