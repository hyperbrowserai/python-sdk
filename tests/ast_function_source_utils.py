import ast
from pathlib import Path


def collect_function_sources(module_path: str) -> dict[str, str]:
    module_text = Path(module_path).read_text(encoding="utf-8")
    module_ast = ast.parse(module_text)
    function_sources: dict[str, str] = {}
    for node in module_ast.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_source = ast.get_source_segment(module_text, node)
            if function_source is not None:
                function_sources[node.name] = function_source
    return function_sources
