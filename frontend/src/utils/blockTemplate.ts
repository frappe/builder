function getBlockTemplate(
	type:
		| "html"
		| "text"
		| "image"
		| "container"
		| "body"
		| "fit-container"
		| "missing-component"
		| "loading-component"
		| "empty-component"
		| "repeater"
		| "video"
		| "input"
		| "select",
	options: { [key: string]: string | number | { [key: string]: string }[] } = {},
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
					flexShrink: 0,
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
		case "missing-component":
			return {
				name: "HTML",
				element: "p",
				originalElement: "__raw_html__",
				innerHTML: `<div style="color:#E86C13;background:#F8F8F8;display:flex;width:300px;height:150px;align-items:center;font-size:16px;justify-content:center"><p>Component Missing</p></div>`,
				baseStyles: {
					height: "fit-content",
					width: "fit-content",
				} as BlockStyleMap,
			};
		case "loading-component":
			return {
				name: "HTML",
				element: "p",
				originalElement: "__raw_html__",
				innerHTML: `<div style="color:#525252;background:#F8F8F8;display:flex;width:300px;height:150px;align-items:center;font-size:16px;justify-content:center"><p>Loading...</p></div>`,
				baseStyles: {
					height: "fit-content",
					width: "fit-content",
				} as BlockStyleMap,
			};
		case "empty-component":
			return {
				name: "HTML",
				element: "div",
				baseStyles: {
					height: "100px",
					width: "100px",
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
		case "input": {
			const attr = getAttributesFromDocumentField(options);
			return {
				name: "Input",
				element: "input",
				attributes: attr.attributes,
				baseStyles: {
					borderColor: "#c9c9c9",
					borderRadius: "4px",
					borderStyle: "solid",
					borderWidth: "1px",
					fontSize: "14px",
					height: "32px",
					width: "100%",
				} as BlockStyleMap,
				customAttributes: attr.customAttributes,
			};
		}
		case "select": {
			const selectOptions = getSelectOptionsFromDocumentField(options);
			const attr = getAttributesFromDocumentField(options);
			return {
				name: "Select",
				element: "select",
				children: selectOptions,
				attributes: attr.attributes,
				baseStyles: {
					borderColor: "#c9c9c9",
					borderRadius: "4px",
					borderStyle: "solid",
					borderWidth: "1px",
					fontSize: "14px",
					height: "32px",
					width: "100%",
				} as BlockStyleMap,
				customAttributes: attr.customAttributes,
			};
		}
		case "textarea": {
			const { attributes, customAttributes } = getAttributesFromDocumentField(options);
			return {
				name: "Textarea",
				element: "textarea",
				attributes,
				baseStyles: {
					borderColor: "#c9c9c9",
					borderRadius: "4px",
					borderStyle: "solid",
					borderWidth: "1px",
					fontSize: "14px",
					height: "100px",
					width: "100%",
				} as BlockStyleMap,
				customAttributes,
			};
		}
	}
}

export default getBlockTemplate;

function getAttributesFromDocumentField(df: any) {
	const attributes = {
		type: df.input_type || "text",
		placeholder: df.label,
	} as BlockAttributeMap;
	const customAttributes = {
		name: df.fieldname,
		required: df.reqd ? "true" : "false",
		"data-fieldname": df.fieldname,
	} as BlockAttributeMap;
	return { attributes, customAttributes };
}

function getSelectOptionsFromDocumentField(df: any) {
	return df.options.split("\n").map((option: string) => {
		return {
			element: "option",
			innerHTML: option,
			attributes: { value: option } as BlockAttributeMap,
		};
	});
}

