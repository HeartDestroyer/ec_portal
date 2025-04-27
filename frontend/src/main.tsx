import { createRoot } from "react-dom/client";
import "antd/dist/reset.css";
import App from "./App";
import "./index.css";

const rootElement = document.getElementById("root");

if (!rootElement) {
    throw new Error("Элемент root не найден");
}

const root = createRoot(rootElement);
root.render(
    <App />
);
