import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";

app.registerExtension({
	name: "VeniceAI.Settings",
	settings: [
		{
			category: ["VeniceAI", "API Key", "VeniceAI API Key"],
			id: "VeniceAI.apikey",
			name: "VeniceAI API Key",
			type: "text",
			defaultValue: "your_venice_api_key_here",
			tooltip: "Enter your VeniceAI API Key/Bearer Token here",
			attrs: {
				type: "password",
			},
			onChange: async (newVal) => {
				api.fetchApi("/veniceai/save_apikey", {
					method: "POST",
					body: JSON.stringify({ apikey: newVal }),
				});
			}
		},
	],
});
