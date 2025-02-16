import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
	name: "VeniceAI.Settings",
	settings: [
		{
			id: "VeniceAI.apikey",
			name: "VeniceAI API Key",
			type: "text",
			defaultValue: "your_venice_api_key_here",
			tooltip: "Enter your VeniceAI API Bearer Token Key here",
			onChange: async (newVal) => {
				api.fetchApi("/veniceai/save_apikey", {
					method: "POST",
					body: JSON.stringify({ apikey: newVal }),
				});
			}
		},
	],

	async setup() {
		// Load saved value from server on startup
		const response = await api.fetchApi("/veniceai/get_apikey");
		const savedKey = await response.json();

		// Update the settings UI
		app.extensionManager.setting.set("VeniceAI.apikey", savedKey.apikey);
	}
});

