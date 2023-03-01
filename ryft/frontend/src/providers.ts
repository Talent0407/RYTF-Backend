import WalletConnect from '@walletconnect/web3-provider';
import { ethers } from 'ethers';
import { SignatureType, SiweMessage } from 'siwe';

declare global {
    interface Window {
        ethereum: { request: (opt: { method: string }) => Promise<Array<string>> };
        web3: unknown;
    }
}

const enum Providers {
    METAMASK = 'metamask',
    WALLET_CONNECT = 'walletconnect',
}

//eslint-disable-next-line
const metamask = window.ethereum;
let walletconnect: WalletConnect;

let disconnectButton: HTMLDivElement;

let signInButton: HTMLButtonElement;

let signatureResult: HTMLParagraphElement;
let messageResult: HTMLParagraphElement;
let bodyResult: HTMLParagraphElement;
let walletAddress: HTMLInputElement;

let warningWindow: HTMLDivElement;

/**
 * We need these to remove/add the eventListeners
 */

const signIn = async (connector: Providers) => {
    let provider: ethers.providers.Web3Provider;

    /**
     * Connects to the wallet and starts a etherjs provider.
     */
    if (connector === 'metamask') {
        await metamask.request({
            method: 'eth_requestAccounts',
        });
        provider = new ethers.providers.Web3Provider(metamask);
    } else {
        /**
         * The Infura ID provided just for the sake of the demo, you'll need to replace
         * it if you want to go to production.
         */
        walletconnect = new WalletConnect({
            infuraId: '8fcacee838e04f31b6ec145eb98879c8',
        });
        walletconnect.enable();
        provider = new ethers.providers.Web3Provider(walletconnect);
    }

    const [address] = await provider.listAccounts();
    if (!address) {
        throw new Error('Address not found.');
    }

    /**
     * Gets a nonce from our backend, this will add this nonce to the session so
     * we can check it on sign in.
     */
    walletAddress = document.getElementById("walletAddress") as HTMLInputElement;
    const walletAddressValue = walletAddress.value
    const messageBody = await fetch('/api/auth/message/', {
        method: 'POST',
        credentials: 'include',
        // headers: {
        //     X_CSRFToken: document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'))[2],
        // },
        body: JSON.stringify({"address": walletAddressValue})
    }).then((res) =>
        res.json(),
    );

    const { nonce, issued_at, message } = messageBody

    console.log(message)

    /**
     * Creates the message object
     */
    // const message = new SiweMessage({
    //     domain: "api.ryftpass.io",
    //     address,
    //     chainId: parseInt(`${await provider.getNetwork().then(({ chainId }) => chainId)}`),
    //     uri: "https://api.ryftpass.io",
    //     version: '1',
    //     statement: 'Ryft Pass',
    //     type: SignatureType.PERSONAL_SIGNATURE,
    //     nonce,
    //     issuedAt: issued_at
    // });

    // console.log(message.signMessage())

    /**
     * Generates the message to be signed and uses the provider to ask for a signature
     */
    const signature = await provider.getSigner().signMessage(message);
    signatureResult = document.getElementById('messageSignResult') as HTMLParagraphElement;
    messageResult = document.getElementById('message') as HTMLParagraphElement;
    bodyResult = document.getElementById('bodyResult') as HTMLParagraphElement;

    const body = JSON.stringify({ message, signature })
    console.log(body)

    signatureResult.textContent = signature
    messageResult.textContent = message
    bodyResult.textContent = body

    /**
     * Calls our sign_in endpoint to validate the message, if successful it will
     * save the message in the session and allow the user to store his text
     */
    // fetch(`/api/auth/login`, {
    //     method: 'POST',
    //     body,
    //     headers: {
    //         'Content-Type': 'application/json',
    //         'X-CSRFToken': document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'))[2],
    //     },
    //     credentials: 'include',
    // }).then(async (res) => {
    //     if (res.status === 200) {
    //         fetch('/api/me', { credentials: 'include' }).then((res) => {
    //             if (res.status === 200) {
    //                 res.json().then(({ text, address, ens }) => {
    //                     connectedState(text, ens ?? address);
    //                 });
    //             }
    //             return;
    //         });
    //     } else {
    //         res.json().then((err) => {
    //             console.error(err);
    //         });
    //     }
    // });
};

const signOut = async () => {
    const loginElements = document.getElementsByClassName('login-screen');
    Array.prototype.forEach.call(loginElements, function (e: HTMLElement) {
        e.classList.remove('hidden');
    });

    const desktopElements = document.getElementsByClassName('desktop-screen');
    Array.prototype.forEach.call(desktopElements, function (e: HTMLElement) {
        e.classList.add('hidden');
    });
    return fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.cookie.match(new RegExp('(^| )csrftoken=([^;]+)'))[2],
        },
    }).then(() => disconnectedState());
};

document.addEventListener('DOMContentLoaded', () => {
    // /**
    //  * Try to fetch user information and updates the state accordingly
    //  */
    // fetch('/api/me', { credentials: 'include' }).then((res) => {
    //     if (res.status === 200) {
    //         res.json().then(({ text, address, ens }) => {
    //             connectedState(text, ens ?? address);
    //         });
    //     } else {
    //         /**
    //          * No session we need to enable signIn buttons
    //          */
    //         const loginElements = document.getElementsByClassName('login-screen');
    //         Array.prototype.forEach.call(loginElements, function (e: HTMLElement) {
    //             e.classList.remove('hidden');
    //         });
    //
    //         const desktopElements = document.getElementsByClassName('desktop-screen');
    //         Array.prototype.forEach.call(desktopElements, function (e: HTMLElement) {
    //             e.classList.add('hidden');
    //         });
    //         disconnectedState();
    //     }
    // });

    /**
     * Bellow here are just helper functions to manage app state
     */
    disconnectButton = document.getElementById('disconnectButton') as HTMLDivElement;

    /**
     * Group buttons
     */
    signInButton = document.getElementById('signIn') as HTMLButtonElement;

    warningWindow = document.getElementById('warningWindow') as HTMLDivElement;

    signInButton.addEventListener('click', () => {
        const selection = document.getElementById('selectProvider') as HTMLSelectElement;

        if (selection.value == 'metamask') {
            signIn(Providers.METAMASK).then(() => {
                void 0;
            });
        } else if (selection.value == 'wallet-connect') {
            signIn(Providers.WALLET_CONNECT).then(() => {
                void 0;
            });
        } else {
            console.log('Provider not yet supported.');
        }
    });

    disconnectButton.addEventListener('click', signOut);
});

const connectedState = (text: string, title: string) => {
    const loginElements = document.getElementsByClassName('login-screen');
    Array.prototype.forEach.call(loginElements, function (e: HTMLElement) {
        e.classList.add('hidden');
    });

    const desktopElements = document.getElementsByClassName('desktop-screen');
    Array.prototype.forEach.call(desktopElements, function (e: HTMLElement) {
        e.classList.remove('hidden');
    });

    /**
     * Updates fields and buttons
     */

    disconnectButton.classList.remove('hidden');
};

const disconnectedState = () => {
    disconnectButton.classList.add('hidden');
};

const showWarning = () => {
    warningWindow.classList.remove('hidden');
    document.getElementById('closeWarningButton').addEventListener('click', hideWarning);
};

const hideWarning = () => {
    warningWindow.classList.add('hidden');
    document.getElementById('closeWarningButton').removeEventListener('click', hideWarning);
};
