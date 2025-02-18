import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "VeniceAI.Startup",

    async setup() {
        // Load saved value from server on startup
        console.log("(VeniceAI.Startup) Fetching VeniceAI API key from config file...");
        const api_key_response = await api.fetchApi("/veniceai/get_apikey");
        const savedKey = await api_key_response.json();

        // update the settings UI
        console.log("(VeniceAI.Startup) Setting VeniceAI API key...");
        app.extensionManager.setting.set("VeniceAI.apikey", savedKey.apikey);

        // update the model list
        console.log("(VeniceAI.Startup) Fetching model list...");
        //alert("fetching model list")
        const response = await api.fetchApi("/veniceai/update_model_list");
        const data = await response.json();
        //alert(`response status ${JSON.stringify(data)}`);
        if (data.error) {
            alert(`${data.message}`);
            console.log(`(VeniceAI.Startup) ${data.message}`);
        }
    },
});