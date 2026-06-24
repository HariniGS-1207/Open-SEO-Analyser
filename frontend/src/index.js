// frontend/src/index.js
import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./app";

// Create the root element (React 18+)
const root = ReactDOM.createRoot(document.getElementById("root"));

// Render your main app
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
