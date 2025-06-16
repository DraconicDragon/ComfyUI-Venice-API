import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";


// Helper function to fetch data and assign to widget
async function fetchAndAssignWidget(widget, url, dataKey, logMsg, errorMsg) {
    if (!widget) return;
    try {
        console.log(`(VeniceAI.NodeSpawn) ${logMsg}`);
        const response = await api.fetchApi(url);

        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
        }

        const rawText = await response.text();

        let data;
        try {
            data = JSON.parse(rawText);
        } catch (jsonError) {
            throw new Error(`Failed to parse JSON: ${jsonError.message}. Raw response: ${rawText}`);
        }

        widget.options.values = data[dataKey];
        if (widget.onChange) {
            widget.onChange();
        }

        this.setDirtyCanvas(true);
    } catch (error) {
        console.error(`(VeniceAI.NodeSpawn) ${errorMsg}:`, error);
        alert(`(VeniceAI.NodeSpawn) ${errorMsg}:\n${error}`);
    }
}

app.registerExtension({
    name: "VeniceAI.NodeSpawn",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "GenerateImage_VENICE" || nodeData.name === "InpaintImage_VENICE") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = async function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.apply(this);
                }
                await fetchAndAssignWidget.call(
                    this,
                    this.widgets.find(w => w.name === "model"),
                    "/veniceai/get_models_list",
                    "image_models",
                    "Trying to fetch image models...",
                    "Failed to fetch image models"
                );
                await fetchAndAssignWidget.call(
                    this,
                    this.widgets.find(w => w.name === "style_preset"),
                    "/veniceai/get_styles_list",
                    "data",
                    "Trying to fetch styles...",
                    "Failed to fetch styles"
                );
            };
        }

        if (nodeData.name === "GenerateText_VENICE" || nodeData.name === "GenerateTextAdvanced_VENICE") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = async function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.apply(this);
                }
                await fetchAndAssignWidget.call(
                    this,
                    this.widgets.find(w => w.name === "model"),
                    "/veniceai/get_models_list",
                    "text_models",
                    "Trying to fetch text models...",
                    "Failed to fetch text models"
                );
            };
        }

        if (nodeData.name === "GenerateTextVeniceParameters_VENICE") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = async function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.apply(this);
                }
                await fetchAndAssignWidget.call(
                    this,
                    this.widgets.find(w => w.name === "character_slug"),
                    "/veniceai/get_characters_list",
                    "characters",
                    "Trying to fetch character slugs...",
                    "Failed to fetch character slugs"
                );
            };
        }

        if (nodeData.name === "GenerateSpeech_VENICE") {
            const originalOnNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = async function () {
                if (originalOnNodeCreated) {
                    originalOnNodeCreated.apply(this);
                }
                await fetchAndAssignWidget.call(
                    this,
                    this.widgets.find(w => w.name === "model"),
                    "/veniceai/get_models_list",
                    "tts_models",
                    "Trying to fetch tts models...",
                    "Failed to fetch tts models"
                );
                await fetchAndAssignWidget.call(
                    this,
                    this.widgets.find(w => w.name === "voice"),
                    "/veniceai/get_models_list",
                    "tts_voices",
                    "Trying to fetch tts voices...",
                    "Failed to fetch tts voices"
                );
            }
        }
    }
});

