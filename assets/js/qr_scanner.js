// assets/qr_scanner.js
console.log('Production Guarded Camera QR Module Active');

// Centralize instances to clean memory allocations explicitly
window.activeHtml5QrCode = null;
window.cameraIsProcessing = false;

async function safelyStopCamera() {
    if (window.activeHtml5QrCode) {
        try {
            console.log("Terminating active camera instance to clean system memory allocation...");
            if (window.activeHtml5QrCode.isScanning) {
                await window.activeHtml5QrCode.stop();
            }
            // Explicit garbage collection wipeout
            document.getElementById("qr-reader").innerHTML = "";
            window.activeHtml5QrCode = null;
            window.cameraIsProcessing = false;
        } catch (err) {
            console.error("Error encountered freeing system camera threads:", err);
        }
    }
}

async function startCameraEngine() {
    await safelyStopCamera(); // Ensure old lingering instance streams are cleared out first

    if (typeof Html5Qrcode === 'undefined') {
        console.error("Html5Qrcode engine dependency missing in window DOM frame context.");
        return;
    }

    const readerElement = document.getElementById("qr-reader");
    if (!readerElement) return;

    window.activeHtml5QrCode = new Html5Qrcode("qr-reader");
    window.cameraIsProcessing = true;

    const qrConfig = { fps: 15, qrbox: { width: 250, height: 250 } };

    window.activeHtml5QrCode.start(
        { facingMode: "environment" },
        qrConfig,
        (decodedText) => {
            console.log("QR Data Processed:", decodedText);
            // Route seamlessly through the Reflex Bridge channel
            const bridgeInput = document.querySelector('.reflex-scan-bridge input');
            if (bridgeInput) {
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                setter.call(bridgeInput, decodedText);
                bridgeInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        },
        (errorMessage) => {
            // Suppress verbose frame telemetry loop logs to avoid memory bloat
        }
    ).catch(err => {
        console.error("Camera startup crash exception:", err);
        window.cameraIsProcessing = false;
    });
}

// Memory Cleanup Hook: Wipe hooks if page context switches
const pathObserver = new MutationObserver(() => {
    if (!window.location.pathname.includes('/scanner')) {
        safelyStopCamera();
    }
});
pathObserver.observe(document.body, { childList: true, subtree: true });

// Page Visibility handler equipped with proper lifecycle check constraints
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        safelyStopCamera();
    } else if (window.location.pathname.includes('/scanner') && !window.cameraIsProcessing) {
        startCameraEngine();
    }
});

window.initiateCameraInterface = startCameraEngine;
window.shutdownCameraInterface = safelyStopCamera;