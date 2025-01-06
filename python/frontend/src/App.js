// import { useState } from 'react';
// import { ethers } from 'ethers';
// import {Helmet} from "react-helmet";
// import axios from 'axios';
// //import logo from './logo.svg';
// import './App.css'; // imports css styles

// import image from './peaq_logo.png'

// const checkMetamaskInstallation = () => {
//     if (window.ethereum == undefined) {
//         alert("MetaMask is not installed");
//         return;
//     }
// };

// const App = () => {
//     const [email, setEmail] = useState("");
//     const [walletAddress, setWalletAddress] = useState("");
//     const [messageToSign, setMessageToSign] = useState("");
//     const [hasSignedUp, setHasSignedUp] = useState(false);
//     const [pendingTxMessage, setPendingTxMessage] = useState("");
//     const [isStoragePromptReady, setIsStoragePromptReady] = useState(false);

    


//    // Connect user email to eoa account.
//     const connectWallet = async () => {
//         checkMetamaskInstallation();
//         const provider = new ethers.BrowserProvider(window.ethereum);
//         const accounts = await provider.send("eth_requestAccounts", []);
//         const account = accounts[0];
//         alert(account);
//         setWalletAddress(accounts[0]);
//     };

//   // 2. Sign up (POST /signup), then fetch the message (GET /api/get-message-to-sign)

//   // Generates a Machine Smart Account DID that the eoa account will sign to prove ownership.
//   const handleSignUp = async () => {
//     try {
//       // set tag to known quest (TEST IN THIS CASE)
//       const payload = { email, eoa_address: walletAddress, tag: "TEST" };
//       console.log("Sign-up payload:", payload);

//       const response = await axios.post("http://localhost:8000/api/signup", payload);

//       if (response.status_code === 200) {
//         console.log("Successfully received DID message:", response.data.did_tx_message);
//         setMessageToSign(response.data.did_tx_message);
//         // Optionally sign it here or let user sign it later
//         setHasSignedUp(true);
//       } else {
//         console.error("Sign Up failed:", response.data.message);
//         alert(`Error: ${response.data.message}`);
//       }
//     } catch (error) {
//       console.error("Error in sign up:", error);
//     }
//   };

//   const sign_message = async() => {
//     try {
//       const provider = new ethers.BrowserProvider(window.ethereum);
//       const signer = await provider.getSigner();
      
//       // Sign the message from the backend
//       const signature = await signer.signMessage(messageToSign);
//       console.log("Message signed! Signature:", signature);

//       return signature
//     } catch (error){
//       console.error("Error in sign up or fetching message:", error);

//     }

//   }

//   // 3. Actually request the signature from the user’s wallet
//   const handleSignMessage = async () => {
//     try {
//       if (!window.ethereum) {
//         alert("MetaMask not detected");
//         return;
//       }
//       const provider = new ethers.BrowserProvider(window.ethereum);
//       const signer = await provider.getSigner();
      
//       // Sign the message from the backend
//       const signature = await signer.signMessage(messageToSign);

//       console.log("Message signed! Signature:", signature);

//       // DID precompile hardcoded in to prevent errors
//       const payload = { signature: signature, eoa_address: walletAddress, target: "0x0000000000000000000000000000000000000800"};
//       const response = await axios.post("http://localhost:8000/api/generate-eoa-tx-message", payload);
//       if (response.status == 200){
//         console.log(response)
//         console.log("Successfully received the message to sign: ", response.data.eoa_tx_message);
//         setPendingTxMessage(response.data.eoa_tx_message); // Update the transaction message
//       }

//       // const response = await axios.get(`http://localhost:8000/api/get-eoa-tx-message`, {
//       //   params: { walletAddress },
//       // });
//     } catch (error) {
//       console.error("Error signing the message:", error);
//     }
//   };

//   const fetchPendingTxMessage = async () => {
//     try {
//       const provider = new ethers.BrowserProvider(window.ethereum);
//       const signer = await provider.getSigner();

//       const packedBytes = ethers.getBytes(pendingTxMessage);

//       // Sign the transaction message
//       const signature = await signer.signMessage(packedBytes);

//       console.log("Transaction signed! Signature:", signature);

//       const payload = { signature: signature, eoa_address: walletAddress, target: "0x0000000000000000000000000000000000000800"};
//       const response = await axios.post("http://localhost:8000/api/test", payload);

//       if (response.status == 200){
//         console.log("Transaction successful:", response.message);
//         setIsStoragePromptReady(true); // Show the new button
//       }
//       console.log(response);

//     } catch (error) {
//       console.error("Error signing the transaction:", error);
//     }
//   };

//   const handleStorageTransaction = async () => {
//     try {
//       const response = await axios.post("http://localhost:8000/api/storage-transaction", payload);
  
//       if (response.status === 200) {
//         console.log("Storage transaction successful:", response.data);
//         alert("Storage transaction successfully executed!");
//       }
//     } catch (error) {
//       console.error("Error triggering storage transaction:", error);
//     }
//   };

//     return (
//         <div className="App">
//           <Helmet>
//             <title>Badger Blocks</title> {/* text that is on the chrome tab */}
//           </Helmet>
//           <header className="App-header">
//             <img src={image} className="small-image" />
//             <h1 className="primary">App Frontend</h1>
      
//             {!walletAddress ? (
//               <button className="btn_props" onClick={connectWallet}>
//                 Connect Wallet
//               </button>
//             ) : (
//               <div>
//                 <button className="btn_props" onClick={handleSignUp}>
//                   Sign Up with Email
//                 </button>
//                 <input
//                   type="email"
//                   placeholder="Enter your email"
//                   value={email}
//                   onChange={(e) => setEmail(e.target.value)}
//                   className="text_box"
//                 />
      
//                 {/* Show sign-message button only if user has "signed up" and we have a message */}
//                 {hasSignedUp && messageToSign && (
//                   <div style={{ marginTop: "1rem" }}>
//                     <p> We need your signature to link your Machine DID to your eoa wallet:</p>
//                     <button className="btn_props" onClick={handleSignMessage}>Sign Message</button>
//                   </div>
//                 )}
//               {pendingTxMessage && (
//                 <div style={{ marginTop: "1rem" }}>
//                   <p>We need your signature to approve the AddAttribute for DID transaction on-chain:</p>
//                     <button className="btn_props" onClick={fetchPendingTxMessage}>
//                     Approve Transaction
//                   </button>
//               </div>
//             )}
//             {/* {isStorageTxReady && (
//             <div style={{ marginTop: "1rem" }}>
//               <p>Transaction approved! Now trigger a storage transaction:</p>
//               <button className="btn_props" onClick={handleStorageTransaction}>
//                 Trigger Storage Transaction
//               </button>
//             </div>
//           )} */}
//               </div>
//             )}
//           </header>
//         </div>
//       );
//     };
    
//     export default App;

import { useState } from "react";
import { ethers } from "ethers";
import { Helmet } from "react-helmet";
import axios from "axios";
import "./App.css";
import image from "./peaq_logo.png";

const checkMetamaskInstallation = () => {
  if (window.ethereum === undefined) {
    alert("MetaMask is not installed");
    return false;
  }
  return true;
};

const App = () => {
  const [email, setEmail] = useState("");
  const [walletAddress, setWalletAddress] = useState("");
  const [messageToSign, setMessageToSign] = useState("");
  const [hasSignedUp, setHasSignedUp] = useState(false);
  const [pendingTxMessage, setPendingTxMessage] = useState("");
  const [targetPrecompile, setTarget] = useState("");
  const [isStoragePromptReady, setIsStoragePromptReady] = useState(false);


  // ------------------------------------------------------------------
  // 1) Connect Wallet
  // ------------------------------------------------------------------
  const connectWallet = async () => {
    if (!checkMetamaskInstallation()) return;
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const accounts = await provider.send("eth_requestAccounts", []);
      const account = accounts[0];
      alert(`Wallet connected: ${account}`);
      setWalletAddress(account);
    } catch (error) {
      console.error("Error connecting wallet:", error);
    }
  };

  // ------------------------------------------------------------------
  // 2) Sign Up with Email
  // ------------------------------------------------------------------
  const handleSignUp = async () => {
    if (!walletAddress) {
      alert("Connect wallet first!");
      return;
    }
    try {
      const payload = { email, eoa_address: walletAddress, tag: "TEST" };
      console.log("Sign-up payload:", payload);

      const response = await axios.post("http://localhost:8000/api/signup", payload);

      if (response.data.status === "success") {
        console.log("Successfully received DID message:", response.data.did_tx_message);
        setMessageToSign(response.data.did_tx_message);
        // Optionally sign it here or let user sign it later
        setHasSignedUp(true);
        setTarget("0x0000000000000000000000000000000000000800");
      } else {
        console.error("Sign Up failed:", response.data.message);
        alert(`Error: ${response.data.message}`);
      }
    } catch (error) {
      console.error("Error in sign up:", error);
    }
  };

  // ------------------------------------------------------------------
  // 3) Sign DID Message (Link DID to EOA)
  // ------------------------------------------------------------------
  const handleSignMessage = async () => {
    if (!checkMetamaskInstallation()) return;
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();

      // Sign the message from the backend (the DID message)
      const signature = await signer.signMessage(messageToSign);
      console.log("DID message signed! Signature:", signature);

      // Now tell the backend we have this signature -> generate EOA Tx message
      const payload = {
        signature,
        eoa_address: walletAddress,
        target: targetPrecompile,
      };
      const response = await axios.post("http://localhost:8000/api/generate-eoa-tx-message", payload);

      if (response.data.status === "success") {
        console.log("Successfully received EOA Tx message:", response.data.eoa_tx_message);
        setMessageToSign(null); // removes button
        setPendingTxMessage(response.data.eoa_tx_message);
      } else {
        console.error("Error generating EOA Tx message:", response.data.eoa_tx_message);
        alert(`Error: ${response.data.eoa_tx_message}`);
      }
    } catch (error) {
      console.error("Error signing the DID message:", error);
    }
  };

  // ------------------------------------------------------------------
  // 4) Approve Transaction
  // ------------------------------------------------------------------
  const handleApproveTransaction = async () => {
    if (!checkMetamaskInstallation()) return;
    if (!pendingTxMessage) {
      alert("No pending transaction message to sign.");
      return;
    }

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();

      // Convert the hex string to bytes
      const packedBytes = ethers.getBytes(pendingTxMessage);

      // Sign the transaction message
      const signature = await signer.signMessage(packedBytes);
      console.log("EOA Transaction signed! Signature:", signature);

      const payload = {
        signature,
        eoa_address: walletAddress,
        target: targetPrecompile,
      };

      console.log(payload)

      const response = await axios.post("http://localhost:8000/api/test", payload);

      if (response.data.status === "success") {
        console.log("Transaction successful:", response.data.message);
        setPendingTxMessage(null);
        setIsStoragePromptReady(true); // Next step: trigger storage transaction
      } else {
        console.error("Transaction failed:", response.data.message);
        alert(`Error: ${response.data.message}`);
      }
    } catch (error) {
      console.error("Error signing the transaction:", error);
    }
  };

  // ------------------------------------------------------------------
  // 5) Trigger Storage Transaction
  // ------------------------------------------------------------------
  const handleStorageTransaction = async () => {
// This is where you will get the ItemType and Item that the user is storing

    try {
      setTarget("0x0000000000000000000000000000000000000801");
      // Now tell the backend we have this signature -> generate EOA Tx message
      const payload = {
        eoa_address: walletAddress,
        target: "0x0000000000000000000000000000000000000801",
        item_type: "ITEM_TYPE_5",
        item: "Item_123"
      };

      const response = await axios.post("http://localhost:8000/api/storage-transaction", payload);

      if (response.data.status === "success") {
        console.log("Storage transaction successful:", response.data.eoa_tx_message);
  
        // Reset states to retrigger the "Approve Transaction" button
        setIsStoragePromptReady(false); // Hide the storage prompt
        setPendingTxMessage(response.data.eoa_tx_message);
      } else {
        console.error("Storage transaction error:", response.data.eoa_tx_message);
        alert(`Error: ${response.data.eoa_tx_message}`);
      }
    } catch (error) {
      console.error("Error triggering storage transaction:", error);
    }
  };

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------
  return (
    <div className="App">
      <Helmet>
        <title>Badger Blocks</title>
      </Helmet>
      <header className="App-header">
        <img src={image} className="small-image" alt="App Logo" />
        <h1 className="primary">App Frontend</h1>

        {!walletAddress ? (
          <button className="btn_props" onClick={connectWallet}>
            Connect Wallet
          </button>
        ) : (
          <div>
            <button className="btn_props" onClick={handleSignUp}>
              Sign Up with Email
            </button>
            <input
              type="email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="text_box"
            />

            {hasSignedUp && messageToSign && (
              <div style={{ marginTop: "1rem" }}>
                <p>We need your signature to link your Machine DID to your EOA wallet:</p>
                <button className="btn_props" onClick={handleSignMessage}>
                  Sign DID Message
                </button>
              </div>
            )}

            {pendingTxMessage && (
              <div style={{ marginTop: "1rem" }}>
                <p>We need your signature to approve the on-chain transaction:</p>
                <button className="btn_props" onClick={handleApproveTransaction}>
                  Approve Transaction
                </button>
              </div>
            )}

            {isStoragePromptReady && (
              <div style={{ marginTop: "1rem" }}>
                <p>Transaction approved! Now trigger a storage transaction:</p>
                <button className="btn_props" onClick={handleStorageTransaction}>
                  Trigger Storage Transaction
                </button>
              </div>
            )}
          </div>
        )}
      </header>
    </div>
  );
};

export default App;
