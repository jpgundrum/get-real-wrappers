import express from 'express';
import bodyParser from 'body-parser';
import cors from 'cors';
import { getRealSdk } from './getRealSdk.js';
import dotenv from 'dotenv';

import Web3 from 'web3'; // only used to mock eoa signature

dotenv.config();

import { serverLogger } from '../logs/logger.js';

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

// Initialize getRealSdk. TODO how to do this with multiple gas stations??
const serviceSdk = new getRealSdk(PEAQ_RPC_URL, PEAQ_SERVICE_URL, SERVICE_API_KEY, PROJECT_API_KEY, GAS_STATION_ADDRESS, GAS_STATION_OWNER_PRIVATE_KEY);

const app = express();
const port = 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());


// listen for machine smart account creation
app.post('/create-smart-account', async (req, res) => {
  try {
    const eventData = req.body; // Event data sent to the server
    const nonce = Math.floor(Math.random() * 1_000_000_000) + 1; // TODO better logic for nonce

    // Deployment signature used to confirm eoa requested the smart account creation
    serverLogger.debug("Requesting Gas Station Owner Deployment Signature");
    const deploySignature = serviceSdk.generateOwnerDeploySignature(eventData.eoaAddress, nonce);

    serverLogger.debug("Deploying Machine Smart Account");
    const machineAddress = await serviceSdk.deployMachineSmartAccount(eventData.eoaAddress, nonce, deploySignature);
    serverLogger.debug(`Machine Smart Account deployed with address ${machineAddress}`);

    const data = {
      "eoaAddress": eventData.eoaAddress,
      "machineAddress": machineAddress,
      "nonce": nonce + 1, // increment by 1 after executing a transaction
      "deploymentStatus": {success: true}
    }
    res.status(200).json({ success: true, payload: data });

  } catch (error) {
    serverLogger.error(`Signup Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});


// storages being added to the chain from an eoa account being sponsored  
app.post('/create-storage', async (req, res) => {
  try { 
    const eventData = req.body; // Event data sent to the server

    serverLogger.debug("Generating the Data Storage Key for your item type and tag");
    const response = await serviceSdk.storeDataKey(eventData.email, eventData.itemType, eventData.tag);
    serverLogger.debug(`Successfully created a data key with the response:\n${JSON.stringify(response, null, 2)}`);

    serverLogger.debug("Generating storage Add Item Transaction");
    const storageCalldata = await serviceSdk.createStorageCalldata(eventData.itemType, eventData.tag);
    serverLogger.debug(`Generated storage Add Item calldata of: ${storageCalldata}`);


    serverLogger.debug("Generating message for EOA account to sign for transaction approval");
    const messageToSign = await serviceSdk.generateEoaSignature(eventData.machineAddress, PRECOMPILE_ADDRESS_STORAGE, storageCalldata, eventData.nonce);
    serverLogger.debug(`Generated message for EOA account to sign: ${messageToSign}`);

    serverLogger.debug("Generating signature for the owner of the Gas Station to give their approval for the machine transaction");
    const ownerSignature = await serviceSdk.generateOwnerSignatureForMachineTx(eventData.eoaAddress, PRECOMPILE_ADDRESS_STORAGE, storageCalldata, eventData.nonce);
    serverLogger.debug(`Generated signature for the owner: ${ownerSignature}`);

    const data = {
      "eoaAddress": eventData.eoaAddress,
      "machineAddress": eventData.machineAddress,
      "target": PRECOMPILE_ADDRESS_STORAGE,
      "messageToSign": messageToSign,
      "ownerSignature": ownerSignature,
      "calldata": storageCalldata,
      "nonce": eventData.nonce
    }
    
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Signup Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});

// listen for create did transaction data
app.post('/create-did', async (req, res) => {
  try {
    const eventData = req.body; // Event data sent to the server
  
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

    // the eoa signature will be constructed with the on-chain data and will be sent to the frontend for the user to sign
    serverLogger.debug("Generating message for EOA account to sign for transaction approval");
    const messageToSign = await serviceSdk.generateEoaSignature(eventData.machineAddress, PRECOMPILE_ADDRESS_DID, didCalldata, eventData.nonce);
    serverLogger.debug(`Generated message for EOA account to sign: ${messageToSign}`);

    serverLogger.debug("Generating signature for the owner of the Gas Station to give their approval for the machine transaction");
    const ownerSignature = await serviceSdk.generateOwnerSignatureForMachineTx(eventData.eoaAddress, PRECOMPILE_ADDRESS_DID, didCalldata, eventData.nonce);
    serverLogger.debug(`Generated signature for the owner: ${ownerSignature}`);

 
    // is there a place we should store calldata? is sending back too much work?
    const data = {
      "eoaAddress": eventData.eoaAddress,
      "machineAddress": eventData.machineAddress,
      "target": PRECOMPILE_ADDRESS_DID,
      "messageToSign": messageToSign,
      "ownerSignature": ownerSignature,
      "calldata": didCalldata,
      "nonce": eventData.nonce
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

    // eoa will have signed on fronted; this is a mock for backend only example
    const web3 = new Web3(PEAQ_RPC_URL);
    const eoaAccount = web3.eth.accounts.privateKeyToAccount(`0x${EOA_PRIVATE_KEY}`);
    const eoaSignature = serviceSdk.localSign(eoaAccount, eventData.messageToSign);

    serverLogger.debug("Executing Machine Transaction");
    await serviceSdk.executeMachineTransaction(
      eventData.eoaAddress,
      eventData.machineAddress,
      eventData.target,
      eventData.calldata,
      eventData.nonce,
      eventData.ownerSignature,
      eoaSignature
    );
    serverLogger.debug("Successfully Executed Machine Transaction");

    const nonce = eventData.nonce + 1 // increment by 1 after executing a transaction
    const data = {"nonce": nonce}
    res.status(200).json({ success: true, payload: data });
  } catch (error) {
    serverLogger.error(`Execute Transaction Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});

// generate owner deployment signature
//
// signature is used to perform operations such as deployMachineSmartAccount(), transferGasStationBalance(), executeTransaction(), & executeMachineTransaction()
app.post('/create-owner-signature', async (req, res) => {
  try {
    const eventData = req.body; // Event data sent to the server

    serverLogger.debug("Requesting Gas Station Owner Deployment Signature");
    const deploy_signature = serviceSdk.generateOwnerDeploySignature(eventData.eoaAddress, nonce);

  } catch (error) {
    serverLogger.error(`Owner Signature Error: ${error}\n${error.stack}`);
    res.status(500).json({ success: false, error: error.message });
  }
});


// Send nonce (per gas station smart contract)


// Send tx to sign


// Event listener endpoints


// Start the server
app.listen(port, () => {
  console.log(`Server is running on http://localhost:${port}`);
});
