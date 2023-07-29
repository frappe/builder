let current = 0;
function getBlockTemplate(type: "html" | "text" | "image" | "container" | "body"): BlockOptions {
	switch (type) {
		case "html":
			return {
				name: "HTML",
				element: "div",
				originalElement: "__raw_html__",
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
			current++;
			return {
				name: "Container",
				element: "div",
				blockName: "container",
				baseStyles: {
					background: ["#A3A3A3", "#F3F3F3", "#E2E2E2", "#C7C7C7"][current % 4],
					display: "flex",
					flexDirection: "column",
				} as BlockStyleMap,
			};
		case "body":
			return {
				element: "div",
				originalElement: "body",
				attributes: {} as BlockAttributeMap,
				baseStyles: {
					display: "flex",
					flexWrap: "wrap",
					flexDirection: "column",
				} as BlockStyleMap,
				blockId: "root",
			};
	}
}

export default getBlockTemplate;
