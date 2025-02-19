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
                        console.log("(VeniceAI.NodeSpawn) Trying to fetch image models...");
                        // Fetch available models from json list
                        const response = await api.fetchApi("/veniceai/get_models_list");
                        //alert(`response status ${response.status}`);

                        const rawText = await response.text();

                        const data = JSON.parse(rawText);
                        //alert(`Parsed response: ${JSON.stringify(data)}`);

                        // Update widget options with image models only
                        modelWidget.options.values = data.image_models;
                        // Set the first value in data.text_models as the selected value
                        // if (data.image_models.length > 0) {
                        //     modelWidget.value = data.image_models[0]; // Select the first model
                        // }

                        // Properly refresh the widget
                        if (modelWidget.onChange) {
                            modelWidget.onChange();
                        }


                        // Force UI update
                        this.setDirtyCanvas(true);
                        //alert(`success? ${data.image_models}`);
                    } catch (error) {
                        console.error("(VeniceAI.NodeSpawn) Failed to fetch image models:", error);
                        alert(`(VeniceAI.NodeSpawn) Failed to fetch image models: ${error}`);
                    }
                }

                // Find the model widget
                const stylesWidget = this.widgets.find(w => w.name === "style_preset");
                if (stylesWidget) {
                    try {
                        console.log("(VeniceAI.NodeSpawn) Trying to fetch styles...");
                        // Fetch available models from json list
                        const response = await api.fetchApi("/veniceai/get_styles_list");
                        //alert(`response status ${response.status}`);

                        const rawText = await response.text();

                        const data = JSON.parse(rawText);

                        //alert(`Parsed response: ${JSON.stringify(data)}`);

                        // Update widget styles
                        stylesWidget.options.values = data.data;
                        // Set the first value in data.text_models as the selected value
                        // if (data.data.length > 0) {
                        //     stylesWidget.value = data.data[0]; // Select the first model
                        // }

                        // Properly refresh the widget
                        if (stylesWidget.onChange) {
                            stylesWidget.onChange();
                        }


                        // Force UI update
                        this.setDirtyCanvas(true);
                        //alert(`success? ${data.image_models}`);
                    } catch (error) {
                        console.error("(VeniceAI.NodeSpawn) Failed to fetch styles:", error);
                        alert(`(VeniceAI.NodeSpawn) Failed to fetch styles: ${error}`);
                    }
                }
            };
        }


        if (nodeData.name === "GenerateText_VENICE") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = async function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.apply(this);
                }
                // Find the model widget
                const modelWidget = this.widgets.find(w => w.name === "model");
                if (modelWidget) {
                    try {
                        console.log("(VeniceAI.NodeSpawn) Trying to fetch text models...");
                        // Fetch available models from json list
                        const response = await api.fetchApi("/veniceai/get_models_list");
                        //alert(`response status ${response.status}`);

                        const rawText = await response.text();

                        const data = JSON.parse(rawText);
                        //alert(`Parsed response: ${JSON.stringify(data)}`);

                        // Update widget options with image models only
                        modelWidget.options.values = data.text_models;
                        // Set the first value in data.text_models as the selected value
                        // if (data.text_models.length > 0) {
                        //     modelWidget.value = data.text_models[0]; // Select the first model
                        // }

                        // Properly refresh the widget
                        if (modelWidget.onChange) {
                            modelWidget.onChange();
                        }


                        // Force UI update
                        this.setDirtyCanvas(true);
                        //alert(`success? ${data.image_models}`);
                    } catch (error) {
                        console.error("(VeniceAI.NodeSpawn) Failed to fetch text models:", error);
                        alert(`(VeniceAI.NodeSpawn) Failed to fetch text models: ${error}`);
                    }
                }
            };
        }
    }
});