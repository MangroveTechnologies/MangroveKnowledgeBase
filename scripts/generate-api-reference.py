#!/usr/bin/env python3
"""Generate Mintlify API reference mdx files for one or more domains in
docs/openapi3.json.

Each domain becomes a single mdx page under docs/api-reference/<domain>.mdx
listing every operation in that path-prefix, with a curl example built from
the spec parameters / requestBody schema.

Intended for the 5 domains that exist in the live MangroveAI API but had no
hand-written mdx page when this was added: config, defi, on-chain,
promo-codes, social.

Usage:
    python scripts/generate-api-reference.py [domain ...]

If no domains are given, generates the default set above. Run from the repo
root.
"""

import json
import os
import sys
from collections import OrderedDict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SPEC_PATH = os.path.join(PROJECT_ROOT, "docs", "openapi3.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "api-reference")

DEFAULT_DOMAINS = ["config", "defi", "on-chain", "promo-codes", "social"]
BASE_URL = "https://api.mangrovedeveloper.ai/api/v1"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _resolve_ref(spec, ref):
    """Resolve a $ref string against the spec dict. Returns the dereferenced
    object or None if not resolvable."""
    if not ref or not ref.startswith("#/"):
        return None
    parts = ref[2:].split("/")
    cur = spec
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _example_for_schema(schema, spec, depth=0):
    """Return a Python value that's a reasonable example for the given JSON
    schema. Handles $ref, type-based defaults, and nested objects/arrays."""
    if depth > 5 or not schema:
        return None
    if isinstance(schema, dict) and "$ref" in schema:
        return _example_for_schema(_resolve_ref(spec, schema["$ref"]), spec, depth + 1)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        out = {}
        for pname, pschema in (schema.get("properties") or {}).items():
            out[pname] = _example_for_schema(pschema, spec, depth + 1)
        return out
    if t == "array":
        item = _example_for_schema(schema.get("items") or {}, spec, depth + 1)
        return [item] if item is not None else []
    if t == "integer":
        return 0
    if t == "number":
        return 0
    if t == "boolean":
        return False
    if t == "string":
        fmt = schema.get("format")
        if fmt == "date-time":
            return "2026-01-01T00:00:00Z"
        if fmt == "date":
            return "2026-01-01"
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        return "string"
    return None


def _example_for_param(param, spec):
    """Pick a sample value for a parameter to embed in a curl URL. Falls back
    to the parameter name as a placeholder so the URL stays readable when
    the spec has no defaults / examples."""
    schema = param.get("schema") or {}
    if "example" in param:
        return param["example"]
    ex = _example_for_schema(schema, spec)
    if ex is None or ex == "" or ex == "string":
        return "<" + param.get("name", "value") + ">"
    return ex


def _substitute_path_params(path, params, spec):
    """Replace {name} placeholders in a path with example values from the
    parameter list."""
    out = path
    for p in params:
        if p.get("in") != "path":
            continue
        name = p.get("name", "")
        if not name:
            continue
        ex = _example_for_param(p, spec)
        out = out.replace("{" + name + "}", str(ex))
    return out


def _path_with_query(path, params, spec):
    """Append example query params to a path for curl examples."""
    qs = []
    for p in params:
        if p.get("in") != "query":
            continue
        name = p.get("name")
        if not name:
            continue
        ex = _example_for_param(p, spec)
        qs.append(f"{name}={ex}")
    return path + ("?" + "&".join(qs) if qs else "")


def _build_curl(method, path, params, request_body, spec):
    """Construct a curl command string for an operation."""
    lines = []
    sub_path = _substitute_path_params(path, params or [], spec)
    full_path = _path_with_query(sub_path, params or [], spec)
    method_u = method.upper()
    url = f"{BASE_URL}{full_path}"
    if method_u == "GET":
        lines.append(f'curl -H "Authorization: Bearer $TOKEN" \\')
        lines.append(f'  "{url}"')
    else:
        lines.append(f'curl -X {method_u} "{url}" \\')
        lines.append('  -H "Authorization: Bearer $TOKEN" \\')
        if request_body:
            content = request_body.get("content") or {}
            json_schema = (content.get("application/json") or {}).get("schema")
            if json_schema:
                example = _example_for_schema(json_schema, spec)
                if example is not None:
                    body_str = json.dumps(example, indent=2)
                    lines.append('  -H "Content-Type: application/json" \\')
                    lines.append(f"  -d '{body_str}'")
                    return "\n".join(lines)
        # No JSON body — drop trailing backslash
        lines[-1] = lines[-1].rstrip(" \\")
    return "\n".join(lines)


def _operation_section(method, path, op, path_item, spec):
    """Build mdx lines for a single operation. `path_item` is the parent
    object in spec.paths so we can pick up shared path-level parameters."""
    out = []
    summary = op.get("summary") or f"{method.upper()} {path}"
    description = op.get("description") or ""

    out.append(f"### {summary}")
    out.append("")
    out.append(f"`{method.upper()} /api/v1{path}`")
    out.append("")
    if description and description != summary:
        out.append(description.strip())
        out.append("")

    # Merge path-level + operation-level parameters; op-level wins on name.
    raw_params = (path_item.get("parameters") or []) + (op.get("parameters") or [])
    seen = set()
    params = []
    for p in reversed(raw_params):
        key = (p.get("name"), p.get("in"))
        if key in seen:
            continue
        seen.add(key)
        params.insert(0, p)

    path_params = [p for p in params if p.get("in") == "path"]
    query_params = [p for p in params if p.get("in") == "query"]
    if path_params or query_params:
        out.append("**Parameters**")
        out.append("")
        out.append("| Name | In | Type | Required | Description |")
        out.append("|------|----|------|----------|-------------|")
        for p in path_params + query_params:
            schema = p.get("schema") or {}
            ptype = schema.get("type", "string")
            required = "yes" if p.get("required") else "no"
            desc = (p.get("description") or "").replace("|", "\\|").replace("\n", " ")
            out.append(f"| `{p.get('name', '')}` | {p.get('in')} | `{ptype}` | {required} | {desc} |")
        out.append("")

    # Request body schema (just note; the curl shows the example)
    if op.get("requestBody"):
        rb = op["requestBody"]
        content = rb.get("content") or {}
        json_schema = (content.get("application/json") or {}).get("schema")
        if json_schema:
            out.append("**Request body** (JSON)")
            out.append("")

    out.append("**Example**")
    out.append("")
    out.append("```bash cURL")
    out.append(_build_curl(method, path, params, op.get("requestBody"), spec))
    out.append("```")
    out.append("")
    return out


def _domain_to_title(domain):
    return domain.replace("-", " ").title() + " API"


def _domain_description(domain):
    blurbs = {
        "config": "Trading defaults and execution-config endpoints used by the strategy engine.",
        "defi": "DeFi metrics — protocol TVL, chain TVL, stablecoin supply.",
        "on-chain": "On-chain analytics — wallet activity, transaction flows, holders, network metrics.",
        "promo-codes": "Admin-managed promotional codes for subscription discounts.",
        "social": "Social-data endpoints — sentiment, mention volume, influence scoring.",
    }
    return blurbs.get(domain, f"{_domain_to_title(domain)} endpoints.")


def generate_for_domain(spec, domain):
    """Emit docs/api-reference/<domain>.mdx for the given path-prefix."""
    paths = spec.get("paths", {})

    # All paths whose first segment matches the domain
    matching = OrderedDict()
    prefix = "/" + domain
    for p in sorted(paths.keys()):
        first = p.split("/")[1] if p.startswith("/") and len(p) > 1 else ""
        if first == domain:
            matching[p] = paths[p]
    if not matching:
        print(f"  WARN: no paths matched /{domain}/* — skipping")
        return None

    title = _domain_to_title(domain)
    description = _domain_description(domain)

    out = []
    out.append("---")
    out.append(f'title: "{title}"')
    out.append(f'description: "{description}"')
    out.append("---")
    out.append("")
    out.append(f"# {title}")
    out.append("")
    out.append(description)
    out.append("")
    out.append("## Base URL")
    out.append("")
    out.append("```")
    out.append(f"{BASE_URL}/{domain}")
    out.append("```")
    out.append("")
    out.append("## Authentication")
    out.append("")
    out.append("All endpoints require a JWT bearer token.")
    out.append("")
    out.append("```")
    out.append("Authorization: Bearer YOUR_JWT_TOKEN")
    out.append("```")
    out.append("")
    out.append("## Endpoints")
    out.append("")
    for path, path_item in matching.items():
        for method, op in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            out.extend(_operation_section(method.lower(), path, op, path_item, spec))

    out_path = os.path.join(OUTPUT_DIR, f"{domain}.mdx")
    with open(out_path, "w") as f:
        f.write("\n".join(out))
    op_count = sum(1 for _, methods in matching.items()
                   for m in methods if m.lower() in HTTP_METHODS)
    print(f"  Generated {out_path} ({op_count} operations across {len(matching)} paths)")
    return out_path


def main():
    domains = sys.argv[1:] or DEFAULT_DOMAINS

    if not os.path.exists(SPEC_PATH):
        print(f"ERROR: spec not found at {SPEC_PATH}")
        sys.exit(1)
    with open(SPEC_PATH) as f:
        spec = json.load(f)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating from {SPEC_PATH}")
    for d in domains:
        generate_for_domain(spec, d)


if __name__ == "__main__":
    main()
