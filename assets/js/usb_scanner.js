// EventLah USB Scanner Workstation
//
// A USB QR scanner behaves as a keyboard/HID device.
// The browser therefore identifies the WORKSTATION, not the
// individual physical USB scanner.
//
// The server-side ScannerState owns the authenticated station identity.

console.log("EventLah USB Scanner Workstation Loaded");

window.scannerActive = false;

let scanBuffer = "";
let lastKeyTime = 0;
let scanQueue = [];
let isProcessingQueue = false;

const HUMAN_TYPING_TIMEOUT_MS = 200;
const MAX_SCAN_AGE_MS = 5000;
const BETWEEN_SCAN_DELAY_MS = 100;


document.addEventListener("keydown", function (event) {
    if (!window.scannerActive) {
        return;
    }

    // Ignore browser/application shortcuts.
    if (event.ctrlKey || event.altKey || event.metaKey) {
        return;
    }

    const now = Date.now();
    const elapsed = now - lastKeyTime;
    lastKeyTime = now;

    // A normal person typing is much slower than a USB scanner.
    // Reset the buffer when the gap indicates a new input sequence.
    if (elapsed > HUMAN_TYPING_TIMEOUT_MS && event.key !== "Enter") {
        scanBuffer = "";
    }

    if (event.key === "Enter") {
        event.preventDefault();

        const code = scanBuffer.trim();
        scanBuffer = "";

        if (code.length >= 3) {
            queueScan(code);
        }

        return;
    }

    // Only accept printable characters.
    if (event.key.length === 1) {
        scanBuffer += event.key;
    }
});


function queueScan(code) {
    scanQueue.push({
        code: code,
        timestamp: Date.now()
    });

    if (!isProcessingQueue) {
        processScanQueue();
    }
}


async function processScanQueue() {
    if (isProcessingQueue) {
        return;
    }

    isProcessingQueue = true;

    try {
        while (scanQueue.length > 0) {
            const item = scanQueue.shift();

            // Never process an unexpectedly old scan.
            if (Date.now() - item.timestamp > MAX_SCAN_AGE_MS) {
                console.warn("Skipping stale scanner input");
                continue;
            }

            const rxInput = document.querySelector(
                ".reflex-scan-bridge input"
            );

            if (!rxInput) {
                console.error("EventLah scanner bridge input not found");
                continue;
            }

            try {
                const setter = Object.getOwnPropertyDescriptor(
                    HTMLInputElement.prototype,
                    "value"
                ).set;

                setter.call(rxInput, item.code);

                rxInput.dispatchEvent(
                    new Event("input", { bubbles: true })
                );

                await new Promise((resolve) =>
                    setTimeout(resolve, BETWEEN_SCAN_DELAY_MS)
                );
            } catch (error) {
                console.error(
                    "EventLah scanner bridge error:",
                    error
                );
            }
        }
    } finally {
        isProcessingQueue = false;
    }
}


/**
 * Activate this workstation's USB scanner.
 *
 * IMPORTANT:
 * This does NOT activate all scanners.
 * Station identity is handled by ScannerState/server authentication.
 */
window.activateScanner = function () {
    console.log("EventLah scanner workstation activated");

    window.scannerActive = true;

    scanBuffer = "";
    lastKeyTime = 0;
    scanQueue = [];
};


/**
 * Deactivate this workstation's USB scanner.
 */
window.deactivateScanner = function () {
    console.log("EventLah scanner workstation deactivated");

    window.scannerActive = false;

    scanBuffer = "";
    lastKeyTime = 0;
    scanQueue = [];
};

window.scannerStationAuthenticate = function (token) {
    const input = document.getElementById(
        "scanner-station-token"
    );

    if (!token) return;

    // Pass the credential to the Reflex state handler.
    window.__eventlahScannerStationToken = token;

    console.log("Scanner station authentication requested");

    // The actual server-side authentication bridge is established
    // by the Reflex page/state event.
};
/*
 * Backward-compatible aliases.
 *
 * Existing pages/code may still call these names.
 * They now control ONLY THIS workstation.
 */
window.activateAllScanners = window.activateScanner;
window.deactivateAllScanners = window.deactivateScanner;

window.enableAllScanners = window.activateScanner;
window.disableAllScanners = window.deactivateScanner;