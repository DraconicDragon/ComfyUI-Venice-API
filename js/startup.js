import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "VeniceAI.Startup",

    async setup() {
        try {
            console.log("(VeniceAI.Startup) Fetching VeniceAI API key from config file...");
            const api_key_response = await api.fetchApi("/veniceai/get_apikey");
            const savedKey = await api_key_response.json();
            app.extensionManager.setting.set("VeniceAI.apikey", savedKey.apikey);
        } catch (error) {
            console.error("(VeniceAI.Startup) Failed to load Venice API key", error);
        }
    },
});