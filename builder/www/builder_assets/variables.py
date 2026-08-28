# Compat route: pages published before the Builder Token rename link
# /builder_assets/variables.css. Serves the same CSS as tokens.css.
from builder.www.builder_assets.tokens import get_context

__all__ = ["get_context"]
