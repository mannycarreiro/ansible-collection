from flask import Flask, request, jsonify
from flask_cors import CORS
import jinja2
import json
import yaml
import re
import os

app = Flask(__name__)
CORS(app)

# ── Version ───────────────────────────────────────────────────────────────────
APP_VERSION = "1.0.0"

# ── Ansible-style custom filters ─────────────────────────────────────────────

def _ansible_regex_replace(value, pattern, replacement, ignorecase=False):
    flags = re.IGNORECASE if ignorecase else 0
    return re.sub(pattern, replacement, str(value), flags=flags)

def _ansible_regex_search(value, pattern, ignorecase=False):
    flags = re.IGNORECASE if ignorecase else 0
    m = re.search(pattern, str(value), flags)
    return m.group(0) if m else ''

def _ansible_regex_findall(value, pattern, ignorecase=False):
    flags = re.IGNORECASE if ignorecase else 0
    return re.findall(pattern, str(value), flags)

def _ansible_to_yaml(value, indent=2):
    return yaml.dump(value, default_flow_style=False, indent=indent)

def _ansible_to_json(value, indent=None):
    return json.dumps(value, indent=indent)

def _ansible_combine(*dicts, **kwargs):
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result

def _ansible_default(value, default_value='', boolean=False):
    if boolean:
        return value if value else default_value
    return value if value is not None else default_value

def _ansible_mandatory(value, msg=None):
    if value is None or value == jinja2.Undefined:
        raise jinja2.UndefinedError(msg or 'Mandatory variable not defined')
    return value

def _ansible_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('yes', 'true', '1', 'on')

def _ansible_ternary(value, true_val, false_val, none_val=None):
    if value is None and none_val is not None:
        return none_val
    return true_val if value else false_val

def _ansible_flatten(lst, levels=None):
    def _flat(l, depth):
        for item in l:
            if isinstance(item, list) and (depth is None or depth > 0):
                yield from _flat(item, None if depth is None else depth - 1)
            else:
                yield item
    return list(_flat(lst, levels))

def _ansible_zip_filter(*lists):
    return [list(x) for x in zip(*lists)]

def _ansible_zip_longest_filter(*lists, fillvalue=None):
    from itertools import zip_longest
    return [list(x) for x in zip_longest(*lists, fillvalue=fillvalue)]

def _ansible_dict2items(d, key_name='key', value_name='value'):
    return [{key_name: k, value_name: v} for k, v in d.items()]

def _ansible_items2dict(lst, key_name='key', value_name='value'):
    return {item[key_name]: item[value_name] for item in lst}

def _ansible_subelements(lst, subelement, skip_missing=False):
    result = []
    for item in lst:
        sub = item.get(subelement)
        if sub is None:
            if skip_missing:
                continue
            raise KeyError(f"'{subelement}' not found in {item}")
        for s in sub:
            result.append((item, s))
    return result

def _ansible_extract(lst, container, morekeys=None):
    results = []
    for key in lst:
        val = container.get(key)
        if morekeys:
            for mk in morekeys:
                if isinstance(val, dict):
                    val = val.get(mk)
        results.append(val)
    return results

def _ansible_from_yaml(value):
    return yaml.safe_load(value)

def _ansible_from_json(value):
    return json.loads(value)

def _ansible_comment(value, style='plain', decoration='# '):
    lines = str(value).splitlines()
    if style == 'xml':
        return '<!-- ' + '\n     '.join(lines) + ' -->'
    return '\n'.join(decoration + l for l in lines)

def _ansible_b64encode(value):
    import base64
    return base64.b64encode(str(value).encode()).decode()

def _ansible_b64decode(value):
    import base64
    return base64.b64decode(str(value)).decode()

def _ansible_hash(value, hashtype='sha1'):
    import hashlib
    h = hashlib.new(hashtype)
    h.update(str(value).encode())
    return h.hexdigest()

def _ansible_password_hash(password, hashtype='sha512'):
    import hashlib, os
    salt = os.urandom(8).hex()[:8]
    h = hashlib.new(hashtype.replace('sha512', 'sha512'))
    h.update((salt + password).encode())
    return f'${hashtype}${salt}${h.hexdigest()}'

def _ansible_to_uuid(value):
    import uuid
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(value)))

def _ansible_unique(lst):
    seen = []
    for x in lst:
        if x not in seen:
            seen.append(x)
    return seen

def _ansible_intersect(a, b):
    return [x for x in a if x in b]

def _ansible_difference(a, b):
    return [x for x in a if x not in b]

def _ansible_symmetric_difference(a, b):
    return [x for x in a if x not in b] + [x for x in b if x not in a]

def _ansible_union(a, b):
    result = list(a)
    for x in b:
        if x not in result:
            result.append(x)
    return result

def _ansible_product(*lists):
    from itertools import product
    return [list(x) for x in product(*lists)]

def _wordwrap(s, width=79, break_long_words=True, wrapstring='\n'):
    import textwrap
    return wrapstring.join(textwrap.wrap(s, width, break_long_words=break_long_words))

# ── Salt-style custom filters ─────────────────────────────────────────────────

def _salt_strftime(value, fmt='%Y-%m-%d'):
    from datetime import datetime
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime(fmt)
    return str(value)

def _salt_is_list(value):
    return isinstance(value, list)

def _salt_is_dict(value):
    return isinstance(value, dict)

def _salt_is_str(value):
    return isinstance(value, str)

def _salt_is_int(value):
    return isinstance(value, int)

def _salt_to_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', 'yes', '1', 'on')

def _salt_yaml_encode(value):
    return yaml.dump(value, default_flow_style=True).strip()

def _salt_yaml_decode(value):
    return yaml.safe_load(value)

def _salt_md5(value):
    import hashlib
    return hashlib.md5(str(value).encode()).hexdigest()

def _salt_sha256(value):
    import hashlib
    return hashlib.sha256(str(value).encode()).hexdigest()

def _salt_base64_encode(value):
    import base64
    return base64.b64encode(str(value).encode()).decode()

def _salt_base64_decode(value):
    import base64
    return base64.b64decode(str(value)).decode()

def _salt_regex_replace(value, pattern, repl):
    return re.sub(pattern, repl, str(value))

def _salt_regex_match(value, pattern):
    return bool(re.match(pattern, str(value)))

def _salt_regex_search(value, pattern):
    m = re.search(pattern, str(value))
    return m.group(0) if m else None

def _salt_indent(s, width=4, first=False):
    lines = s.splitlines(keepends=True)
    if not first:
        return lines[0] + ''.join(' ' * width + l for l in lines[1:]) if lines else s
    return ''.join(' ' * width + l for l in lines)

def _salt_quote(value):
    return "'" + str(value).replace("'", "\\'") + "'"

def _salt_sequence(value):
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]

def _salt_unique(lst):
    seen = []
    for x in lst:
        if x not in seen:
            seen.append(x)
    return seen


# ── Environment factories ─────────────────────────────────────────────────────

def build_env(mode, undefined_class, active_extensions, trim_blocks, lstrip_blocks, keep_trailing_newline):
    """Build a Jinja2 environment configured for the given rendering mode."""

    common_kwargs = dict(
        undefined=undefined_class,
        extensions=active_extensions,
        trim_blocks=trim_blocks,
        lstrip_blocks=lstrip_blocks,
        keep_trailing_newline=keep_trailing_newline,
    )

    if mode == 'ansible':
        env = jinja2.Environment(**common_kwargs)
        # Ansible enables loopcontrols + do by default
        if 'jinja2.ext.loopcontrols' not in active_extensions:
            env2_exts = active_extensions + ['jinja2.ext.loopcontrols', 'jinja2.ext.do']
            env = jinja2.Environment(**{**common_kwargs, 'extensions': env2_exts})

        # Add Ansible filters
        env.filters.update({
            'regex_replace':        _ansible_regex_replace,
            'regex_search':         _ansible_regex_search,
            'regex_findall':        _ansible_regex_findall,
            'to_yaml':              _ansible_to_yaml,
            'to_json':              _ansible_to_json,
            'to_nice_yaml':         lambda v: _ansible_to_yaml(v, indent=2),
            'to_nice_json':         lambda v: _ansible_to_json(v, indent=4),
            'from_yaml':            _ansible_from_yaml,
            'from_json':            _ansible_from_json,
            'combine':              _ansible_combine,
            'default':              _ansible_default,
            'd':                    _ansible_default,
            'mandatory':            _ansible_mandatory,
            'bool':                 _ansible_bool,
            'ternary':              _ansible_ternary,
            'flatten':              _ansible_flatten,
            'zip':                  _ansible_zip_filter,
            'zip_longest':          _ansible_zip_longest_filter,
            'dict2items':           _ansible_dict2items,
            'items2dict':           _ansible_items2dict,
            'subelements':          _ansible_subelements,
            'extract':              _ansible_extract,
            'comment':              _ansible_comment,
            'b64encode':            _ansible_b64encode,
            'b64decode':            _ansible_b64decode,
            'hash':                 _ansible_hash,
            'to_uuid':              _ansible_to_uuid,
            'unique':               _ansible_unique,
            'intersect':            _ansible_intersect,
            'difference':           _ansible_difference,
            'symmetric_difference': _ansible_symmetric_difference,
            'union':                _ansible_union,
            'product':              _ansible_product,
            'wordwrap':             _wordwrap,
        })
        # Ansible tests
        env.tests.update({
            'defined':   lambda v: not isinstance(v, jinja2.Undefined),
            'undefined': lambda v: isinstance(v, jinja2.Undefined),
            'none':      lambda v: v is None,
            'boolean':   lambda v: isinstance(v, bool),
            'integer':   lambda v: isinstance(v, int) and not isinstance(v, bool),
            'float':     lambda v: isinstance(v, float),
            'string':    lambda v: isinstance(v, str),
            'list':      lambda v: isinstance(v, list),
            'dict':      lambda v: isinstance(v, dict),
            'number':    lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        })
        # Ansible globals
        env.globals.update({
            'lookup': lambda *a, **kw: '',   # stub
            'query':  lambda *a, **kw: [],   # stub
            'q':      lambda *a, **kw: [],   # stub
        })
        return env

    elif mode == 'salt':
        env = jinja2.Environment(**common_kwargs)
        env.filters.update({
            'strftime':      _salt_strftime,
            'is_list':       _salt_is_list,
            'is_dict':       _salt_is_dict,
            'is_str':        _salt_is_str,
            'is_int':        _salt_is_int,
            'to_bool':       _salt_to_bool,
            'yaml_encode':   _salt_yaml_encode,
            'yaml_dquote':   lambda v: '"' + str(v).replace('"', '\\"') + '"',
            'yaml_squote':   _salt_quote,
            'yaml_decode':   _salt_yaml_decode,
            'md5':           _salt_md5,
            'sha256':        _salt_sha256,
            'base64_encode': _salt_base64_encode,
            'base64_decode': _salt_base64_decode,
            'regex_replace': _salt_regex_replace,
            'regex_match':   _salt_regex_match,
            'regex_search':  _salt_regex_search,
            'indent':        _salt_indent,
            'quote':         _salt_quote,
            'sequence':      _salt_sequence,
            'unique':        _salt_unique,
            'tojson':        _ansible_to_json,
            'toyaml':        _ansible_to_yaml,
        })
        env.tests.update({
            'list':    lambda v: isinstance(v, list),
            'dict':    lambda v: isinstance(v, dict),
            'string':  lambda v: isinstance(v, str),
            'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
            'float':   lambda v: isinstance(v, float),
            'none':    lambda v: v is None,
        })
        # Salt globals (stubs so templates don't error)
        env.globals.update({
            'salt':   {},
            'grains': {},
            'pillar': {},
            'opts':   {},
            'env':    os.environ.copy(),
        })
        return env

    else:  # base jinja2
        return jinja2.Environment(**common_kwargs)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': APP_VERSION, 'jinja2_version': jinja2.__version__})

@app.route('/render', methods=['POST'])
def render():
    data = request.get_json()
    template_str = data.get('template', '')
    variables_str = data.get('variables', '{}')
    variables_format = data.get('format', 'json')
    undefined_behavior = data.get('undefined', 'undefined')
    extensions = data.get('extensions', [])
    trim_blocks = data.get('trim_blocks', False)
    lstrip_blocks = data.get('lstrip_blocks', False)
    keep_trailing_newline = data.get('keep_trailing_newline', True)
    mode = data.get('mode', 'base')  # base | ansible | salt

    # Parse variables
    try:
        if variables_format == 'yaml':
            context = yaml.safe_load(variables_str) or {}
        else:
            context = json.loads(variables_str) if variables_str.strip() else {}
        if not isinstance(context, dict):
            return jsonify({'error': 'Variables must be a JSON/YAML object (dict)', 'output': None}), 400
    except Exception as e:
        return jsonify({'error': f'Variable parsing error: {str(e)}', 'output': None}), 400

    # Build environment
    try:
        undefined_map = {
            'undefined':  jinja2.Undefined,
            'strict':     jinja2.StrictUndefined,
            'chainable':  jinja2.ChainableUndefined,
            'debug':      jinja2.DebugUndefined,
        }
        undefined_class = undefined_map.get(undefined_behavior, jinja2.Undefined)

        ext_map = {
            'debug':        'jinja2.ext.debug',
            'do':           'jinja2.ext.do',
            'loopcontrols': 'jinja2.ext.loopcontrols',
            'i18n':         'jinja2.ext.i18n',
        }
        active_extensions = [ext_map[e] for e in extensions if e in ext_map]

        env = build_env(mode, undefined_class, active_extensions, trim_blocks, lstrip_blocks, keep_trailing_newline)
        tmpl = env.from_string(template_str)
        output = tmpl.render(**context)
        return jsonify({'output': output, 'error': None})

    except jinja2.TemplateSyntaxError as e:
        return jsonify({'error': f'Template syntax error at line {e.lineno}: {e.message}', 'output': None, 'line': e.lineno}), 400
    except jinja2.UndefinedError as e:
        return jsonify({'error': f'Undefined variable: {str(e)}', 'output': None}), 400
    except Exception as e:
        return jsonify({'error': f'Render error: {str(e)}', 'output': None}), 400


@app.route('/validate', methods=['POST'])
def validate():
    data = request.get_json()
    template_str = data.get('template', '')
    try:
        env = jinja2.Environment()
        env.parse(template_str)
        return jsonify({'valid': True, 'error': None})
    except jinja2.TemplateSyntaxError as e:
        return jsonify({'valid': False, 'error': str(e), 'line': e.lineno})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
