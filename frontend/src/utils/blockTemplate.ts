function getBlockTemplate(
	type: "html" | "text" | "image" | "container" | "body" | "fit-container"
): BlockOptions {
	switch (type) {
		case "html":
			return {
				name: "HTML",
				element: "div",
				originalElement: "__raw_html__",
				innerHTML: `<div style="color: #8e8e8e;background: #f4f4f4;display:flex;flex-direction:column;position:static;top:auto;left:auto;width: 600px;height: 275px;align-items:center;font-size: 30px;justify-content:center"><p>&lt;paste html&gt;</p></div>`,
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
					fontSize: "30px",
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
				element: "div",
				blockName: "container",
				baseStyles: {
					display: "flex",
					flexDirection: "column",
				} as BlockStyleMap,
			};
		case "body":
			return {
				element: "div",
				originalElement: "body",
				attributes: {} as BlockAttributeMap,
				editorStyles: {
					paddingBottom: "100px",
				} as BlockStyleMap,
				baseStyles: {
					display: "flex",
					flexWrap: "wrap",
					flexDirection: "column",
					alignItems: "center",
				} as BlockStyleMap,
				blockId: "root",
			};

		case "fit-container":
			return {
				name: "Container",
				element: "div",
				blockName: "container",
				baseStyles: {
					display: "flex",
					flexDirection: "column",
					height: "fit-content",
					width: "fit-content",
				} as BlockStyleMap,
			};
	}
}

export default getBlockTemplate;
