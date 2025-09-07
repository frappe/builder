import { syntaxTree } from '@codemirror/language';

function getAllProperties(obj:Object) {
  const props = new Set();
  let current = obj;
  
  while (current && current !== Object.prototype) {
    // Get all properties from current level
    Object.getOwnPropertyNames(current).forEach(prop => {
      props.add(prop);
    });
    
    // Move up the prototype chain
    current = Object.getPrototypeOf(current);
  }
  
  return Array.from(props);
}

// Usage
const allDocumentProps = getAllProperties(document);
console.log(allDocumentProps.includes('addEventListener')); // ✅ true
console.log(allDocumentProps.includes('querySelector')); // ✅ true

const completePropertyAfter = ['PropertyName', '.', '?.'];
const dontCompleteIn = [
  'TemplateString',
  'LineComment',
  'BlockComment',
  'VariableDefinition',
  'PropertyDefinition',
];

export default function jsCompletionsFromGlobalScope(context: any) {
  let nodeBefore = syntaxTree(context.state).resolveInner(context.pos, -1);

  console.log({nodeBefore})
  if (
    completePropertyAfter.includes(nodeBefore.name) &&
    nodeBefore.parent?.name == 'MemberExpression'
  ) {
    let object = nodeBefore.parent.getChild('Expression');
    if (object?.name == 'VariableName') {
      let from = /\./.test(nodeBefore.name) ? nodeBefore.to : nodeBefore.from;
      let variableName = context.state.sliceDoc(object.from, object.to);
      console.log({variableName})
      if (typeof window[variableName] == 'object')
        return completeProperties(from, window[variableName]);
    }
  } else if (nodeBefore.name == 'VariableName') {
    console.log({nodeBefore, window})
    return completeProperties(nodeBefore.from, window);
  } else if (context.explicit && !dontCompleteIn.includes(nodeBefore.name)) {
    return completeProperties(context.pos, window);
  }
  return null;
}

function completeProperties(from: any, object: any) {
  let options = [];
  console.log({object})
  for (let name of getAllProperties(object)) {
    options.push({
      label: name,
      type: typeof object[name as string] == 'function' ? 'function' : 'variable',
    });
  }
  return {
    from,
    options,
    validFor: /^[\w$]*$/,
  };
}
