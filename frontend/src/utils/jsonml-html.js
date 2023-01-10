/*
	jsonml-html.js
	JsonML to HTML utility

	Created: 2006-11-09-0116
	Modified: 2012-11-24-1051

	Copyright (c)2006-2012 Stephen M. McKamey
	Distributed under The MIT License: http://jsonml.org/license

	This file ensures a global JsonML object adding these methods:

		JsonML.toHTML(JsonML, filter)

			This method produces a tree of DOM elements from a JsonML tree. The
			array must not contain any cyclical references.

			The optional filter parameter is a function which can filter and
			transform the results. It receives each of the DOM nodes, and
			its return value is used instead of the original value. If it
			returns what it received, then structure is not modified. If it
			returns undefined then the member is deleted.

			This is useful for binding unobtrusive JavaScript to the generated
			DOM elements.

			Example:

			// Parses the structure. If an element has a specific CSS value then
			// takes appropriate action: Remove from results, add special event
			// handlers, or bind to a custom component.

			var myUI = JsonML.toHTML(myUITemplate, function (elem) {
				if (elem.className.indexOf('Remove-Me') >= 0) {
					// this will remove from resulting DOM tree
					return null;
				}

				if (elem.tagName && elem.tagName.toLowerCase() === 'a' &&
					elem.className.indexOf('External-Link') >= 0) {
					// this is the equivalent of target='_blank'
					elem.onclick = function(evt) {
						window.open(elem.href); return false;
					};

				} else if (elem.className.indexOf('Fancy-Widgit') >= 0) {
					// bind to a custom component
					FancyWidgit.bindDOM(elem);
				}
				return elem;
			});

		JsonML.toHTMLText(JsonML)
			Converts JsonML to HTML text

		// Implement onerror to handle any runtime errors while binding:
		JsonML.onerror = function (ex, jml, filter) {
			// display inline error message
			return document.createTextNode('['+ex+']');
		};
*/

var JsonML = JsonML || {};

if (typeof module === 'object') {
	module.exports = JsonML;
}

(function(JsonML, document) {
	'use strict';

	/**
	 * Attribute name map
	 *
	 * @private
	 * @constant
	 * @type {Object.<string>}
	 */
	var ATTR_MAP = {
		'accesskey': 'accessKey',
		'bgcolor': 'bgColor',
		'cellpadding': 'cellPadding',
		'cellspacing': 'cellSpacing',
		'checked': 'defaultChecked',
		'class': 'className',
		'colspan': 'colSpan',
		'contenteditable': 'contentEditable',
		'defaultchecked': 'defaultChecked',
		'for': 'htmlFor',
		'formnovalidate': 'formNoValidate',
		'hidefocus': 'hideFocus',
		'ismap': 'isMap',
		'maxlength': 'maxLength',
		'novalidate': 'noValidate',
		'readonly': 'readOnly',
		'rowspan': 'rowSpan',
		'spellcheck': 'spellCheck',
		'tabindex': 'tabIndex',
		'usemap': 'useMap',
		'willvalidate': 'willValidate'
		// can add more attributes here as needed
	};

	/**
	 * Attribute duplicates map
	 *
	 * @private
	 * @constant
	 * @type {Object.<string>}
	 */
	var ATTR_DUP = {
		'enctype': 'encoding',
		'onscroll': 'DOMMouseScroll'
		// can add more attributes here as needed
	};

	/**
	 * Attributes to be set via DOM
	 *
	 * @private
	 * @constant
	 * @type {Object.<number>}
	 */
	var ATTR_DOM = {
		'autocapitalize': 1,
		'autocomplete': 1,
		'autocorrect': 1
		// can add more attributes here as needed
	};

	/**
	 * Boolean attribute map
	 *
	 * @private
	 * @constant
	 * @type {Object.<number>}
	 */
	var ATTR_BOOL = {
		'async': 1,
		'autofocus': 1,
		'checked': 1,
		'defaultchecked': 1,
		'defer': 1,
		'disabled': 1,
		'formnovalidate': 1,
		'hidden': 1,
		'indeterminate': 1,
		'ismap': 1,
		'multiple': 1,
		'novalidate': 1,
		'readonly': 1,
		'required': 1,
		'spellcheck': 1,
		'willvalidate': 1
		// can add more attributes here as needed
	};

	/**
	 * Leading SGML line ending pattern
	 *
	 * @private
	 * @constant
	 * @type {RegExp}
	 */
	var LEADING = /^[\r\n]+/;

	/**
	 * Trailing SGML line ending pattern
	 *
	 * @private
	 * @constant
	 * @type {RegExp}
	 */
	var TRAILING = /[\r\n]+$/;

	/**
	 * @private
	 * @const
	 * @type {number}
	 */
	var NUL = 0;

	/**
	 * @private
	 * @const
	 * @type {number}
	 */
	var FUN = 1;

	/**
	 * @private
	 * @const
	 * @type {number}
	 */
	var ARY = 2;

	/**
	 * @private
	 * @const
	 * @type {number}
	 */
	var OBJ = 3;

	/**
	 * @private
	 * @const
	 * @type {number}
	 */
	var VAL = 4;

	/**
	 * @private
	 * @const
	 * @type {number}
	 */
	var RAW = 5;

	/**
	 * Wraps a data value to maintain as raw markup in output
	 *
	 * @private
	 * @this {Markup}
	 * @param {string} value The value
	 * @constructor
	 */
	function Markup(value) {
		/**
		 * @type {string}
		 * @const
		 * @protected
		 */
		this.value = value;
	}

	/**
	 * Renders the value
	 *
	 * @public
	 * @override
	 * @this {Markup}
	 * @return {string} value
	 */
	Markup.prototype.toString = function() {
		return this.value;
	};

	/**
	 * @param {string} value
	 * @return {Markup}
	 */
	JsonML.raw = function(value) {
		return new Markup(value);
	};

	/**
	 * @param {*} value
	 * @return {boolean}
	 */
	var isMarkup = JsonML.isRaw = function(value) {
		return (value instanceof Markup);
	};

	/**
	 * Determines if the value is an Array
	 *
	 * @private
	 * @param {*} val the object being tested
	 * @return {boolean}
	 */
	var isArray = Array.isArray || function(val) {
		return (val instanceof Array);
	};

	/**
	 * Determines if the value is a function
	 *
	 * @private
	 * @param {*} val the object being tested
	 * @return {boolean}
	 */
	function isFunction(val) {
		return (typeof val === 'function');
	}

	/**
	 * Determines the type of the value
	 *
	 * @private
	 * @param {*} val the object being tested
	 * @return {number}
	 */
	function getType(val) {
		switch (typeof val) {
			case 'object':
				return !val ? NUL : (isArray(val) ? ARY : (isMarkup(val) ? RAW : ((val instanceof Date) ? VAL : OBJ)));
			case 'function':
				return FUN;
			case 'undefined':
				return NUL;
			default:
				return VAL;
		}
	}

	/**
	 * Creates a DOM element
	 *
	 * @private
	 * @param {string} tag The element's tag name
	 * @return {Node}
	 */
	var createElement = function(tag) {
		if (!tag) {
			// create a document fragment to hold multiple-root elements
			if (document.createDocumentFragment) {
				return document.createDocumentFragment();
			}

			tag = '';

		} else if (tag.charAt(0) === '!') {
			return document.createComment(tag === '!' ? '' : tag.substr(1)+' ');
		}

		if (tag.toLowerCase() === 'style' && document.createStyleSheet) {
			// IE requires this interface for styles
			return document.createStyleSheet();
		}

		return document.createElement(tag);
	};

	/**
	 * Adds an event handler to an element
	 *
	 * @private
	 * @param {Node} elem The element
	 * @param {string} name The event name
	 * @param {function(Event)} handler The event handler
	 */
	var addHandler = function(elem, name, handler) {
		if (name.substr(0,2) === 'on') {
			name = name.substr(2);
		}

		switch (typeof handler) {
			case 'function':
				if (elem.addEventListener) {
					// DOM Level 2
					elem.addEventListener(name, handler, false);

				} else if (elem.attachEvent && getType(elem[name]) !== NUL) {
					// IE legacy events
					elem.attachEvent('on'+name, handler);

				} else {
					// DOM Level 0
					var old = elem['on'+name] || elem[name];
					elem['on'+name] = elem[name] = !isFunction(old) ? handler :
						function(e) {
							return (old.call(this, e) !== false) && (handler.call(this, e) !== false);
						};
				}
				break;

			case 'string':
				// inline functions are DOM Level 0
				/*jslint evil:true */
				elem['on'+name] = new Function('event', handler);
				/*jslint evil:false */
				break;
		}
	};

	/**
	 * Appends an attribute to an element
	 *
	 * @private
	 * @param {Node} elem The element
	 * @param {Object} attr Attributes object
	 * @return {Node}
	 */
	var addAttributes = function(elem, attr) {
		if (attr.name && document.attachEvent && !elem.parentNode) {
			try {
				// IE fix for not being able to programatically change the name attribute
				var alt = createElement('<'+elem.tagName+' name="'+attr.name+'">');
				// fix for Opera 8.5 and Netscape 7.1 creating malformed elements
				if (elem.tagName === alt.tagName) {
					elem = alt;
				}
			} catch (ex) { }
		}

		// for each attributeName
		for (var name in attr) {
			if (attr.hasOwnProperty(name)) {
				// attributeValue
				var value = attr[name],
					type = getType(value);

				if (name) {
					if (type === NUL) {
						value = '';
						type = VAL;
					}

					name = ATTR_MAP[name.toLowerCase()] || name;

					if (name === 'style') {
						if (getType(elem.style.cssText) !== NUL) {
							elem.style.cssText = value;
						} else {
							elem.style = value;
						}

					} else if (name.substr(0,2) === 'on') {
						addHandler(elem, name, value);

						// also set duplicated events
						name = ATTR_DUP[name];
						if (name) {
							addHandler(elem, name, value);
						}

					} else if (!ATTR_DOM[name.toLowerCase()] && (type !== VAL || name.charAt(0) === '$' || getType(elem[name]) !== NUL || getType(elem[ATTR_DUP[name]]) !== NUL)) {
						// direct setting of existing properties
						elem[name] = value;

						// also set duplicated properties
						name = ATTR_DUP[name];
						if (name) {
							elem[name] = value;
						}

					} else if (ATTR_BOOL[name.toLowerCase()]) {
						if (value) {
							// boolean attributes
							elem.setAttribute(name, name);

							// also set duplicated attributes
							name = ATTR_DUP[name];
							if (name) {
								elem.setAttribute(name, name);
							}
						}

					} else {
						// http://www.quirksmode.org/dom/w3c_core.html#attributes

						// custom and 'data-*' attributes
						elem.setAttribute(name, value);

						// also set duplicated attributes
						name = ATTR_DUP[name];
						if (name) {
							elem.setAttribute(name, value);
						}
					}
				}
			}
		}
		return elem;
	};

	/**
	 * Appends a child to an element
	 *
	 * @private
	 * @param {Node} elem The parent element
	 * @param {Node} child The child
	 */
	var appendDOM = function(elem, child) {
		if (child) {
			var tag = (elem.tagName||'').toLowerCase();
			if (elem.nodeType === 8) { // comment
				if (child.nodeType === 3) { // text node
					elem.nodeValue += child.nodeValue;
				}
			} else if (tag === 'table' && elem.tBodies) {
				if (!child.tagName) {
					// must unwrap documentFragment for tables
					if (child.nodeType === 11) {
						while (child.firstChild) {
							appendDOM(elem, child.removeChild(child.firstChild));
						}
					}
					return;
				}

				// in IE must explicitly nest TRs in TBODY
				var childTag = child.tagName.toLowerCase();// child tagName
				if (childTag && childTag !== 'tbody' && childTag !== 'thead') {
					// insert in last tbody
					var tBody = elem.tBodies.length > 0 ? elem.tBodies[elem.tBodies.length-1] : null;
					if (!tBody) {
						tBody = createElement(childTag === 'th' ? 'thead' : 'tbody');
						elem.appendChild(tBody);
					}
					tBody.appendChild(child);
				} else if (elem.canHaveChildren !== false) {
					elem.appendChild(child);
				}

			} else if (tag === 'style' && document.createStyleSheet) {
				// IE requires this interface for styles
				elem.cssText = child;

			} else if (elem.canHaveChildren !== false) {
				elem.appendChild(child);

			} else if (tag === 'object' &&
				child.tagName && child.tagName.toLowerCase() === 'param') {
					// IE-only path
					try {
						elem.appendChild(child);
					} catch (ex1) {}
					try {
						if (elem.object) {
							elem.object[child.name] = child.value;
						}
					} catch (ex2) {}
			}
		}
	};

	/**
	 * Tests a node for whitespace
	 *
	 * @private
	 * @param {Node} node The node
	 * @return {boolean}
	 */
	var isWhitespace = function(node) {
		return !!node && (node.nodeType === 3) && (!node.nodeValue || !/\S/.exec(node.nodeValue));
	};

	/**
	 * Trims whitespace pattern from the text node
	 *
	 * @private
	 * @param {Node} node The node
	 */
	var trimPattern = function(node, pattern) {
		if (!!node && (node.nodeType === 3) && pattern.exec(node.nodeValue)) {
			node.nodeValue = node.nodeValue.replace(pattern, '');
		}
	};

	/**
	 * Removes leading and trailing whitespace nodes
	 *
	 * @private
	 * @param {Node} elem The node
	 */
	var trimWhitespace = function(elem) {
		if (elem) {
			while (isWhitespace(elem.firstChild)) {
				// trim leading whitespace text nodes
				elem.removeChild(elem.firstChild);
			}
			// trim leading whitespace text
			trimPattern(elem.firstChild, LEADING);
			while (isWhitespace(elem.lastChild)) {
				// trim trailing whitespace text nodes
				elem.removeChild(elem.lastChild);
			}
			// trim trailing whitespace text
			trimPattern(elem.lastChild, TRAILING);
		}
	};

	/**
	 * Converts the markup to DOM nodes
	 *
	 * @private
	 * @param {string|Markup} value The node
	 * @return {Node}
	 */
	var toDOM = function(value) {
		var wrapper = createElement('div');
		wrapper.innerHTML = ''+value;

		// trim extraneous whitespace
		trimWhitespace(wrapper);

		// eliminate wrapper for single nodes
		if (wrapper.childNodes.length === 1) {
			return wrapper.firstChild;
		}

		// create a document fragment to hold elements
		var frag = createElement('');
		while (wrapper.firstChild) {
			frag.appendChild(wrapper.firstChild);
		}
		return frag;
	};

	/**
	 * Default error handler
	 * @param {Error} ex
	 * @return {Node}
	 */
	var onError = function(ex) {
		return document.createTextNode('['+ex+']');
	};

	/* override this to perform custom error handling during binding */
	JsonML.onerror = null;

	/**
	 * also used by JsonML.BST
	 * @param {Node} elem
	 * @param {*} jml
	 * @param {function} filter
	 * @return {Node}
	 */
	var patch = JsonML.patch = function(elem, jml, filter) {

		for (var i=1; i<jml.length; i++) {
			if (isArray(jml[i]) || 'string' === typeof jml[i]) {
				// append children
				appendDOM(elem, toHTML(jml[i], filter));

			} else if (isMarkup(jml[i])) {
				appendDOM(elem, toDOM(jml[i].value));

			} else if ('object' === typeof jml[i] && jml[i] !== null && elem.nodeType === 1) {
				// add attributes
				elem = addAttributes(elem, jml[i]);
			}
		}

		return elem;
	};

	/**
	 * Main builder entry point
	 * @param {string|array} jml
	 * @param {function} filter
	 * @return {Node}
	 */
	var toHTML = JsonML.toHTML = function(jml, filter) {
		try {
			if (!jml) {
				return null;
			}
			if ('string' === typeof jml) {
				return document.createTextNode(jml);
			}
			if (isMarkup(jml)) {
				return toDOM(jml.value);
			}
			if (!isArray(jml) || ('string' !== typeof jml[0])) {
				throw new SyntaxError('invalid JsonML');
			}

			var tagName = jml[0]; // tagName
			if (!tagName) {
				// correctly handle a list of JsonML trees
				// create a document fragment to hold elements
				var frag = createElement('');
				for (var i=1; i<jml.length; i++) {
					appendDOM(frag, toHTML(jml[i], filter));
				}

				// trim extraneous whitespace
				trimWhitespace(frag);

				// eliminate wrapper for single nodes
				if (frag.childNodes.length === 1) {
					return frag.firstChild;
				}
				return frag;
			}

			if (tagName.toLowerCase() === 'style' && document.createStyleSheet) {
				// IE requires this interface for styles
				patch(document.createStyleSheet(), jml, filter);
				// in IE styles are effective immediately
				return null;
			}

			var elem = patch(createElement(tagName), jml, filter);

			// trim extraneous whitespace
			trimWhitespace(elem);
			return (elem && isFunction(filter)) ? filter(elem) : elem;
		} catch (ex) {
			try {
				// handle error with complete context
				var err = isFunction(JsonML.onerror) ? JsonML.onerror : onError;
				return err(ex, jml, filter);
			} catch (ex2) {
				return document.createTextNode('['+ex2+']');
			}
		}
	};

	/**
	 * Not super efficient.
	 * TODO: port render.js from DUEL
	 * @param {string|array} jml JsonML structure
	 * @return {string} HTML text
	 */
	JsonML.toHTMLText = function(jml, filter) {
		var elem = toHTML(jml, filter);
		if (elem.outerHTML) {
			return elem.outerHTML;
		}

		var parent = createElement('div');
		parent.appendChild(elem);

		var html = parent.innerHTML;
		parent.removeChild(elem);

		return html;
	};

})(JsonML, document);
