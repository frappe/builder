from builder.builder.doctype.builder_variable.builder_variable import get_css_variables


def get_context(context):
	css_variables, dark_mode_css_variables = get_css_variables()
	context.css_variables = css_variables
	context.dark_mode_css_variables = dark_mode_css_variables
