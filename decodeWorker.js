const { parentPort, workerData } = require("worker_threads");
const { AisDecode } = require("ggencoder");

try {
  const ais = new AisDecode(workerData);
  if (ais.valid) {
    parentPort.postMessage(ais); // Send decoded data back to main thread
  } else {
    parentPort.postMessage(null);
  }
} catch (error) {
  parentPort.postMessage(null);
}
