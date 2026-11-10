import type Block from "@/block";
import useBlockTemplateStore from "@/stores/blockTemplateStore";
import useCanvasStore from "@/stores/canvasStore";
import { __ } from "@/translation";
import { escapeHtml, getBlockInstance, getBlockObject } from "@/utils/helpers";
import { createResource, toast } from "frappe-ui";

interface FormFieldSchema {
	fieldname: string;
	label: string;
	fieldtype: string;
	options?: string;
	reqd: boolean;
}

interface DoctypeField {
	fieldname: string;
	label: string;
	fieldtype: string;
	options?: string;
	needed: boolean;
	suggested: boolean;
}

// the DocType field an input type is saved as; the rest are saved as Data
const FIELDTYPES: Record<string, string> = {
	checkbox: "Check",
	date: "Date",
	time: "Time",
	"datetime-local": "Datetime",
	password: "Password",
	color: "Color",
};

// the input type a field is added with; a field of any other type, like a Link, isn't added
const INPUT_TYPES: Record<string, string> = {
	Data: "text",
	"Small Text": "text",
	Text: "text",
	"Long Text": "text",
	Int: "number",
	Float: "number",
	Currency: "number",
	Percent: "number",
	Date: "date",
	Time: "time",
	Datetime: "datetime-local",
	Password: "password",
	Color: "color",
	Phone: "tel",
};

const LONG_TEXT_FIELDTYPES = new Set(["Small Text", "Text", "Long Text"]);

const DECIMAL_FIELDTYPES = new Set(["Float", "Currency", "Percent"]);

// the Form parts block template a choice field is added from
const FIELD_TEMPLATES: Record<string, string> = {
	Select: "Select",
	Autocomplete: "Select",
	Check: "Checkbox",
};

const SUBMIT_BUTTON_TEMPLATE = "Form 1";

// inputs that only act on the form, and files, which a submission can't carry
const SKIPPED_INPUT_TYPES = new Set(["submit", "reset", "button", "image", "file"]);

// the fields a form submits, in order; a radio group is one field
function getFormFields(block: Block): Block[] {
	return block.getChildren().flatMap((child) => {
		if (child.isRadioGroup() || child.isSelect()) return [child];
		if (child.isInput()) {
			const skipped =
				child.isRadio() || SKIPPED_INPUT_TYPES.has(child.getEffectiveAttribute("type") as string);
			return skipped ? [] : [child];
		}
		return getFormFields(child);
	});
}

function getFieldSchema(field: Block): FormFieldSchema {
	return {
		fieldname: getFieldName(field),
		label: getFieldLabel(field),
		fieldtype: getFieldType(field),
		options: getFieldOptions(field),
		reqd: field.isRadioGroup() ? field.isGroupRequired() : field.getEffectiveAttribute("required") != null,
	};
}

// a submission is saved by input name, so each input is named after the field it saves to
function nameFormFields(fields: Block[], fieldnames: string[]) {
	fields.forEach((field, index) =>
		getNamedBlocks(field).forEach((block) => block.setEffectiveAttribute("name", fieldnames[index])),
	);
}

// a submission is saved by input name, so a picked DocType is checked against the form's inputs
async function checkFormDoctype(form: Block, doctype: string, createDoctype?: () => void) {
	const fields = await createResource({ url: "builder.api.get_form_doctype_fields" }).submit({ doctype });
	const check = new FormDoctypeCheck(form, doctype, fields, createDoctype);
	if (check.describe()) check.warn();
}

// checked again on publish, since a form can drift from its DocType after it was picked
function checkPageForms(root: Block) {
	for (const form of getForms(root)) {
		if (!hasButton(form)) warnNoSubmitButton(form);
		if (hasFileInput(form)) warnFileInput(form);
		const destinations = form.getFormDestinations().filter((destination) => destination.value);
		const doctype = destinations.find((destination) => destination.type === "doctype")?.value;
		if (doctype) checkFormDoctype(form, doctype);
		else if (!destinations.length && !form.getEffectiveAttribute("action")) warnUnsentForm(form);
	}
}

const getForms = (block: Block): Block[] =>
	block.isForm() ? [block] : block.getChildren().flatMap(getForms);

function warnUnsentForm(form: Block) {
	toast.warning(__("A form on this page doesn't send its submissions anywhere"), {
		id: "form-unsent",
		description: __("Add an email, webhook or DocType in its Send to, or visitors' answers are lost."),
		duration: Infinity,
		action: { label: __("Select form"), onClick: () => useCanvasStore().selectBlock(form, null, true, true) },
	});
}

// the Button block is a link, which doesn't submit, so a form that lost its button has none to drop in
function warnNoSubmitButton(form: Block) {
	toast.warning(__("A form on this page has no submit button"), {
		id: "form-no-submit-button",
		description: __("Visitors can't send it."),
		duration: Infinity,
		action: { label: __("Add button"), onClick: () => addSubmitButton(form) },
	});
}

const hasFileInput = (block: Block): boolean =>
	block
		.getChildren()
		.some(
			(child) => (child.isInput() && child.getEffectiveAttribute("type") === "file") || hasFileInput(child),
		);

function warnFileInput(form: Block) {
	toast.warning(__("A form on this page has a file input"), {
		id: "form-file-input",
		description: __("Submissions don't carry files, so whatever visitors upload is lost."),
		duration: Infinity,
		action: { label: __("Select form"), onClick: () => useCanvasStore().selectBlock(form, null, true, true) },
	});
}

// the Basic Forms templates' button, with its Sending, Success and Error variants
async function addSubmitButton(form: Block) {
	await useBlockTemplateStore().fetchBlockTemplate(SUBMIT_BUTTON_TEMPLATE);
	const template = useBlockTemplateStore().getBlockTemplate(SUBMIT_BUTTON_TEMPLATE);
	const button = getBlockInstance(template.block, false).getChildren().find(isButton);
	if (button) form.addChild(getBlockObject(button), null);
}

class FormDoctypeCheck {
	constructor(
		private form: Block,
		private doctype: string,
		private fields: DoctypeField[],
		// offered in place of a fix when the form can't fill a needed field
		private createDoctype?: () => void,
	) {}

	// an input named after no field isn't saved
	getDropped() {
		return getFormFields(this.form).filter(
			(input) => !this.fields.some((df) => df.fieldname === getFieldName(input)),
		);
	}

	// what Fix form will change, or why no change to the form can make its submissions save
	describe() {
		const { renames, additions, unfillable, removals } = this.planFix();
		if (unfillable.length) {
			return __("A form can't fill in {0}.", [listLabels(unfillable.map((df) => df.label))]);
		}
		const changes = [
			additions.length && __("adds {0}", [listLabels(additions.map((df) => df.label))]),
			renames.size &&
				__("saves {0}", [listLabels([...renames].map(([input, df]) => describeRename(input, df)))]),
			removals.length && __("removes {0}", [listLabels(removals.map(getInputLabel))]),
		].filter(Boolean) as string[];
		return changes.length ? __("Fix form {0}.", [joinWithAnd(changes)]) : "";
	}

	// the inputs to rename after the field they match or remove, the needed and suggested fields to add
	// an input for, and the needed ones no input can be added for, like a Link
	planFix() {
		const taken = new Set(getFormFields(this.form).map(getFieldName));
		const renames = new Map<Block, DoctypeField>();
		const dropped = this.getDropped();
		for (const matches of FIELD_MATCHERS) {
			for (const input of dropped.filter((input) => !renames.has(input))) {
				const df = this.fields.find((df) => !taken.has(df.fieldname) && matches(input, df));
				if (!df) continue;
				renames.set(input, df);
				taken.add(df.fieldname);
			}
		}
		const remaining = this.fields.filter((df) => (df.needed || df.suggested) && !taken.has(df.fieldname));
		const additions = remaining.filter((df) => canAddField(this.form, df));
		const unfillable = remaining.filter((df) => df.needed && !additions.includes(df));
		const removals = dropped.filter((input) => !renames.has(input));
		return { renames, additions, unfillable, removals };
	}

	warn() {
		toast.warning(__("This form doesn't match {0}", [this.doctype]), {
			// picking another DocType replaces the warning
			id: "form-doctype-check",
			description: this.describe(),
			duration: Infinity,
			action: this.getAction(),
		});
	}

	// a fix can't make submissions save while a needed field stays empty, so a new DocType is offered instead
	getAction() {
		const { renames, additions, unfillable, removals } = this.planFix();
		if (unfillable.length) {
			return this.createDoctype && { label: __("New DocType"), onClick: this.createDoctype };
		}
		if (renames.size || additions.length || removals.length) {
			return { label: __("Fix form"), onClick: () => this.fix() };
		}
	}

	async fix() {
		const { renames, additions, removals } = this.planFix();
		const removed = removals.map(getInputLabel);
		// fetched first, so the changes below land together and undo in one step
		const templates = additions.map((df) => FIELD_TEMPLATES[df.fieldtype]).filter(Boolean);
		await Promise.all(templates.map((name) => useBlockTemplateStore().fetchBlockTemplate(name)));
		renames.forEach((df, input) => nameFormFields([input], [df.fieldname]));
		// added before the removals, which may take the only input to copy
		additions.forEach((df) => addFormInput(this.form, df));
		removals.forEach((input) => removeFormField(this.form, input));
		// a new toast, since the warning closes once its action runs
		toast.success(__("The form now matches {0}", [this.doctype]), {
			description: removed.length ? __("Removed {0}.", [listLabels(removed)]) : undefined,
		});
	}
}

const getInputLabel = (input: Block) => getFieldLabel(input) || getFieldName(input) || __("Unnamed input");

// the field's label is only worth naming when it reads differently from the input's
const describeRename = (input: Block, df: DoctypeField) => {
	const label = getInputLabel(input);
	return normalize(label) === normalize(df.label) ? label : __("{0} as {1}", [label, df.label]);
};

const listLabels = (labels: string[]) =>
	labels.length > 6
		? __("{0} and {1} more", [labels.slice(0, 5).join(", "), labels.length - 5])
		: labels.join(", ");

const joinWithAnd = (parts: string[]) =>
	parts.length > 1 ? __("{0} and {1}", [parts.slice(0, -1).join(", "), parts[parts.length - 1]]) : parts[0];

const normalize = (text: string) => text.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

// an input matches the field its name or label spells, or failing that, an email input an email field
const FIELD_MATCHERS = [
	(input: Block, df: DoctypeField) => {
		const keys = [df.label, df.fieldname].map(normalize);
		return [getFieldName(input), getFieldLabel(input)]
			.map(normalize)
			.some((key) => key && keys.includes(key));
	},
	(input: Block, df: DoctypeField) =>
		input.getEffectiveAttribute("type") === "email" && df.options === "Email",
];

// a Data field's options say what kind of text it holds
const DATA_INPUT_TYPES: Record<string, string> = { Email: "email", Phone: "tel", URL: "url" };

const getInputType = (df: DoctypeField) =>
	(df.fieldtype === "Data" && DATA_INPUT_TYPES[df.options || ""]) || INPUT_TYPES[df.fieldtype];

// one of the form's own text inputs, so an added one is styled the same
function getInputTemplate(form: Block, df: DoctypeField) {
	if (!getInputType(df)) return;
	const inputs = getFormFields(form).filter(
		(field) => field.isInput() && !field.isCheckable() && field.getEffectiveAttribute("type") !== "hidden",
	);
	return (
		(LONG_TEXT_FIELDTYPES.has(df.fieldtype) && inputs.find((input) => input.isTextarea())) ||
		inputs.find((input) => !input.isTextarea()) ||
		inputs[0]
	);
}

// a choice field comes from its block template, and a text field is copied from the form's own inputs
const canAddField = (form: Block, df: DoctypeField) =>
	df.fieldtype in FIELD_TEMPLATES
		? df.fieldtype === "Check" || Boolean(df.options?.trim())
		: Boolean(getInputTemplate(form, df));

// added after the last field, at the form's own level so it isn't put inside that field's row
function addFormInput(form: Block, df: DoctypeField) {
	const input = df.fieldtype in FIELD_TEMPLATES ? makeChoiceField(df) : copyTextInput(form, df);
	const last = getFormFields(form).at(-1);
	form.addChild(input, last ? form.getChildIndex(getFormChild(form, last)) + 1 : 0, false);
}

function copyTextInput(form: Block, df: DoctypeField) {
	const template = getInputTemplate(form, df) as Block;
	const attributes = {
		name: df.fieldname,
		placeholder: df.label,
		"aria-label": df.label,
		type: template.isTextarea() ? undefined : getInputType(df),
		step: DECIMAL_FIELDTYPES.has(df.fieldtype) ? "any" : undefined,
		required: df.needed ? "required" : undefined,
	};
	return getBlockInstance({ ...getBlockObject(template), attributes, customAttributes: {} }, false);
}

// a label holding the field's own text and its select or checkbox, as dropped from the blocks panel
function makeChoiceField(df: DoctypeField) {
	const template = useBlockTemplateStore().getBlockTemplate(FIELD_TEMPLATES[df.fieldtype]);
	const wrapper = getBlockInstance(template.block, false);
	const [field] = getFormFields(wrapper);
	wrapper
		.getChildren()
		.find((child) => child.isText())
		?.setInnerHTML(escapeHtml(df.label));
	field.setEffectiveAttribute("name", df.fieldname);
	field.setEffectiveAttribute("required", df.needed ? "required" : undefined);
	if (field.isSelect()) setSelectOptions(field, df);
	return wrapper;
}

// the template's placeholder option stays, and its sample options give way to the field's
function setSelectOptions(select: Block, df: DoctypeField) {
	select
		.getOptions()
		.filter((option) => option.getEffectiveAttribute("value") !== "")
		.forEach((option) => select.removeChild(option));
	(df.options || "")
		.split("\n")
		.filter(Boolean)
		.forEach((option) => select.addOption(escapeHtml(option)));
}

// with the label it sits in, but not a row it shares with other fields or the submit button
function removeFormField(form: Block, field: Block) {
	const wrapper = getFieldWrapper(form, field);
	wrapper.getParentBlock()?.removeChild(wrapper);
}

const getFieldWrapper = (form: Block, field: Block): Block => {
	const parent = field.getParentBlock() as Block;
	const ownsParent =
		parent.blockId !== form.blockId && getFormFields(parent).length === 1 && !hasButton(parent);
	return ownsParent ? getFieldWrapper(form, parent) : field;
};

const isButton = (block: Block) =>
	block.getElement() === "button" || block.getEffectiveAttribute("type") === "submit";

const hasButton = (block: Block): boolean =>
	block.getChildren().some((child) => isButton(child) || hasButton(child));

const getFormChild = (form: Block, block: Block): Block =>
	block.getParentBlock()?.blockId === form.blockId
		? block
		: getFormChild(form, block.getParentBlock() as Block);

const getFieldName = (field: Block) => String(getNamedBlocks(field)[0]?.getEffectiveAttribute("name") || "");

const getNamedBlocks = (field: Block) => (field.isRadioGroup() ? field.getRadios() : [field]);

function getFieldLabel(field: Block) {
	const label = field.getEffectiveAttribute("aria-label") || field.getEffectiveAttribute("placeholder");
	if (label) return String(label);
	// a radio group's heading, or the text of the <label> a select or checkbox sits in
	const labelled = field.isRadioGroup() ? field : field.getParentBlock();
	if (!labelled || !(field.isRadioGroup() || labelled.getElement() === "label")) return "";
	return labelled
		.getChildren()
		.filter((child) => child.isText())
		.map((child) => child.getTextContent())
		.join(" ")
		.trim();
}

function getFieldType(field: Block) {
	if (field.isRadioGroup() || field.isSelect()) return "Select";
	if (field.isTextarea()) return "Small Text";
	// a number input takes whole numbers unless its step allows decimals
	if (field.getEffectiveAttribute("type") === "number") {
		return /^\d+$/.test(String(field.getEffectiveAttribute("step") ?? "1")) ? "Int" : "Float";
	}
	return FIELDTYPES[field.getEffectiveAttribute("type") as string] || "Data";
}

function getFieldOptions(field: Block) {
	if (field.isRadioGroup()) {
		return field
			.getRadios()
			.map((radio) => radio.getEffectiveAttribute("value"))
			.filter(Boolean)
			.join("\n");
	}
	// an option without a value submits its label; the placeholder's empty value is no choice
	if (field.isSelect()) {
		return field
			.getOptions()
			.map((option) => option.getEffectiveAttribute("value") ?? option.getTextContent())
			.filter(Boolean)
			.join("\n");
	}
	if (field.getEffectiveAttribute("type") === "email") return "Email";
}

export { checkFormDoctype, checkPageForms, getFieldSchema, getFormFields, nameFormFields };
