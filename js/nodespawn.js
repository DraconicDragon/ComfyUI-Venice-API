import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "VeniceAI.NodeSpawn",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "GenerateImage_VENICE" || nodeData.name === "InpaintImage_VENICE") {
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
                        const response = await api.fetchApi("/veniceai/get_models_list");

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

                        modelWidget.options.values = data.image_models;
                        if (modelWidget.onChange) {
                            modelWidget.onChange();
                        }

                        this.setDirtyCanvas(true);
                    } catch (error) {
                        console.error("(VeniceAI.NodeSpawn) Failed to fetch image models:", error);
                        alert(`(VeniceAI.NodeSpawn) Failed to fetch image models:\n${error}`);
                    }
                }

                // Find the styles widget
                const stylesWidget = this.widgets.find(w => w.name === "style_preset");
                if (stylesWidget) {
                    try {
                        console.log("(VeniceAI.NodeSpawn) Trying to fetch styles...");
                        const response = await api.fetchApi("/veniceai/get_styles_list");

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

                        stylesWidget.options.values = data.data;
                        if (stylesWidget.onChange) {
                            stylesWidget.onChange();
                        }

                        this.setDirtyCanvas(true);
                    } catch (error) {
                        console.error("(VeniceAI.NodeSpawn) Failed to fetch styles:", error);
                        alert(`(VeniceAI.NodeSpawn) Failed to fetch styles:\n${error}`);
                    }
                }
            };
        }

        if (nodeData.name === "GenerateText_VENICE" || nodeData.name === "GenerateTextAdvanced_VENICE") {
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
                        const response = await api.fetchApi("/veniceai/get_models_list");

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

                        modelWidget.options.values = data.text_models;
                        if (modelWidget.onChange) {
                            modelWidget.onChange();
                        }

                        this.setDirtyCanvas(true);
                    } catch (error) {
                        console.error("(VeniceAI.NodeSpawn) Failed to fetch text models:", error);
                        alert(`(VeniceAI.NodeSpawn) Failed to fetch text models:\n${error}`);
                    }
                }

                // Find the character_slug widget // TODO: move this to a separate node depending on how character slugs are used (if model dependent eg)
                // const characterSlugWidget = this.widgets.find(w => w.name === "model");
                // if (characterSlugWidget) {
                //     try {
                //         console.log("(VeniceAI.NodeSpawn) Trying to fetch character slugs...");
                //         const response = await api.fetchApi("/veniceai/get_characters_list");

                //         if (!response.ok) {
                //             throw new Error(`HTTP error: ${response.status} ${response.statusText}`);
                //         }

                //         const rawText = await response.text();

                //         let data;
                //         try {
                //             data = JSON.parse(rawText);
                //         } catch (jsonError) {
                //             throw new Error(`Failed to parse JSON: ${jsonError.message}. Raw response: ${rawText}`);
                //         }

                //         characterSlugWidget.options.values = data.characters; // todo: implement on python side
                //         if (characterSlugWidget.onChange) {
                //             characterSlugWidget.onChange();
                //         }

                //         this.setDirtyCanvas(true);
                //     } catch (error) {
                //         console.error("(VeniceAI.NodeSpawn) Failed to fetch character slugs:", error);
                //         alert(`(VeniceAI.NodeSpawn) Failed to fetch character slugs:\n${error}`);
                //     }
                // }
            };
        }
    }
});
