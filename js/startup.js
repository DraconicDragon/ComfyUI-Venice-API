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
        app.extensionManager.setting.set("VeniceAI.apikey", savedKey.apikey);

        try {
            // update the model list
            console.log("(VeniceAI.Startup) Updating model list...");
            //alert("fetching model list")
            const response = await api.fetchApi("/veniceai/update_models_list");
            const data = await response.json();
            //alert(`response status ${JSON.stringify(data)}`);
            if (data.error) {
                alert(`${data.message}`);
                console.log(`(VeniceAI.Startup) ${data.message}`);
            }
            else{
                // update the style list if not model list error
                console.log("(VeniceAI.Startup) Updating styles list...");
                //alert("fetching styles list")
                const response_s = await api.fetchApi("/veniceai/update_styles_list");
                //alert(`response status ${await response_s.text()}`);
                const data_s = await response_s.json();
                if (data_s.error) {
                    alert(`${data_s.message}`);
                    console.log(`(VeniceAI.Startup) ${data_s.message}`);
                }

                // update the characters list
                console.log("(VeniceAI.Startup) Updating characters list...");
                const response_c = await api.fetchApi("/veniceai/update_characters_list");
                const data_c = await response_c.json();
                if (data_c.error) {
                    alert(`${data_c.message}`);
                    console.log(`(VeniceAI.Startup) ${data_c.message}`);
                }
            }
        } catch (error) {
            // Handle any unexpected errors
            alert(`(VeniceAI.Startup) Unexpected Error: ${error.message}`);
            console.error("(VeniceAI.Startup) Unexpected Error:", error);
        }

    },
});