// SendToCirceBot.jsx
//
// Implements a send to bot button for debugging purposes that, on click, sends the coordinate points in order to
// CirceBot.
//

function sendToCirceBot ({ path }) {
    const callSendAPI = async() => {
        console.log("Sending to CirceBot...")
        console.log("Data to send: ", JSON.stringify({ items: path }))
        try {
            console.log("Trying to send PUT to API...")
            //update when coordinate format is standardized
            const response = await fetch('http://localhost:8765/coordinates/send', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ items: path })
            });
        
            const data = await response.json()
            console.log('Success: ', data);

        } catch (error) {
            console.log("Failed to establish API endpoint connection", error)
        }
    }

    return (
        <div>
        <button onClick={callSendAPI}>Send path to CirceBot</button>
        </div>
    );
};

export default sendToCirceBot;