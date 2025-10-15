#include <ixwebsocket/IXWebSocket.h>
#include <iostream>
#include <chrono>

int main() {
    ix::WebSocket webSocket;

    // Replace with the actual address of your Python WebSocket server
    std::string serverUrl = "ws://192.168.1.42:8765"; // example IP/port

    webSocket.setUrl(serverUrl);

    webSocket.setOnMessageCallback([](const ix::WebSocketMessagePtr& msg) {
        if (msg->type == ix::WebSocketMessageType::Message) {
            auto now = std::chrono::high_resolution_clock::now();
            auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
            std::cout << "Received message: " << msg->str << " at " << ms << " ms\n";
        } else if (msg->type == ix::WebSocketMessageType::Open) {
            std::cout << "Connection established to server.\n";
        } else if (msg->type == ix::WebSocketMessageType::Error) {
            std::cout << "Error: " << msg->errorInfo.reason << std::endl;
        }
    });

    webSocket.start();

    std::cout << "WebSocket client started. Listening...\n";

    // Keep the main thread alive
    while (true) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }

    return 0;
}