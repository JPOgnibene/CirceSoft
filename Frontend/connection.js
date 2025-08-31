// Get DOM elements
const connectionIcon = document.getElementById('toggleImage');
const connectionSwitch = document.getElementById('websocket_on');
const messagesContainer = document.getElementById('messages');

let websocketConnectionStatus = false;

// Handle toggle event
connectionSwitch.addEventListener('change', function () {
    websocketConnectionStatus = this.checked;
    updateConnection();
});

// Main logic to update connection state
function updateConnection() {
    // Update icon image
    connectionIcon.src = websocketConnectionStatus 
        ? 'websocket_connection_on.png' 
        : 'websocket_connection_off.png';

    // Add log entry + start/stop message simulation
    if (websocketConnectionStatus) {
        addHazardMessage("WebSocket ON - simulated messages activated", "info");
        simulateMessages(); // Simulated demo messages
    } else {
        addHazardMessage("WebSocket OFF", "warning");
    }
}

// Add styled hazard message to log
function addHazardMessage(text, level = "info") {
    const p = document.createElement("p");
    const timestamp = new Date().toLocaleTimeString();
    p.textContent = `[${timestamp}] ${text}`;
    p.className = `hazard ${level}`;
    messagesContainer.appendChild(p);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Simulated message sequence
function simulateMessages() {
    setTimeout(() => addHazardMessage("Obstacle detected ahead", "danger"), 1000);
    setTimeout(() => addHazardMessage("Low visibility in sector 3", "warning"), 3000);
    setTimeout(() => addHazardMessage("System check complete", "info"), 5000);
}


const slider = document.getElementById('progressSlider');
const progressFill = document.getElementById('progressFill');
const progressValue = document.getElementById('progressValue');

slider.addEventListener('input', () => {
    const value = slider.value;
    progressFill.style.width = value + '%';
    progressValue.textContent = value + '%';
});

const readFromFileButton = document.querySelector('.readFromFile');

readFromFileButton.addEventListener('click', () => {
    fetch('messages.txt')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.text();
        })
        .then(text => {
            const lines = text.split('\n');
            lines.forEach(line => {
                if (line.trim()) {
                    addHazardMessage(line.trim(), "info");
                }
            });
        })
        .catch(error => {
            addHazardMessage(`Failed to read botInput.txt: ${error.message}`, "danger");
        });
});
