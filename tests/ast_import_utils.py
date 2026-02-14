import ast


def imports_collect_function_sources(module_text: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "tests.ast_function_source_utils":
            continue
        if any(alias.name == "collect_function_sources" for alias in node.names):
            return True
    return False
