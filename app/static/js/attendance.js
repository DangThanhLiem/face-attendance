class AttendanceManager {
    constructor() {
        this.isProcessing = false;
    }

    async markAttendance() {
        if (this.isProcessing) {
            showNotification('Please wait, processing previous request...', 'warning');
            return;
        }

        this.isProcessing = true;
        showLoading(true);

        try {
            if (!cameraHandler || !cameraHandler.isInitialized) {
                throw new Error('Camera is not initialized');
            }

            const imageBlob = await cameraHandler.captureFrame();
            const formData = new FormData();
            formData.append('image', imageBlob, 'capture.jpg');

            const response = await fetch('/employee/mark-attendance', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                showNotification(result.message, 'success');
                updateAttendanceStatus(result);
                
                // Reload page after successful attendance marking
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                showNotification(result.message, 'error');
            }
        } catch (error) {
            console.error('Error marking attendance:', error);
            showNotification('Failed to mark attendance. Please try again.', 'error');
        } finally {
            this.isProcessing = false;
            showLoading(false);
        }
    }
}

function showNotification(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    const container = document.querySelector('.container');
    container.insertBefore(alertDiv, container.firstChild);

    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

function showLoading(show) {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.style.display = show ? 'block' : 'none';
    }
}

function updateAttendanceStatus(data) {
    const statusElement = document.getElementById('attendance-status');
    if (statusElement) {
        statusElement.textContent = data.status;
        statusElement.className = `attendance-status status-${data.status.toLowerCase()}`;
    }

    const timeElement = document.querySelector('.card-body p strong');
    if (timeElement) {
        timeElement.textContent = data.time;
    }
}

// Initialize attendance manager
let attendanceManager;

document.addEventListener('DOMContentLoaded', () => {
    attendanceManager = new AttendanceManager();
});

// Global function to mark attendance
function markAttendance() {
    if (attendanceManager) {
        attendanceManager.markAttendance();
    }
}