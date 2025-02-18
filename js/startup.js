import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "VeniceAI.Startup",

    async setup() {
        // Load saved value from server on startup
        console.log("Fetching API key from config file...");
        const api_key_response = await api.fetchApi("/veniceai/get_apikey");
        const savedKey = await api_key_response.json();

        // update the settings UI
        app.extensionManager.setting.set("VeniceAI.apikey", savedKey.apikey);

        // update the model list
        console.log("Fetching model list...");
        //alert("fetching model list")
        await api.fetchApi("/veniceai/update_model_list");
    }
});