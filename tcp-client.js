const net = require("net");

/**
 * Establish persistent TCP connections and stream AIS data.
 * @param {Array<{ip: string, port: number}>} connections - List of IP and port pairs.
 * @param {Function} onDataCallback - Callback to handle incoming AIS data.
 */
function listenToAISStreams(connections, onDataCallback) {
  connections.forEach(({ ip, port }) => {
    const createConnection = () => {
      const client = net.createConnection({ host: ip, port }, () => {
        console.log(`Connected to ${ip}:${port}`);
      });

      client.on("data", (data) => {
        // Pass incoming AIS data to the callback
        onDataCallback(ip, port, data.toString());
      });

      client.on("error", (err) => {
        console.error(`Error on ${ip}:${port} - ${err.message}`);
      });

      client.on("end", () => {
        console.warn(`Disconnected from ${ip}:${port}. Reconnecting...`);
        setTimeout(createConnection, 5000); // Reconnect after a delay
      });

      client.on("close", () => {
        console.warn(`Connection closed for ${ip}:${port}. Reconnecting...`);
        setTimeout(createConnection, 5000); // Reconnect after a delay
      });
    };

    createConnection();
  });
}

module.exports = { listenToAISStreams };
