class CameraHandler {
    constructor() {
        this.video = document.getElementById('camera-feed');
        this.canvas = document.createElement('canvas');
        this.stream = null;
        this.isInitialized = false;
    }

    async initialize() {
        if (this.isInitialized) return;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: 640,
                    height: 480,
                    facingMode: 'user'
                }
            });

            this.video.srcObject = this.stream;
            await this.video.play();

            this.canvas.width = this.video.videoWidth;
            this.canvas.height = this.video.videoHeight;

            this.isInitialized = true;
        } catch (error) {
            console.error('Error initializing camera:', error);
            throw new Error('Could not access camera. Please ensure camera permissions are granted.');
        }
    }

    async captureFrame() {
        if (!this.isInitialized) {
            await this.initialize();
        }

        const context = this.canvas.getContext('2d');
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        
        return new Promise((resolve) => {
            this.canvas.toBlob(resolve, 'image/jpeg', 0.9);
        });
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.video.srcObject = null;
            this.isInitialized = false;
        }
    }
}

// Global camera instance
let cameraHandler;

document.addEventListener('DOMContentLoaded', async () => {
    const cameraFeed = document.getElementById('camera-feed');
    if (cameraFeed) {
        cameraHandler = new CameraHandler();
        try {
            await cameraHandler.initialize();
        } catch (error) {
            showNotification(error.message, 'error');
        }
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (cameraHandler) {
        cameraHandler.stop();
    }
});