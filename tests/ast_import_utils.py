import ast


def imports_symbol_from_module(module_text: str, module: str, symbol: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in module_ast.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != module:
            continue
        if any(alias.name == symbol for alias in node.names):
            return True
    return False


def calls_symbol(module_text: str, symbol: str) -> bool:
    module_ast = ast.parse(module_text)
    for node in ast.walk(module_ast):
        if not isinstance(node, ast.Call):
            continue
        called_function = node.func
        if isinstance(called_function, ast.Name) and called_function.id == symbol:
            return True
        if isinstance(called_function, ast.Attribute) and called_function.attr == symbol:
            return True
    return False


def imports_collect_function_sources(module_text: str) -> bool:
    return imports_symbol_from_module(
        module_text,
        module="tests.ast_function_source_utils",
        symbol="collect_function_sources",
    )


def imports_imports_collect_function_sources(module_text: str) -> bool:
    return imports_symbol_from_module(
        module_text,
        module="tests.ast_import_utils",
        symbol="imports_collect_function_sources",
    )
