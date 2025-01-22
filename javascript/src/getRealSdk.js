import fs from 'fs';
import path from 'path';

import { AbiCoder, ethers, NonceManager } from 'ethers'
// import Web3 from 'web3';
import { hexToU8a } from '@polkadot/util';
import axios from 'axios';
import { fileURLToPath } from 'url';
import { sdkLogger } from '../logs/logger.js'

import { Sdk } from "@peaq-network/sdk";
import * as peaqDidProto from 'peaq-did-proto-js';

// Constants
// const ABI_GAS_STATION = 'gas_station_abi';
const abiCache = {};
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const abiPath = path.resolve(__dirname, '../abi/gas_station_abi.json');
const MyContractABI = JSON.parse(fs.readFileSync(abiPath, 'utf-8'));

/**
 * Class that abstracts away implements peaq's Get-Real Service, Gas Station Payment System, and signature generation.
 * 
 */
export class getRealSdk {
    constructor(rpcUrl, chainID, peaqServiceUrl, serviceApiKey, projectApiKey, gasStationAddress, gasStationOwnerPrivate, eoaPrivate) {
        // Initialize ethers
        this.provider = new ethers.JsonRpcProvider(rpcUrl);
        this.chainID = chainID;


        // Set class properties
        this.peaqServiceUrl = peaqServiceUrl;
        this.serviceApiKey = serviceApiKey;
        this.projectApiKey = projectApiKey;
        this.gasStationAddress = gasStationAddress;

        // Create wallet for transactions
        this.ownerAccount = new ethers.Wallet(gasStationOwnerPrivate, this.provider);
        this.eoaAccount = new ethers.Wallet(eoaPrivate, this.provider);


        // Load Gas Station ABI and create contract instance
        // const gasStationAbi = this._loadAbi(ABI_GAS_STATION);
        // const gasStationAbi = new ethers.ContractFactory(MyContractABI, this.gasStationAddress);

        this.gasStationContract = new ethers.ContractFactory(MyContractABI.abi, this.gasStationAddress);
    }

    /**
     * Generates a signature to prove the owner of a smart account. 
     * The gas station contract owner signs an address that will be the owner of the 
     * be deployed machine smart account.
     * 
     * @param {string} eoaAddress - Owner of the Smart Account.
     * @param {number} nonce - Unique identifier to prevent reply attacks.
     * @returns {string} The signature of approval provided by the gas station owner.
     */
    async ownerSignTypedDataDeployMachineSmartAccount(eoaAddress, nonce) {
        try {
            const domain = {
                name: "MachineStationFactory",
                version: "1",
                chainId: this.chainID,
                verifyingContract: this.gasStationAddress,
            };
            
            const types = {
                DeployMachineSmartAccount: [
                { name: "machineOwner", type: "address" },
                { name: "nonce", type: "uint256" },
                ],
            };
            
            const message = {
                machineOwner: eoaAddress,
                nonce: nonce
            };
            
            const signature = await this.ownerAccount.signTypedData(domain, types, message);
            console.log(signature);
            return signature;
        } catch (error) {
            sdkLogger.error(`Error generating owner deployment signature: ${error}`);
            throw error;
        }
    }

    /**
     * Executes the gas station contract function that deploys a new smart account. The smart contract
     * uses the signature passed to see if the gas station owner account gave its approval for this action.
     * 
     * @param {string} eoaAddress - Owner of the Smart Account.
     * @param {number} nonce - Unique identifier to prevent reply attacks.
     * @param {number} signature - Signature of approval by the gas station owner that the eoaAddress can create a new Smart Account.
     * @returns {string} - The address of the newly created Smart Account.
     */
    async deployMachineSmartAccount(eoaAddress, nonce, signature) {
        try {
            const methodData = this.gasStationContract.interface.encodeFunctionData(
                "deployMachineSmartAccount",
                [eoaAddress, nonce, signature]
            );
            sdkLogger.debug(`Deploying Machine Smart Account on behalf of\neoa account: ${eoaAddress}\nnonce: ${nonce}\ndeployer signature: ${signature}`);

            const receipt = await this._sendTransaction(methodData);

            const eventSignature = ethers.id("MachineSmartAccountDeployed(address)");
            for (const log of receipt.logs) {
                if (log.topics[0] === eventSignature && log.topics.length > 1) {
                    const smartAddress = ethers.getAddress(`0x${log.topics[1].slice(26)}`);
                    sdkLogger.debug(`Successfully Deployed Machine Smart Account address: ${smartAddress}`);
                    return smartAddress;
                }
            }
            throw new Error('MachineSmartAccountDeployed event not found in logs');
        } catch (error) {
            sdkLogger.error(`Error deploying machine smart account: ${error}`);
            throw error;
        }
    }

    async ownerSignTypedDataTransferMachineStationBalance(newMachineStationAddress, nonce) {
        try {
            const domain = {
                name: "MachineStationFactory",
                version: "1",
                chainId: this.chainID,
                verifyingContract: this.gasStationAddress,
            };
            
            const types = {
                TransferMachineStationBalance: [
                { name: "newMachineStationAddress", type: "address" },
                { name: "nonce", type: "uint256" },
                ],
            };
            
            const message = {
                newMachineStationAddress: newMachineStationAddress,
                nonce: nonce
            };
            
            const signature = await this.ownerAccount.signTypedData(domain, types, message);
            return signature;
        } catch (error) {
            sdkLogger.error(`Error generating owner Transfer Machine Station Balance signature: ${error}`);
            throw error;
        }
    }

    async transferMachineStationBalance(newMachineStationAddress, nonce, signature) {
        try {
            const methodData = this.gasStationContract.interface.encodeFunctionData(
                "transferMachineStationBalance",
                [newMachineStationAddress, nonce, signature]
            );
            sdkLogger.debug(`Transferring Machine StationBalance...`);
            const receipt = await this._sendTransaction(methodData);
        } catch (error) {
            sdkLogger.error(`Error Transferrring Machine Station Balance: ${error}`);
            throw error;
        }
    }

    async ownerSignTypedDataExecuteTransaction(target, calldata, nonce) {
        try {
            const domain = {
                name: "MachineStationFactory",
                version: "1",
                chainId: this.chainID,
                verifyingContract: this.gasStationAddress,
            };
            
            const types = {
                ExecuteTransaction: [
                { name: "target", type: "address" },
                { name: "data", type: "bytes" },
                { name: "nonce", type: "uint256" },
                ],
            };
            
            const message = {
                target: target,
                data: calldata,
                nonce: nonce
            };
            
            const signature = await this.ownerAccount.signTypedData(domain, types, message);
            return signature;
        } catch (error) {
            sdkLogger.error(`Error generating owner Transfer Machine Station Balance signature: ${error}`);
            throw error;
        }
    }

    async executeTransaction(target, calldata, nonce, ownerSignature) {
        try {
            console.log(target)
            console.log(calldata)
            console.log(nonce)
            console.log(ownerSignature)

            const methodData = this.gasStationContract.interface.encodeFunctionData(
                "executeTransaction",
                [target, calldata, nonce, ownerSignature]
            );
            sdkLogger.debug(`Executing Gas Station Transaction:\ntarget precompile: ${target}\ncalldata: ${calldata}\nonce: ${nonce}\nowner signature: ${ownerSignature}`);

            await this._sendTransaction(methodData);
            sdkLogger.debug(`Successfully Executed Machine Transaction.`);
        } catch (error) {
            sdkLogger.error('Error executing the transaction:', error);
            throw error;
        }
    }



    /**
     * Get-Real Service endpoint action that generates an email signature based on an email, address, and tag.
     * Used to verify a user/machine at that email has this address for the tag.
     * 
     * @param {string} email - Email of the end-user/machine who will create a new identity.
     * @param {string} eoaAddress - The end-user/machine wallet address.
     * @param {string} tag - Unique identifier used in get-real verification.
     * @returns {string} - The signature of the posted data to be added to DID Document for verification.
     */
    async generateEmailSignature(email, eoaAddress, tag) {
        try {
            const data = { email, did_address: eoaAddress, tag };
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

    /**
     * Serializes the DID Document of the smart account to be stored on chain. Specifically, creates the document to store the
     * email signature of the get-real user and links their externally owner account (eoa) to the smart account document.
     * 
     * @param {string} eoaAddress - Email of the end-user/machine who will create a new identity.
     * @param {string} emailSignature - The get-real generated signature for email verification.
     * @param {string} smartAddress - The address of the smart account the eoa account owns. 
     * @returns {string} - The signature of the posted data to be added to DID Document for verification.
     */
    async createDidSerialization(eoaAddress, emailSignature, smartAddress) {
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

            const didSerialization = (await Sdk.generateDidDocument({address: smartAddress, customDocumentFields: customFields})).value;
            sdkLogger.debug(`DID serialization as: ${didSerialization}`);
            await this._didReadable(didSerialization);
            return didSerialization

        } catch (error) {
            sdkLogger.error('Error serializing the DID: ', error);
            throw error;
        }
    }
        
    /**
     * Generates the hexadecimal data that represents an AddAttribute peaq pallet execution.
     * 
     * @param {string} smartAddress - Address of the generated smart account.
     * @param {string} company - Unique identifier used to track total machines/users in Dune for each DePIN.
     * @param {string} serializedDID - The string of serialized DID data.
     * @returns {string} - The properly constructed calldata to perform an AddAttribute peaq precompile operation.
     */
    async createDidCalldata(smartAddress, company, serializedDID) {
        try {
            const abiCoder = new AbiCoder();

            const addAttributeFunctionSignature = "addAttribute(address,bytes,bytes,uint32)";
            const createDidFunctionSelector = ethers.keccak256(ethers.toUtf8Bytes(addAttributeFunctionSignature)).substring(0, 10);  

            const nameString = `did:peaq:${smartAddress}#${company}` // format used for dune analytics
            const nameBytes = ethers.hexlify(ethers.toUtf8Bytes(nameString));
            const valueBytes = ethers.hexlify(ethers.toUtf8Bytes(serializedDID));
            const validityFor = 0;

            const params = abiCoder.encode(
                ["address", "bytes", "bytes", "uint32"],
                [smartAddress, nameBytes, valueBytes, validityFor]
            );

            const calldata = params.replace("0x", createDidFunctionSelector);
            sdkLogger.debug(`Calldata tx for the addAttribute precompile with name ${nameString} at address ${smartAddress} is ${calldata}`);
            return calldata;
        } catch (error){
            sdkLogger.error('Error creating DID calldata:', error);
            throw error;
        }
    }

    /**
     * Generates a signature to prove the eoa address owns that smart account. 
     * The gas station contract owner signs an address that will be the owner of the 
     * be deployed machine smart account.
     * 
     * @param {string} eoaAddress - Owner of the Smart Account.
     * @param {number} nonce - Unique identifier to prevent reply attacks.
     * @returns {string} The signature of approval provided by the gas station owner.
     */
    async generateEoaSignature(machineAddress, target, calldata, nonce) {
        try {
            const domain = {
                name: "MachineSmartAccount", 
                version: "1", 
                chainId: this.chainID,
                verifyingContract: machineAddress,
              };
            
            const types = {
                Execute: [
                    { name: "target", type: "address" },
                    { name: "data", type: "bytes" },
                    { name: "nonce", type: "uint256" },
                ],
            };
        
            const message = {
                target: target,
                data: calldata,
                nonce: nonce,
            };
        /// TODO THE USER EOA MUST SIGN HERE...
            const signature = await this.eoaAccount.signTypedData(domain, types, message);
            // sdkLogger.debug(`EOA Message Signature created: ${signature}`);
            return signature;
        } catch (error) {
            sdkLogger.error('Error generating the eoa signature:', error);
            throw error;
        }
    }

    async generateOwnerSignatureForMachineTx(machineAddress, target, calldata, nonce){
        try {
            const domain = {
                name: "MachineStationFactory", 
                version: "1", 
                chainId: this.chainID,
                verifyingContract: this.gasStationAddress,
              };
            
              const types = {
                ExecuteMachineTransaction: [
                  { name: "machineAddress", type: "address" },
                  { name: "target", type: "address" },
                  { name: "data", type: "bytes" },
                  { name: "nonce", type: "uint256" },
                ],
              };
          
              const message = {
                machineAddress: machineAddress,
                target: target,
                data: calldata,
                nonce: nonce,
              };
            
              const signature = await this.ownerAccount.signTypedData(domain, types, message);
              return signature;
            // const messageHash =  ethers.solidityPackedKeccak256(
            //     ["address", "address", "address", "bytes", "uint256"],
            //     [this.gasStationAddress, eoaAddress, target, calldata, nonce]
            // );
            // // can directly sign because we are the owner of the gas station
            // const signature = this.owner.sign(messageHash).signature;
            // sdkLogger.debug(`Owner Signature for Machine Tx generated: ${signature}`);
            // return signature
        } catch (error) {
            sdkLogger.error('Error generating the owner signature:', error);
            throw error;
        }
    }

    async ownerSignTypedDataExecuteMachineBatchTransaction(machineAddresses, targets, calldata, nonce, machineNonces) {
        try {
            const domain = {
                name: "MachineStationFactory",
                version: "1",
                chainId: this.chainID,
                verifyingContract: this.gasStationAddress,
            };
            
            const types = {
                ExecuteMachineBatchTransactions: [
                { name: "machineAddresses", type: "address[]" },
                { name: "targets", type: "address[]" },
                { name: "data", type: "bytes[]" },
                { name: "nonce", type: "uint256" },
                { name: "machineNonces", type: "uint256[]" }
                ],
            };
            
            const message = {
                machineAddresses: machineAddresses,
                targets: targets,
                data: calldata,
                nonce: nonce,
                machineNonces: machineNonces
            };
            
            const signature = await this.ownerAccount.signTypedData(domain, types, message);
            return signature;
        } catch (error) {
            sdkLogger.error(`Error generating owner Transfer Machine Station Balance signature: ${error}`);
            throw error;
        }
    }


    async machineSignTypedDataTransferMachineBalance(machineAddress, recipientAddress, nonce) {
        try {
            const domain = {
                name: "MachineSmartAccount",
                version: "1",
                chainId: this.chainID,
                verifyingContract: machineAddress,
            };
            
            const types = {
                TransferMachineBalance: [
                { name: "recipientAddress", type: "address" },
                { name: "nonce", type: "uint256" }
                ],
            };
            
            const message = {
                recipientAddress: recipientAddress,
                nonce: nonce
            };
            // HOW CAN I SIGN WITH THE MACHINE SMART ACCOUNT??
            const signature = await this.eoaAccount.signTypedData(domain, types, message);
            return signature;
        } catch (error) {
            sdkLogger.error(`Error generating owner Transfer Machine Station Balance signature: ${error}`);
            throw error;
        }
    }

    async ownerSignTypedDataExecuteMachineTransferBalance(machineAddress, recipientAddress, nonce) {
        try {
            const domain = {
                name: "MachineStationFactory",
                version: "1",
                chainId: this.chainID,
                verifyingContract: this.gasStationAddress,
            };
            const types = {
                ExecuteMachineTransferBalance: [
                { name: "machineAddress", type: "address" },
                { name: "recipientAddress", type: "address" },
                { name: "nonce", type: "uint256" }
                ],
            };
            const message = {
                machineAddress: machineAddress,
                recipientAddress: recipientAddress,
                nonce: nonce
            };
            const signature = await this.ownerAccount.signTypedData(domain, types, message);
            return signature;
        } catch (error) {
            sdkLogger.error(`Error generating owner Transfer Machine Station Balance signature: ${error}`);
            throw error;
        }
    }


    async executeMachineTransaction(machineAddress, target, calldata, nonce, ownerSignature, eoaSignature){
        try {
            const methodData = this.gasStationContract.interface.encodeFunctionData(
                "executeMachineTransaction",
                [machineAddress, target, calldata, nonce, ownerSignature, eoaSignature]
            );
            
            sdkLogger.debug(`Executing Machine Transaction on behalf of\nmachine address: ${machineAddress}\ntarget precompile: ${target}\ncalldata: ${calldata}\nowner signature: ${ownerSignature}\neoa signature: ${eoaSignature}`);

            await this._sendTransaction(methodData);
            sdkLogger.debug(`Successfully Executed Machine Transaction.`);
        } catch (error) {
            sdkLogger.error('Error executing the machine transaction:', error);
            throw error;
        }
    }


    async executeMachineBatchTransactions(machineAddresses, targets, calldata, nonce, machineNonces, ownerSignature, machineOwnerSignatures){
        try {
            const methodData = this.gasStationContract.interface.encodeFunctionData(
                "executeMachineBatchTransactions",
                [machineAddresses, targets, calldata, nonce, machineNonces, ownerSignature, machineOwnerSignatures]
            );
            await this._sendTransaction(methodData);
            sdkLogger.debug(`Successfully Executed Machine Transaction.`);
        } catch (error) {
            sdkLogger.error('Error executing the machine transaction:', error);
            throw error;
        }
    }

    async executeMachineTransferBalance(machineAddress, recipientAddress, nonce, ownerSignature, machineOwnerSignature){
        try {
            const methodData = this.gasStationContract.interface.encodeFunctionData(
                "executeMachineTransferBalance",
                [machineAddress, recipientAddress, nonce, ownerSignature, machineOwnerSignature]
            );
            await this._sendTransaction(methodData);
            sdkLogger.debug(`Successfully Executed Machine Transaction.`);
        } catch (error) {
            sdkLogger.error('Error executing the machine transaction:', error);
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
            console.log(calldata);
            sdkLogger.debug(`Calldata tx for the AddItem precompile with itemType ${itemType} and item ${item} is ${calldata}`);
            return calldata
        } catch (error) {
            sdkLogger.error('Error creating storage calldata:', error);
            throw error;
        }
    }

    async _sendTransaction(methodData) {
        try {
            const tx = {
                to: this.gasStationAddress,
                data: methodData,
              };

            const txResponse = await this.ownerAccount.sendTransaction(tx)
            let receipt = await txResponse.wait().finally();
            
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
            abiCache[filename] = JSON.parse(fs.readFileSync(abiPath, 'utf8'));
        }
        return abiCache[filename];
    }
}
