function getBlockTemplate(
	type:
		| "html"
		| "text"
		| "image"
		| "container"
		| "body"
		| "fit-container"
		| "fallback-component"
		| "repeater"
		| "video",
): BlockOptions {
	switch (type) {
		case "html":
			return {
				name: "HTML",
				element: "div",
				originalElement: "__raw_html__",
				innerHTML: `<div style="color: #8e8e8e;background: #f4f4f4;display:flex;flex-direction:column;position:static;top:auto;left:auto;width: 200px;height: 155px;align-items:center;font-size:18px;justify-content:center"><p>&lt;paste html&gt;</p></div>`,
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
					fontSize: "16px",
					width: "fit-content",
					height: "fit-content",
					lineHeight: "1.4",
					minWidth: "10px",
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
					flexShrink: 0,
					overflow: "hidden",
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
					flexShrink: 0,
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
					flexShrink: 0,
					height: "fit-content",
					width: "fit-content",
					overflow: "hidden",
				} as BlockStyleMap,
			};
		case "fallback-component":
			return {
				name: "HTML",
				element: "p",
				originalElement: "__raw_html__",
				innerHTML: `<div style="color: red;background: #f4f4f4;display:flex;flex-direction:column;position:static;top:auto;left:auto;width: 600px;height: 275px;align-items:center;font-size: 30px;justify-content:center"><p>Component missing</p></div>`,
				baseStyles: {
					height: "fit-content",
					width: "fit-content",
				} as BlockStyleMap,
			};
		case "repeater":
			return {
				name: "Repeater",
				element: "div",
				blockName: "repeater",
				baseStyles: {
					display: "flex",
					flexDirection: "column",
					width: "100%",
					flexShrink: 0,
					minHeight: "300px",
					overflow: "hidden",
				} as BlockStyleMap,
				isRepeaterBlock: true,
			};
		case "video":
			return {
				name: "Video",
				element: "video",
				attributes: {
					autoplay: "",
					muted: "",
				} as BlockAttributeMap,
				baseStyles: {
					objectFit: "cover",
				} as BlockStyleMap,
			};
	}
}

export default getBlockTemplate;
