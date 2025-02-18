import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "VeniceAI.NodeSpawn",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "GenerateImage_VENICE") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = async function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.apply(this);
                }
                // Find the model widget
                const modelWidget = this.widgets.find(w => w.name === "model");
                if (modelWidget) {
                    try {
                        // Fetch available models from API
                        const response = await api.fetchApi("/veniceai/get_model_list");
                        //alert(`response status ${response.status}`);

                        const rawText = await response.text();

                        const data = JSON.parse(rawText);
                        //alert(`Parsed response: ${JSON.stringify(data)}`);

                        // Update widget options with image models only
                        modelWidget.options.values = data.image_models;


                        // Properly refresh the widget
                        if (modelWidget.onChange) {
                            modelWidget.onChange();
                        }

                        // Force UI update
                        this.setDirtyCanvas(true);
                        //alert(`success? ${data.image_models}`);
                    } catch (error) {
                        console.error("Failed to fetch VeniceAI models:", error);
                        alert(`error ${error}`);
                    }
                }
            };
        }
    }
});