from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utils.user_signup import user_signup
from utils.create_tx import create_tx
from utils.send_tx import send_tx

from threading import Lock

app = FastAPI()

# -- Global constants/variables --
nonce = 335  # Initial value
nonce_lock = Lock()  # To prevent race conditions

# -- In-memory data stores (replace with DB in production) --
eoa_data_store = {}       # { eoa_address: {... eoa_object ...} }
pending_did_messages = {} # { eoa_address: did_message }
pending_eoa_messages = {} # { eoa_address: eoa_tx_message }

# -- CORS configuration --
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, limit to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------
# 1) Helper Functions
# --------------------------------------------------------------------


# Increment and get the global nonce atomically
def get_and_increment_nonce():
    global nonce
    with nonce_lock:
        current_nonce = nonce
        nonce += 1
    return current_nonce

def get_eoa_object(eoa_address: str):
    """
    Retrieve the EOA object from in-memory store or return None if it doesn't exist.
    """
    return eoa_data_store.get(eoa_address)

def respond_with_success(data: dict, status_code: int = 200):
    """
    Return a standard success response.
    """
    content = {"status": "success"}
    content.update(data)
    return JSONResponse(content=content, status_code=status_code)

def respond_with_error(message: str, status_code: int = 400):
    """
    Return a standard error response.
    """
    content = {"status": "error", "message": message}
    return JSONResponse(content=content, status_code=status_code)

# --------------------------------------------------------------------
# 2) Signup & DID Generation
# --------------------------------------------------------------------
@app.post("/api/signup")
async def signup(request: Request):
    data = await request.json()
    email = data.get("email")
    eoa_address = data.get("eoa_address")
    tag = data.get("tag", "TEST")  # Default "TEST" if not provided

    if not eoa_address:
        return respond_with_error("Missing eoa_address")

    eoa_object = {
        "email": email,
        "eoa_address": eoa_address,
        "tag": tag,
    }

    response = user_signup(eoa_object, nonce)
    get_and_increment_nonce()
    if response["status"] == "success":
        # Save the eoa_object in memory
        eoa_data_store[eoa_address] = eoa_object
        # Return the message to sign
        return respond_with_success({"did_tx_message": response["message"]})
    else:
        return respond_with_error(response["message"])


# --------------------------------------------------------------------
# 3) Generate EOA Tx Message
# --------------------------------------------------------------------
@app.post("/api/generate-eoa-tx-message")
async def generate_eoa_tx_message(request: Request):
    data = await request.json()
    signature = data.get("signature")
    eoa_address = data.get("eoa_address")
    target = data.get("target")

    eoa_object = get_eoa_object(eoa_address)
    if not eoa_object:
        return respond_with_error("No eoa_event found for this wallet.")
    
    print("EOA NONCE", nonce)
    response = create_tx(eoa_object, signature, target, nonce, "")
    if response["status"] == "success":
        # Save the calldata in memory to be referenced later
        eoa_object["calldata"] = response["calldata"]
        eoa_data_store[eoa_address] = eoa_object
        return respond_with_success({"eoa_tx_message": response["message"]})
    else:
        return respond_with_error(response["message"])


# --------------------------------------------------------------------
# 4) Execute Tx (aka "/api/test")
# --------------------------------------------------------------------
@app.post("/api/test")
async def test_endpoint(request: Request):
    data = await request.json()
    eoa_signature = data.get("signature")
    eoa_address = data.get("eoa_address")
    target = data.get("target")

    eoa_object = get_eoa_object(eoa_address)
    if not eoa_object:
        return respond_with_error("No eoa_event found for this wallet.")

    print("My object:", eoa_object)
    print("Target: ", target)
    print("Nonce: ", nonce)
    response = send_tx(eoa_object, eoa_signature, target, nonce)
    get_and_increment_nonce()
    if response["status"] == "success":
        # delete the previously stored calldata
        del eoa_object["calldata"]
        eoa_data_store[eoa_address] = eoa_object
        return respond_with_success({"message": response["message"]})
    else:
        return respond_with_error(response["message"])


# --------------------------------------------------------------------
# 5) (Optional) Storage Transaction Endpoint
# --------------------------------------------------------------------
@app.post("/api/storage-transaction")
async def storage_transaction(request: Request):
    data = await request.json()
    eoa_address = data.get("eoa_address")
    target = data.get("target")
    item_type = data.get("item_type")
    item = data.get("item")
    quest_data = {}
    quest_data["item_type"] = item_type
    quest_data["item"] = item
    

    # Additional payload for the storage logic

    eoa_object = get_eoa_object(eoa_address)
    if not eoa_object:
        return respond_with_error("No eoa_event found for this wallet.")
    
    print("My object:", eoa_object)
    print("Target: ", target)
    print("Nonce: ", nonce)
    print("Nonce: ", quest_data)
    
    response = create_tx(eoa_object, "", target, nonce, quest_data)
    if response["status"] == "success":
        # Save the calldata in memory to be referenced later
        eoa_object["calldata"] = response["calldata"]
        eoa_data_store[eoa_address] = eoa_object
        return respond_with_success({"eoa_tx_message": response["message"]})
    else:
        return respond_with_error(response["message"])



# Start the server with:
# python % uvicorn python_server.event_listener:app --reload