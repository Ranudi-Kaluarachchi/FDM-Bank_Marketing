// Entry point: mounts the React app into the <div id="root"> in index.html.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  // StrictMode runs extra checks in development to surface common React bugs.
  <StrictMode>
    <App />
  </StrictMode>,
);
