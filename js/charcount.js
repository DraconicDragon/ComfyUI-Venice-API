import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "VeniceAI.CharCountNode",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "CharCountTextBox") {
            // Store the original onConfigure method
            const onConfigure = nodeType.prototype.onConfigure;

            nodeType.prototype.onNodeCreated = function () {
                onConfigure?.apply(this, arguments);
                
                // Button used like a label
                let charCountWidget = { type: "button", name: "Character count: 0", callback: () => {
                    alert("u stinky");
                    alert(`aaaa ${app.extensionManager.setting.get('example.number')}`);
                } };
                this.widgets.splice(0, 0, charCountWidget); // Insert at the top of the widget list
                
                // Poll for changes to input_text
                let lastText = "";
                setInterval(() => {
                    const inputText = this.widgets?.find(w => w.name === "input_text")?.value || "";
                    if (inputText !== lastText) {
                        lastText = inputText;
                        charCountWidget.name = `Character count: ${inputText.length}`;
                        this.setDirtyCanvas(true); // Refresh the canvas to update UI
                    }
                }, 1200); // Check every 1200ms, 0 clue if good approach or not but it works
                // check https://docs.comfy.org/custom-nodes/javascript_examples#capture-ui-events for better approach?
            };
        }
    },
});
