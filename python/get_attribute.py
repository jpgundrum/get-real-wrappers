import hashlib
from eth_utils import to_bytes, keccak
from substrateinterface.utils.ss58 import ss58_decode
from substrateinterface.utils.hasher import blake2_256
from eth_abi import encode

def create_storage_keys(account_address, name):
    """
    Generate the hashed key for the given DID and attribute name.

    Args:
        account_address (str): The account address (SS58 or Ethereum hex format).
        name (str): The name of the attribute.

    Returns:
        str: The hashed key (Blake2b-256 hash as hex string).
    """
    keys_byte_array = []

    # Decode account address (SS58 or hex) into bytes
    try:
        decoded_address = bytes.fromhex(account_address[2:])  # If Ethereum address (0x...)
    except ValueError:
        decoded_address = ss58_decode(account_address)  # If SS58 address

    # Convert the name into bytes
    name_bytes = name.encode("utf-8")

    # Concatenate address and name bytes
    concatenated_key = decoded_address + name_bytes

    # Hash the concatenated key using Blake2b-256
    hashed_key = blake2_256(concatenated_key).hex()

    return hashed_key

def generate_read_attribute_calldata(did_account, name):
    """
    Generate the calldata for the `readAttribute` precompile.

    Args:
        did_account (str): The DID account address (Ethereum hex format).
        name (str): The name of the attribute.

    Returns:
        str: The calldata for the `readAttribute` precompile.
    """
    # Function selector for `readAttribute(address,bytes)`
    function_signature = "readAttribute(address,bytes)"
    function_selector = keccak(text=function_signature)[:4].hex()

    
    # did_account = did_account.encode("utf-8").hex()
    # Encode the parameters
    encoded_params = encode(
        ['address', 'bytes'],
        [did_account, name.encode("utf-8")]
    ).hex()

    # Combine the function selector and encoded parameters
    calldata = function_selector + encoded_params

    return calldata

def read_did_document(w3, precompile_address, did_account, name):
    """
    Read the DID document using the `readAttribute` precompile.

    Args:
        w3: The Web3 instance.
        precompile_address (str): The precompile address for the DID contract.
        did_account (str): The DID account address (Ethereum hex format).
        name (str): The name of the attribute to read.

    Returns:
        bytes: The raw attribute data (DID document).
    """
    # Generate the calldata
    calldata = generate_read_attribute_calldata(did_account, name)

    # Call the precompile
    result = w3.eth.call({
        'to': precompile_address,
        'data': calldata
    })

    return result
