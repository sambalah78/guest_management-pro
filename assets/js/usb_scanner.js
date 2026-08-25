// assets/js/usb_scanner.js
console.log('EventLah Multi-Scanner System Loaded');

window.scannerActive = false;
let scanBuffers = {};
let scannerTimestamps = {};

// Support multiple scanners by device ID
function getScannerId(e) {
    // Try to identify which scanner sent the input
    // Some scanners send a unique prefix or use different key codes
    return e.target ? e.target.id || 'default' : 'default';
}

document.addEventListener('keydown', function(e) {
    if (!window.scannerActive) return;

    // Ignore modifier keys
    if (e.ctrlKey || e.altKey || e.metaKey) return;

    const scannerId = getScannerId(e);
    const currentTime = Date.now();
    const timeDiff = currentTime - (scannerTimestamps[scannerId] || currentTime);
    scannerTimestamps[scannerId] = currentTime;

    // Reset buffer if typing is too slow (human typing)
    if (timeDiff > 200 && e.key !== 'Enter') {
        scanBuffers[scannerId] = '';
    }

    if (e.key === 'Enter') {
        e.preventDefault();
        const code = (scanBuffers[scannerId] || '').trim();
        if (code.length >= 3) {
            processGlobalScan(code, scannerId);
        }
        scanBuffers[scannerId] = '';
    } else if (e.key.length === 1) {
        scanBuffers[scannerId] = (scanBuffers[scannerId] || '') + e.key;
    }
});

// Queue for processing scans
let scanQueue = [];
let isProcessingQueue = false;

function processGlobalScan(code, scannerId) {
    console.log(`Scanner ${scannerId} captured:`, code);

    // Add to queue
    scanQueue.push({ code, scannerId, timestamp: Date.now() });

    // Process queue if not already processing
    if (!isProcessingQueue) {
        processQueue();
    }
}

async function processQueue() {
    if (isProcessingQueue || scanQueue.length === 0) return;

    isProcessingQueue = true;

    while (scanQueue.length > 0) {
        const item = scanQueue.shift();

        // Skip if too old (> 5 seconds)
        if (Date.now() - item.timestamp > 5000) {
            console.log('Skipping old scan:', item.code);
            continue;
        }

        try {
            // Find the Reflex bridge input
            const rxInput = document.querySelector('.reflex-scan-bridge input');
            if (rxInput) {
                const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(rxInput, item.code);

                const event = new Event('input', { bubbles: true });
                rxInput.dispatchEvent(event);

                // Small delay between scans
                await new Promise(resolve => setTimeout(resolve, 100));
            }
        } catch(e) {
            console.error('Process error:', e);
        }
    }

    isProcessingQueue = false;
}

// Window functions for external control
window.activateAllScanners = function() {
    console.log('All scanners activated');
    window.scannerActive = true;
    scanBuffers = {};
    scannerTimestamps = {};
};

window.deactivateAllScanners = function() {
    console.log('All scanners deactivated');
    window.scannerActive = false;
    scanBuffers = {};
    scannerTimestamps = {};
};

window.enableAllScanners = window.activateAllScanners;
window.disableAllScanners = window.deactivateAllScanners;