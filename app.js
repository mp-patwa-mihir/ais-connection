const express = require("express");
const http = require("http");
const socketIo = require("socket.io");
const { listenToAISStreams } = require("./tcp-client");
const { Worker } = require("worker_threads");
const app = express();
const server = http.createServer(app);
const io = socketIo(server);

// Middleware to parse JSON
app.use(express.json());

// Configure connections
const connections = [{ ip: "37.58.208.109", port: 8040 }];

// To store which user is interested in which ip and port
const userSubscriptions = {};

// Worker pool setup
const workerPool = [];

// Function to get a worker from the pool or create a new one
function getWorker(data) {
  if (workerPool.length > 0) {
    return workerPool.pop();
  } else {
    return new Worker("./decodeWorker.js", { workerData: data });
  }
}

// Function to return a worker to the pool
function returnWorker(worker) {
  workerPool.push(worker);
}

// Function to decode AIS data using worker threads
function decodeAisMessageInWorker(data) {
  return new Promise((resolve, reject) => {
    const worker = getWorker(data);
    worker.postMessage(data);

    worker.on("message", (decoded) => {
      returnWorker(worker);
      resolve(decoded);
    });

    worker.on("error", (error) => {
      returnWorker(worker);
      reject(error);
    });

    worker.on("exit", (code) => {
      if (code !== 0) {
        returnWorker(worker);
        reject(new Error(`Worker stopped with exit code ${code}`));
      }
    });
  });
}

// Listen to AIS streams and emit decoded data to relevant users
listenToAISStreams(connections, async (ip, port, data) => {
  try {
    const decoded = await decodeAisMessageInWorker(data); // Decode using worker thread
    if (decoded) {
      const targetClients = userSubscriptions[`${ip}:${port}`] || [];
      targetClients.forEach((socketId) => {
        const socket = io.sockets.sockets.get(socketId);
        if (socket) {
          socket.emit("ais-data", { ip, port, data: decoded });
        }
      });
    }
  } catch (error) {
    console.error(`Error processing AIS data: ${error.message}`);
  }
});

// WebSocket connection handling
io.on("connection", (socket) => {
  console.log(`Client connected: ${socket.id}`);

  // Subscribe the client to multiple IP and port pairs
  socket.on("subscribe", (ipPorts) => {
    ipPorts.forEach(({ ip, port }) => {
      const key = `${ip}:${port}`;
      if (!userSubscriptions[key]) {
        userSubscriptions[key] = [];
      }
      userSubscriptions[key].push(socket.id);
      console.log(`Client ${socket.id} subscribed to ${key}`);
    });
  });

  // Unsubscribe the client from a specific IP and port
  socket.on("unsubscribe", (ipPorts) => {
    ipPorts.forEach(({ ip, port }) => {
      const key = `${ip}:${port}`;
      if (userSubscriptions[key]) {
        userSubscriptions[key] = userSubscriptions[key].filter(
          (id) => id !== socket.id
        );
        console.log(`Client ${socket.id} unsubscribed from ${key}`);
      }
    });
  });

  // Handle disconnections
  socket.on("disconnect", () => {
    console.log(`Client disconnected: ${socket.id}`);
    // Remove the client from all subscriptions
    for (const key in userSubscriptions) {
      userSubscriptions[key] = userSubscriptions[key].filter(
        (id) => id !== socket.id
      );
    }
  });
});

// Endpoint to serve the app
app.get("/", (req, res) => {
  res.send("Express server with Socket.io is running.");
});

// Start the HTTP server
const port = 3001;
server.listen(port, () => {
  console.log(`Server running at http://localhost:${port}`);
});
