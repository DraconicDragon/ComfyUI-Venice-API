import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "VeniceAI.CharCountNode",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CharCountTextBox") {
            // Store the original onConfigure method
            const onConfigure = nodeType.prototype.onConfigure;

            nodeType.prototype.onConfigure = function () {
                onConfigure?.apply(this, arguments);
                
                // Button used like a label
                let charCountWidget = this.addWidget("button", "Char count: 0", "", null);
                
                // Poll for changes to input_text
                let lastText = "";
                setInterval(() => {
                    const inputText = this.widgets?.find(w => w.name === "input_text")?.value || "";
                    if (inputText !== lastText) {
                        lastText = inputText;
                        charCountWidget.name = `Char count: ${inputText.length}`;
                        this.setDirtyCanvas(true); // Refresh the canvas to update UI
                    }
                }, 1500); // Check every 500ms, 0 clue if good approach or not but it works
            };
        }
    },
});
