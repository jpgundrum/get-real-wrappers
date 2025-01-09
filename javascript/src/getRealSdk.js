import fs from 'fs';
import path from 'path';

import { AbiCoder, ethers } from 'ethers'
import Web3 from 'web3';
import { hexToU8a } from '@polkadot/util';
import axios from 'axios';
import { fileURLToPath } from 'url';
import { sdkLogger } from '../logs/logger.js'

import { Sdk } from "@peaq-network/sdk";
import * as peaqDidProto from 'peaq-did-proto-js';

// Constants
const ABI_GAS_STATION = 'gas_station_abi';

const abiCache = {};
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// only set network specific properties in the initialization function
export class getRealSdk {
    constructor(rpcUrl, peaqServiceUrl, serviceApiKey, projectApiKey, gasStationAddress, gasStationPrivate) {
        // Initialize web3
        this.web3 = new Web3(rpcUrl); // Replace with your Ethereum node URL

        // Set class properties
        this.peaqServiceUrl = peaqServiceUrl;
        this.serviceApiKey = serviceApiKey;
        this.projectApiKey = projectApiKey;
        this.gasStationAddress = gasStationAddress;

        // Create wallet for transactions
        this.owner = this.web3.eth.accounts.privateKeyToAccount(`0x${gasStationPrivate}`);
        // this.web3.eth.accounts.wallet.add(this.owner);

        // Load Gas Station ABI and create contract instance
        const gasStationAbi = this._loadAbi(ABI_GAS_STATION);
        this.gasStationContract = new this.web3.eth.Contract(gasStationAbi, gasStationAddress);
    }

    generateOwnerDeploySignature(eoa, nonce) {
        try {
            sdkLogger.debug(`Generating Gas Station Owner Signature...`);
            const deployMessageHash =  ethers.solidityPackedKeccak256(
                ["address", "address", "uint256"],
                [this.gasStationAddress, eoa, nonce]
            );
        
            const signature = this.owner.sign(deployMessageHash).signature;
            sdkLogger.debug(`Gas Station owner signature for deployment: ${signature}`);
            return signature
        } catch (error) {
            sdkLogger.error(`Error generating owner deployment signature: ${error}`);
            throw error;
        }
    }

    // ADD NonceAlreadyUsed() to this tx in Smart contract for verbose loggings
    async deployMachineSmartAccount(eoa, nonce, signature) {
        try {
            const methodData = this.gasStationContract.methods
                .deployMachineSmartAccount(eoa, nonce, signature)
                .encodeABI();
            sdkLogger.debug(`Deploying Machine Smart Account on behalf of\neoa account: ${eoa}\nnonce: ${nonce}\ndeployer signature: ${signature}`);
            
            
            const receipt = await this._sendTransaction(methodData, 900000);

            const eventSignature = this.web3.utils.keccak256('MachineSmartAccountDeployed(address)');
            for (const log of receipt.logs) {
                if (log.topics[0] === eventSignature && log.topics.length > 1) {
                    const machineAddress = this.web3.utils.toChecksumAddress(`0x${log.topics[1].slice(26)}`);
                    sdkLogger.debug(`Successfully Deployed Machine Smart Account address: ${machineAddress}`);
                    return machineAddress;
                }
            }
            throw new Error('MachineSmartAccountDeployed event not found in logs');
        } catch (error) {
            sdkLogger.error(`Error deploying machine smart account: ${error}`);
            throw error;
        }
    }

    async generateEmailSignature(email, machineAddress, tag) {
        try {
            const data = { email, did_address: machineAddress, tag };
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'APIKEY': this.serviceApiKey,
                'P-APIKEY': this.projectApiKey
            };
            sdkLogger.debug(`Sending email signature to get-real service:\nData: ${JSON.stringify(data, null, 2)}`);
            const response = await axios.post(`${this.peaqServiceUrl}/v1/sign`, data, { headers });
            sdkLogger.debug(`Email signature generated: ${response.data.data.signature}`);
            return response.data.data.signature;
        } catch (error) {
            sdkLogger.error('Error generating email signature:', error);
            throw error;
        }
    }

    async createDidSerialization(eoaAddress, emailSignature, machineAddress) {
        try {
            // generate custom fields for DID Document
            const customFields = {
                services: [
                {
                    id: '#emailSignature',
                    type: 'emailSignature',
                    data: emailSignature
                },
                {
                    id: '#owner',
                    type: 'owner',
                    data: eoaAddress
                },
              ]
            }

            const didSerialization = (await Sdk.generateDidDocument({address: machineAddress, customDocumentFields: customFields})).value;
            sdkLogger.debug(`DID serialization as: ${didSerialization}`);
            await this._didReadable(didSerialization);
            return didSerialization

        } catch (error) {
            sdkLogger.error('Error serializing the DID: ', error);
            throw error;
        }
    }

    async createDidCalldata(machineAddress, company, didSerialization) {
        try {
            // create function signatuare
            const abiCoder = new AbiCoder();

            const addAttributeFunctionSignature = "addAttribute(address,bytes,bytes,uint32)";
            const createDidFunctionSelector = ethers.keccak256(ethers.toUtf8Bytes(addAttributeFunctionSignature)).substring(0, 10);  

            const nameString = `did:peaq:${machineAddress}#${company}` // format used for dune analytics
            const nameBytes = ethers.hexlify(ethers.toUtf8Bytes(nameString));
            const valueBytes = ethers.hexlify(ethers.toUtf8Bytes(didSerialization));
            const validityFor = 0;
            

            const params = abiCoder.encode(
                ["address", "bytes", "bytes", "uint32"],
                [machineAddress, nameBytes, valueBytes, validityFor]
            );

            const calldata = params.replace("0x", createDidFunctionSelector);
            sdkLogger.debug(`Calldata tx for the addAttribute precompile with name ${nameString} at address ${machineAddress} is ${calldata}`);
            return calldata;
        } catch (error){
            sdkLogger.error('Error creating DID calldata:', error);
            throw error;
        }
    }

    async generateEoaSignature(machineAddress, target, calldata, nonce) {
        try {
            const eoaMessageHash =  ethers.solidityPackedKeccak256(
                ["address", "address", "bytes", "uint256"],
                [machineAddress, target, calldata, nonce]
              );
            sdkLogger.debug(`EOA Message Hash created: ${eoaMessageHash}`);
            return eoaMessageHash;
        } catch (error) {
            sdkLogger.error('Error generating the eoa signature:', error);
            throw error;
        }
    }

    async generateOwnerSignatureForMachineTx(eoaAddress, target, calldata, nonce){
        try {
            const messageHash =  ethers.solidityPackedKeccak256(
                ["address", "address", "address", "bytes", "uint256"],
                [this.gasStationAddress, eoaAddress, target, calldata, nonce]
            );
            // can directly sign because we are the owner of the gas station
            const signature = this.owner.sign(messageHash).signature;
            sdkLogger.debug(`Owner Signature for Machine Tx generated: ${signature}`);
            return signature
        } catch (error) {
            sdkLogger.error('Error generating the eoa signature:', error);
            throw error;
        }
    }

    async executeMachineTransaction(eoaAddress, machineAddress, target, calldata, nonce, ownerSignature, eoaSignature){
        try {

            // const methodData = this.gasStationContract.methods
            // .deployMachineSmartAccount(eoa, nonce, signature)
            // .encodeABI();

            const methodData = this.gasStationContract.methods
                .executeMachineTransaction(eoaAddress, machineAddress, target, calldata, nonce, ownerSignature, eoaSignature)
                .encodeABI();
            sdkLogger.debug(`Executing Machine Transaction on behalf of\neoa address: ${eoaAddress}\nmachine address: ${machineAddress}\ntarget precompile: ${target}\ncalldata: ${calldata}\nowner signature: ${ownerSignature}\neoa signature: ${eoaSignature}`);

            const receipt = await this._sendTransaction(methodData, 900000);
            sdkLogger.debug(`Successfully Executed Machine Transaction.`);
        } catch (error) {
            sdkLogger.error('Error generating the eoa signature:', error);
            throw error;
        }
    }

    async storeDataKey(email, itemType, tag) {
        try {
            const data = { email, item_type: itemType, tag };
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'APIKEY': this.serviceApiKey,
                'P-APIKEY': this.projectApiKey
            };
            sdkLogger.debug(`Sending data key to get-real service:\nData: ${JSON.stringify(data, null, 2)}`);
            const response = await axios.post(`${this.peaqServiceUrl}/v1/data/store`, data, { headers });
            sdkLogger.debug(`Response from storing data key: ${JSON.stringify(response.data, null, 2)}`);
            return response.data;
        } catch (error) {
            sdkLogger.error('Error storing data key:', error);
            throw error;
        }
    }

    async createStorageCalldata(itemType, item) {
        try {
            const abiCoder = new AbiCoder()
    
            const addItemFunctionSignature = "addItem(bytes,bytes)";
            const addItemFunctionSelector = ethers.keccak256(ethers.toUtf8Bytes(addItemFunctionSignature)).substring(0, 10);
    
            const itemTypeHex = ethers.hexlify(ethers.toUtf8Bytes(itemType));
            const itemHex = ethers.hexlify(ethers.toUtf8Bytes(item));
    
            const params = abiCoder.encode(
                ["bytes", "bytes"],
                [itemTypeHex, itemHex]
            );
            
            const calldata = params.replace("0x", addItemFunctionSelector);
            sdkLogger.debug(`Calldata tx for the AddItem precompile with itemType ${itemType} and item ${item} is ${calldata}`);
            return calldata
        } catch (error) {
            sdkLogger.error('Error creating storage calldata:', error);
            throw error;
        }
    }

    async _sendTransaction(methodData, gas) {
        try { 
            // // SHOULD WE ESTIMATE??? It is sometimes not enough
            // const gasEstimate = await this.web3.eth.estimateGas(methodData);
            // console.log(gasEstimate);

            const gasPrice = await this.web3.eth.getGasPrice();
            // const nonce = await this.web3.eth.getTransactionCount(this.owner.address);

            // TODO -> what is the best way to send the transaction (concerning gas)
            const tx = {
                from: this.owner.address,
                to: this.gasStationAddress,
                gas: gas,
                gasPrice: gasPrice,
                data: methodData,
            };
            const signedTx = await this.owner.signTransaction(tx);
            if (!signedTx.rawTransaction) {
                throw new Error('Failed to sign transaction');
            }
            const receipt = await this.web3.eth.sendSignedTransaction(signedTx.rawTransaction);
            sdkLogger.debug(`Transaction receipt: ${JSON.stringify(receipt, (key, value) =>
                typeof value === 'bigint' ? value.toString() : value
            , 2)}`);
            return receipt;
        } catch (error) {
            // still working on verbose loggings
            sdkLogger.error(`Error sending the transaction ${methodData}\nError Message: ${error.message}`);
            sdkLogger.error(`Stack Trace: ${error.stack}`);

            // Log additional properties, if available
            if (error.receipt) {
                sdkLogger.error(`Transaction Receipt: ${JSON.stringify(error.receipt, null, 2)}`);
            }
            if (error.data) {
                sdkLogger.error(`Error Data: ${JSON.stringify(error.data, null, 2)}`);
            }
            if (error.reason) {
                sdkLogger.error(`Revert Reason: ${error.reason}`);
            }
            throw error;
        }
    }

    async _didReadable(didSerialization) {
        try {
            const document = peaqDidProto.default.Document.deserializeBinary(hexToU8a(didSerialization));
            sdkLogger.debug(`Sending DID Document to chain: \n${JSON.stringify(document.toObject(), null, 2)}`);
        } catch (error){
            sdkLogger.error('Error logging the readable DID Document:', error);
            throw error;
        }
    }
    // used to mock a frontend signature from a eoa account
    localSign(eoaAccount, messageToSign) {
        try {
            return eoaAccount.sign(messageToSign).signature;
        } catch (error){
            sdkLogger.error('Error logging the readable DID Document:', error);
            throw error;
        }
    }
    _encodePacked(types, values) {
        return this.web3.eth.abi.encodeParameters(types, values);
    }

    _loadAbi(filename) {
        if (!abiCache[filename]) {
            const abiPath = path.resolve(__dirname, `../abi/${filename}.json`);
            abiCache[filename] = JSON.parse(fs.readFileSync(abiPath, 'utf8')).output.abi;
        }
        return abiCache[filename];
    }
}
