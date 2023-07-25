let current = 0;
function getBlockTemplate(type: "html" | "text" | "image" | "container") {
	switch (type) {
		case "html":
			return {
				name: "HTML",
				element: "div",
				originalElement: "__html__",
				innerHTML: "<p>HTML</p>",
				baseStyles: {
					height: "fit-content",
					width: "fit-content",
				} as BlockStyleMap,
			};
		case "text":
			return {
				name: "Text",
				element: "p",
				innerHTML: "Text",
				baseStyles: {
					fontSize: "40px",
					width: "fit-content",
					height: "fit-content",
					lineHeight: "1",
					minWidth: "30px",
				} as BlockStyleMap,
			};
		case "image":
			return {
				name: "Image",
				element: "img",
				baseStyles: {
					objectFit: "cover",
				} as BlockStyleMap,
			};
		case "container":
			return {
				name: "Container",
				element: "section",
				baseStyles: {
					background: ["#F3F3F3", "#EDEDED", "#E2E2E2", "#C7C7C7"][current % 4],
					display: "flex",
				} as BlockStyleMap,
			};
	}
}

export default getBlockTemplate;
