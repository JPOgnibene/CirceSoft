/*
Author: JP Ognibene & ChatGPT
Purpose: prototype code to send a command at a 10hz frequency
Date: 4/15/2025
*/
#include <iostream>
#include <chrono>
#include <thread>

// Simulated command function
void sendCommand() {
    std::cout << "Command sent at " 
              << std::chrono::duration_cast<std::chrono::milliseconds>(
                     std::chrono::high_resolution_clock::now().time_since_epoch()
                 ).count() 
              << " ms\n";
}

int main() {
    using namespace std::chrono;

    // Target period for 10 Hz = 100 milliseconds
    const auto targetPeriod = milliseconds(100);

    while (true) {
        auto start = high_resolution_clock::now();

        // Send the command
        sendCommand();

        // Wait until the next 100ms tick
        std::this_thread::sleep_until(start + targetPeriod);
    }

    return 0;
}