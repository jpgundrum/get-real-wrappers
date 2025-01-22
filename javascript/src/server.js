import express from 'express';
import bodyParser from 'body-parser';
import cors from 'cors';
import { getRealSdk } from './getRealSdk.js';
import dotenv from 'dotenv';

import Web3 from 'web3'; // only used to mock eoa signature

dotenv.config();

import { sdkLogger, serverLogger } from '../logs/logger.js';

// Load environment variables
const PEAQ_RPC_URL = process.env.PEAQ_RPC_URL;
const PEAQ_SERVICE_URL = process.env.PEAQ_SERVICE_URL;
const SERVICE_API_KEY = process.env.SERVICE_API_KEY;
const PROJECT_API_KEY = process.env.PROJECT_API_KEY;
const GAS_STATION_ADDRESS = process.env.GAS_STATION_ADDRESS;
const GAS_STATION_OWNER_PRIVATE_KEY = process.env.GAS_STATION_OWNER_PRIVATE_KEY;
const EOA_PRIVATE_KEY = process.env.EOA_PRIVATE_KEY;
const PRECOMPILE_ADDRESS_DID = '0x0000000000000000000000000000000000000800';
const PRECOMPILE_ADDRESS_STORAGE = '0x0000000000000000000000000000000000000801';


// chainID:
// agung: 9990
// peaq: 3338
const chainID = 9990

// Initialize getRealSdk. TODO how to do this with multiple gas stations??
const serviceSdk = new getRealSdk(PEAQ_RPC_URL, chainID, PEAQ_SERVICE_URL, SERVICE_API_KEY, PROJECT_API_KEY, GAS_STATION_ADDRESS, GAS_STATION_OWNER_PRIVATE_KEY, EOA_PRIVATE_KEY);

const app = express();
const port = 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// DIFFERENT POSSIBLE FLOWS:
// User Signup:
// - When user signs up for the first time trigger /create-smart-account to get a Smart Account for that user that the gas station funds txs for.
// Return back the eoaAddress & the newly deployed Smart Account. Map eoa address to the smart account address to see if a user has been created already
// - Submit a /smart-account-create-did-tx to create a new DID that represents the smart account funded by the gas Station
// - When user tries to claim sign up reward check get-real backend to see if it has been found on-chain
//
// User Adds Storage
// - 
// 
// 
// Batch Transactions:
// - Multiple Smart Accounts to send multiple txs per smart contract call
// - Events being generated from different concurrent user/machine requests



// listen for machine smart account creation
app.post('/create-smart-account', async (req, res) => {
  try {
    const eventData = req.body; // Event data sent to the server
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;

    // Deployment signature used to confirm eoa requested the smart account creation
    serverLogger.debug("Requesting Gas Station Owner Deployment Signature");
    const deploySignature = await serviceSdk.ownerSignTypedDataDeployMachineSmartAccount(eventData.eoaAddress, nonce);

    serverLogger.debug("Deploying Machine Smart Account");
    const machineAddress = await serviceSdk.deployMachineSmartAccount(eventData.eoaAddress, nonce, deploySignature);
    serverLogger.debug(`Machine Smart Account deployed with address ${machineAddress}`);

    const data = {
      "eoaAddress": eventData.eoaAddress,
      "machineAddress": machineAddress,
      "nonce": nonce + 1, // increment by 1 after executing a transaction
    }
    res.status(200).json({ success: true, payload: data });

  } catch (error) {
    serverLogger.error(`Signup Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});

// For me:
// current 0x17bD3d6639b28Ee774040D3aE2137F49390a584c
app.post('/transfer-machine-station-balance', async (req,res) => {
  try {
    const eventData = req.body;

    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;

    serverLogger.debug("Generating signature for a machine station balance transfer");
    const ownerFunctionSignature = await serviceSdk.ownerSignTypedDataTransferMachineStationBalance(eventData.newMachineStationAddress, nonce);
    serverLogger.debug("Generated signature for a machine station balance transfer.");

    sdkLogger.debug(`Transferring Machine StationBalance from ${eventData.oldMachineStationAddress} to ${eventData.newMachineStationAddress}`);
    await serviceSdk.transferMachineStationBalance(eventData.newMachineStationAddress, nonce, ownerFunctionSignature);
    sdkLogger.debug(`Successful Transfer from Machine StationBalance from ${eventData.oldMachineStationAddress} to ${eventData.newMachineStationAddress}`);


    const data = { "successfully": "executed"}
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Transfer Machine Station Balance Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Generates a Gas Station Factory owner signed storage message.
app.post('/generate-storage-tx', async (req, res) => {
  try { 
    const eventData = req.body;
    console.log(eventData);
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;

    serverLogger.debug("Generating the Data Storage Key for your item type and tag");
    const response = await serviceSdk.storeDataKey(eventData.email, eventData.itemType, eventData.tag);
    serverLogger.debug(`Successfully created a data key with the response:\n${JSON.stringify(response, null, 2)}`);

    serverLogger.debug("Generating storage Add Item Transaction");
    const storageCalldata = await serviceSdk.createStorageCalldata(eventData.itemType, eventData.item);
    serverLogger.debug(`Generated storage Add Item calldata of: ${storageCalldata}`);

    // now only sign with the gas station factory owner
    const ownerSignature = await serviceSdk.ownerSignTypedDataExecuteTransaction(PRECOMPILE_ADDRESS_STORAGE, storageCalldata, nonce);


    const data = {
      "target": PRECOMPILE_ADDRESS_STORAGE,
      "calldata": storageCalldata,
      "nonce": nonce,
      "ownerSignature": ownerSignature,
    }
    
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Smart Account Storage Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});

// no machine smart account. Will just create the DID for the user address passed (no machine smart account to tie here.)
app.post('/generate-did-tx', async (req, res) => {
  try { 
    const eventData = req.body;
    console.log(eventData);
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;

      // Create did tx for user eoa on the frontend to sign
      serverLogger.debug("Creating email signature from peaq get-real service endpoint");
      const emailSignature = await serviceSdk.generateEmailSignature(eventData.email, eventData.userAddress, eventData.tag);
      serverLogger.debug(`Email signature generated: ${emailSignature}`);
  
      serverLogger.debug("Serializing DID to be sent on-chain");
      const didSerialization = await serviceSdk.createDidSerialization(eventData.userAddress, emailSignature, eventData.userAddress);
      serverLogger.debug(`DID serialization as: ${didSerialization}`);
      
      serverLogger.debug("Generating DID Add Attribute Transaction");
      const didCalldata = await serviceSdk.createDidCalldata(eventData.userAddress, eventData.company, didSerialization);
      serverLogger.debug(`Generated DID Add Attribute calldata of: ${didCalldata}`);


    // now only sign with the gas station factory owner
    const ownerSignature = await serviceSdk.ownerSignTypedDataExecuteTransaction(PRECOMPILE_ADDRESS_DID, didCalldata, nonce);


    const data = {
      "target": PRECOMPILE_ADDRESS_DID,
      "calldata": didCalldata,
      "nonce": nonce,
      "ownerSignature": ownerSignature,
    }
    
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Smart Account Storage Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});

// funds a transaction on behalf of the gas station (no need for a machine account signature; just the machine factory signature)
app.post('/execute-tx', async (req, res) => {
  try { 
    const eventData = req.body;

    await serviceSdk.executeTransaction(
      eventData.target,
      eventData.calldata,
      eventData.nonce,
      eventData.ownerSignature
    );


    const data = { "successfully": "executed"}
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Smart Account Storage Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});



// storages being added to the chain from an eoa account being sponsored  
app.post('/generate-smart-account-storage-tx', async (req, res) => {
  try { 
    const eventData = req.body; // Event data sent to the server
    console.log(eventData);
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;


    serverLogger.debug("Generating the Data Storage Key for your item type and tag");
    const response = await serviceSdk.storeDataKey(eventData.email, eventData.itemType, eventData.tag);
    serverLogger.debug(`Successfully created a data key with the response:\n${JSON.stringify(response, null, 2)}`);

    serverLogger.debug("Generating storage Add Item Transaction");
    const storageCalldata = await serviceSdk.createStorageCalldata(eventData.itemType, eventData.item);
    serverLogger.debug(`Generated storage Add Item calldata of: ${storageCalldata}`);

    // // in the case you need to request for user signature
    // // the eoa signature will be constructed with the on-chain data and will be sent to the frontend for the user to sign
    // serverLogger.debug("Generating message for EOA account to sign for transaction approval");
    // const messageToSign = await serviceSdk.generateEoaSignature(eventData.machineAddress, PRECOMPILE_ADDRESS_STORAGE, storageCalldata, eventData.nonce);
    // serverLogger.debug(`Generated message for EOA account to sign: ${messageToSign}`);

    // has access to user private key
    serverLogger.debug("Generating signature from EOA account");
    const machineOwnerSignature = await serviceSdk.generateEoaSignature(eventData.machineAddress, PRECOMPILE_ADDRESS_STORAGE, storageCalldata, nonce);
    serverLogger.debug(`Generated signature from EOA account: ${machineOwnerSignature}`);

    serverLogger.debug("Generating signature for the owner of the Gas Station to give their approval for the machine transaction");
    const ownerSignature = await serviceSdk.generateOwnerSignatureForMachineTx(eventData.machineAddress, PRECOMPILE_ADDRESS_STORAGE, storageCalldata, nonce);
    serverLogger.debug(`Generated signature for the owner: ${ownerSignature}`);

    const data = {
      "machineAddress": eventData.machineAddress,
      "target": PRECOMPILE_ADDRESS_STORAGE,
      "calldata": storageCalldata,
      "nonce": nonce,
      "ownerSignature": ownerSignature,
      "signature": machineOwnerSignature,
    }
    
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Smart Account Storage Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});



// listen for create did transaction data
app.post('/generate-smart-account-create-did-tx', async (req, res) => {
  try {
    const eventData = req.body; // Event data sent to the server
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;

  
    // Create did tx for user eoa on the frontend to sign
    serverLogger.debug("Creating email signature from peaq get-real service endpoint");
    const emailSignature = await serviceSdk.generateEmailSignature(eventData.email, eventData.machineAddress, eventData.tag);
    serverLogger.debug(`Email signature generated: ${emailSignature}`);

    serverLogger.debug("Serializing DID to be sent on-chain");
    const didSerialization = await serviceSdk.createDidSerialization(eventData.eoaAddress, emailSignature, eventData.machineAddress);
    serverLogger.debug(`DID serialization as: ${didSerialization}`);
    
    serverLogger.debug("Generating DID Add Attribute Transaction");
    const didCalldata = await serviceSdk.createDidCalldata(eventData.machineAddress, eventData.company, didSerialization);
    serverLogger.debug(`Generated DID Add Attribute calldata of: ${didCalldata}`);

    // // in the case you need to request for user signature
    // // the eoa signature will be constructed with the on-chain data and will be sent to the frontend for the user to sign
    // serverLogger.debug("Generating message for EOA account to sign for transaction approval");
    // // need to chagne the function a bit below:
    // const messageToSign = await serviceSdk.generateEoaSignature(eventData.machineAddress, PRECOMPILE_ADDRESS_DID, didCalldata, eventData.nonce);
    // serverLogger.debug(`Generated message for EOA account to sign: ${messageToSign}`);

    serverLogger.debug("Generating signature for EOA account of data");
    // in the cases you can sign eoa locally (ob-behalf of user; they gave you access to private keys)
    const machineOwnerSignature = await serviceSdk.generateEoaSignature(eventData.machineAddress, PRECOMPILE_ADDRESS_DID, didCalldata, nonce);
    serverLogger.debug(`Generated signature from EOA account: ${machineOwnerSignature}`);

    serverLogger.debug("Generating signature for the owner of the Gas Station to give their approval for the machine transaction");
    const ownerSignature = await serviceSdk.generateOwnerSignatureForMachineTx(eventData.machineAddress, PRECOMPILE_ADDRESS_DID, didCalldata, nonce);
    serverLogger.debug(`Generated signature for the owner: ${ownerSignature}`);
 
    // is there a place we should store calldata? is sending back too much work?
    const data = {
      "machineAddress": eventData.machineAddress,
      "target": PRECOMPILE_ADDRESS_DID,
      "calldata": didCalldata,
      "nonce": nonce,
      "ownerSignature": ownerSignature,
      "signature": machineOwnerSignature
    }

    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Signup Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }

});

// sends a machine smart account transaction funded by the gas station
app.post('/execute-machine-tx', async (req, res) => {
  try {
    const eventData = req.body;
    console.log(eventData)

    // // eoa will have signed on fronted; this is a mock for backend only example
    // const web3 = new Web3(PEAQ_RPC_URL);
    // const eoaAccount = web3.eth.accounts.privateKeyToAccount(`0x${EOA_PRIVATE_KEY}`);
    // const eoaSignature = serviceSdk.localSign(eoaAccount, eventData.messageToSign);

    serverLogger.debug("Executing Machine Transaction");
    await serviceSdk.executeMachineTransaction(
      eventData.machineAddress,
      eventData.target,
      eventData.calldata,
      eventData.nonce,
      eventData.ownerSignature,
      eventData.signature
    );
    serverLogger.debug("Successfully Executed Machine Transaction");

    const data = { "successfully": "executed"}
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Execute Transaction Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});


// Batch Transactions:
// - Multiple Smart Accounts to send multiple txs per smart contract call
// - Events being generated from different concurrent user/machine requests
app.post('/execute-machine-batch-txs', async (req, res) => {
  try {
    const batchData = req.body;
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;

    const machineAddresses = []
    const targets = []
    const calldata = []
    const machineNonces = []
    const machineOwnerSignatures = []


    for (const tx of batchData) {
      machineAddresses.push(tx.machineAddress);
      targets.push(tx.target);
      calldata.push(tx.calldata);
      machineNonces.push(tx.nonce);
      machineOwnerSignatures.push(tx.signature);
    }


    // machineAddresses, targets, data, nonce, machineNonces
    const ownerSignature = await serviceSdk.ownerSignTypedDataExecuteMachineBatchTransaction(machineAddresses, targets, calldata, nonce, machineNonces)

    // machineAddresses, targets, calldata, nonce, machineNonces, ownerSignature, machineOwnerSignatures
    await serviceSdk.executeMachineBatchTransactions(
      machineAddresses,
      targets,
      calldata,
      nonce,
      machineNonces,
      ownerSignature,
      machineOwnerSignatures
    )

    const data = { "successfully": "executed"}
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Execute Transaction Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});


app.post('/execute-machine-transfer-balance', async (req, res) => {
  try {
    const eventData = req.body;
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1;

    const machineOwnerSignature = await serviceSdk.machineSignTypedDataTransferMachineBalance(eventData.machineAddress, eventData.recipientAddress, nonce)

    const ownerSignature = await serviceSdk.ownerSignTypedDataExecuteMachineTransferBalance(eventData.machineAddress, eventData.recipientAddress, nonce);
    await serviceSdk.executeMachineTransferBalance(
      eventData.machineAddress, 
      eventData.recipientAddress,
      nonce,
      ownerSignature,
      machineOwnerSignature
    );

    const data = { "successfully": "executed"}
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
      serverLogger.error(`Execute Transaction Error: ${error}\n${error.stack}`);
      res.status(500).json({ success: false, error: error.message });
    }
  });


// Start the server
app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});
