const express = require("express");
const { kill } = require("process");
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.text({type: 'text/plain'}));

let address = null; // Only one PC's info
let interval = null;
// Update the current PC IP + port
app.post("/set", (req, res) => {
  const new_address = req.body;
  if (!new_address)
    return res.status(400).json({ error: `Missing IP or port.`});
  address = new_address;
  res.send("IP registered successfully");
  interval = setInterval(checkStatus, 3000);
});

async function checkStatus() {
  try {
    const res = await fetch(`${address}/ping`, { timeout: 3000 });
    if (res.ok) {
      console.log("PC connected");
    } else {
      console.log("PC error status: " + res.status);
      clearInterval(interval);
      address = null;
    }
  } catch (err) {
    console.log("PC disconnected");
    clearInterval(interval);
    address = null;
  }
}

// Get the saved IP
app.get("/get", (req, res) => {
  if (!address) {
    return res.status(404).json({ error: "No IP registered yet" });
  }
  res.json(address);
});

app.listen(PORT, () => {
  console.log(`Minimal IP server running on port ${PORT}`);
});
