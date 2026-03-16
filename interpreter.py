# interpreter.py
# Usage: python interpreter.py program.lum

import ast
import math
import operator
import sys

# Allowed math functions and helpers available in expressions
SAFE_FUNCS = {
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'log': math.log,   # natural log, log(x, base) works as math.log(x, base)
    'exp': math.exp,
    'abs': abs,
    'floor': math.floor,
    'ceil': math.ceil,
    'round': round,
    'int': int,
    'float': float,
    'str': str,
    'len': len,
    'max': max,
    'min': min,
}

# Simple constant aliases
SAFE_CONSTS = {
    'pi': math.pi,
    'e': math.e,
    'true': True,
    'false': False,
    'True': True,
    'False': False
}

# Environment to store variables
variables = {}

# Evaluate an expression AST node safely
def eval_node(node):
    if isinstance(node, ast.Expression):
        return eval_node(node.body)

    # numbers and strings (ast.Constant covers both in Python 3.8+)
    if isinstance(node, ast.Constant):
        return node.value

    # binary operations a + b, a * b, etc.
    if isinstance(node, ast.BinOp):
        left = eval_node(node.left)
        right = eval_node(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.Mod):
            return left % right
        if isinstance(op, ast.Pow):
            return left ** right
        if isinstance(op, ast.FloorDiv):
            return left // right
        raise ValueError(f"Unsupported binary operator: {ast.dump(op)}")

    # unary operations: -x, +x
    if isinstance(node, ast.UnaryOp):
        val = eval_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +val
        if isinstance(node.op, ast.USub):
            return -val
        raise ValueError(f"Unsupported unary operator: {ast.dump(node.op)}")

    # parenthesized expressions are represented by nested nodes so no special case needed

    # variables / names
    if isinstance(node, ast.Name):
        name = node.id
        if name in variables:
            return variables[name]
        if name in SAFE_CONSTS:
            return SAFE_CONSTS[name]
        if name in SAFE_FUNCS:
            # returning function object (useful if user wants to pass functions around)
            return SAFE_FUNCS[name]
        raise NameError(f"Undefined variable or name: {name}")

    # function calls: name(args...)
    if isinstance(node, ast.Call):
        fn_node = node.func
        # only allow direct names as calls (no attribute access)
        if not isinstance(fn_node, ast.Name):
            raise ValueError("Only direct function calls allowed, e.g. sqrt(4)")
        fn_name = fn_node.id
        if fn_name not in SAFE_FUNCS:
            raise NameError(f"Function '{fn_name}' is not available.")
        fn = SAFE_FUNCS[fn_name]
        args = [eval_node(a) for a in node.args]
        # allow keyword args if they exist (rare) — evaluate safely
        kwargs = {kw.arg: eval_node(kw.value) for kw in node.keywords} if node.keywords else {}
        return fn(*args, **kwargs)

    # list literals
    if isinstance(node, ast.List):
        return [eval_node(elt) for elt in node.elts]

    # boolean operations (and/or)
    if isinstance(node, ast.BoolOp):
        values = [eval_node(v) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)

    # comparisons
    if isinstance(node, ast.Compare):
        left = eval_node(node.left)
        results = []
        for op, comparator in zip(node.ops, node.comparators):
            right = eval_node(comparator)
            if isinstance(op, ast.Eq):
                results.append(left == right)
            elif isinstance(op, ast.NotEq):
                results.append(left != right)
            elif isinstance(op, ast.Lt):
                results.append(left < right)
            elif isinstance(op, ast.LtE):
                results.append(left <= right)
            elif isinstance(op, ast.Gt):
                results.append(left > right)
            elif isinstance(op, ast.GtE):
                results.append(left >= right)
            else:
                raise ValueError(f"Unsupported comparison: {ast.dump(op)}")
            left = right
        return all(results)

    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def safe_eval(expr_str):
    """
    Parse a single expression and evaluate it safely using our AST whitelist.
    """
    try:
        expr_ast = ast.parse(expr_str, mode='eval')
        return eval_node(expr_ast)
    except Exception as e:
        raise

def run_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for i, raw in enumerate(lines, start=1):
        # strip newline and trim whitespace
        line = raw.split('#', 1)[0].strip()  # remove comments after '#'
        if not line:
            continue  # skip empty/comment lines

        try:
            # print statement: print expr
            if line.startswith('print '):
                expr = line[len('print '):].strip()
                val = safe_eval(expr)
                print(val)
                continue

            # assignment: name = expr
            if '=' in line:
                left, right = line.split('=', 1)
                name = left.strip()
                if not name.isidentifier():
                    raise SyntaxError(f"Invalid variable name: '{name}'")
                expr = right.strip()
                val = safe_eval(expr)
                variables[name] = val
                continue

            # unknown statement
            raise SyntaxError(f"Unknown or unsupported statement: {line}")

        except Exception as e:
            print(f"[Error] {path}:{i}: {e}")
            # continue interpreting next lines (helpful while developing)
            continue


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python interpreter.py file.lum")
        sys.exit(1)
    filename = sys.argv[1]
    run_file(filename)