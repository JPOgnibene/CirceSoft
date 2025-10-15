const connectionIcon     = document.getElementById('toggleWebsocket');
const connectionSwitch  = document.getElementById('websocket_on');
const messagesContainer = document.getElementById('messages');

let websocketConnectionStatus = false;

// Toggle WebSocket icon based on switch
connectionSwitch.addEventListener('change', function () {
  websocketConnectionStatus = this.checked;
  updateConnection();
});

// Update the connection icon and, if connected, load messages from file
function updateConnection() {
  if (websocketConnectionStatus) {
    addHazardMessage("Connected to CirceBot", "info");
    loadMessagesFromFile();
    // Optional: poll every 5 seconds
    // pollInterval = setInterval(loadMessagesFromFile, 5000);
  } else {
    addHazardMessage("Disconnected from CirceBot", "warning");
    // clearInterval(pollInterval);
  }
}

// Function to add styled log messages
function addHazardMessage(text, level = "info") {
  const p = document.createElement("p");
  const timestamp = new Date().toLocaleTimeString();
  p.textContent = `[${timestamp}] ${text}`;
  p.className = `hazard ${level}`;
  messagesContainer.appendChild(p);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Fetches current_values.txt, parses it, and emits each key/value as a message
async function loadMessagesFromFile() {
  try {
    const res = await fetch('current_values.txt', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.text();

    raw
      .split('\n')
      .map(line => line.trim())
      .filter(line => line && line.includes('='))
      .forEach(line => {
        const [key, value] = line.split('=');
        // Default level
        let level = 'info';
        // Example: flag non-zero errorCode as danger
        if (key === 'errorCode' && value.trim() !== '0') {
          level = 'danger';
        }
        addHazardMessage(`${key}: ${value}`, level);
      });
  } catch (err) {
    console.error('Failed to load messages:', err);
    addHazardMessage("Error loading messages file", "danger");
  }
}
