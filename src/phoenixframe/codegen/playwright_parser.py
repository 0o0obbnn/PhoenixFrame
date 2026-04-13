import ast
from .core import AssetParser

class PlaywrightParser(AssetParser):
    """Parses a Playwright Codegen Python script to extract UI interactions."""
    def parse(self, source: str) -> list:
        """Parses the given Python script content and returns a structured representation of UI interactions."""
        interactions = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    call = node.value

                    # Handle direct page method calls: page.goto()
                    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == "page":
                        method_name = call.func.attr
                        args = [ast.unparse(arg) for arg in call.args]
                        keywords = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}

                        interaction = {
                            "type": "page_interaction",
                            "method": method_name,
                            "args": args,
                            "keywords": keywords,
                            "line_no": node.lineno
                        }
                        interactions.append(interaction)

                    # Handle other attribute calls
                    elif isinstance(call.func, ast.Attribute):
                        # Handle expect calls: expect(page).to_have_url()
                        if (isinstance(call.func.value, ast.Call) and
                            isinstance(call.func.value.func, ast.Name) and
                            call.func.value.func.id == "expect"):

                            method_name = call.func.attr
                            args = [ast.unparse(arg) for arg in call.args]
                            keywords = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}

                            interaction = {
                                "type": "page_interaction",
                                "method": method_name,
                                "args": args,
                                "keywords": keywords,
                                "line_no": node.lineno
                            }
                            interactions.append(interaction)

                        # Handle chained calls: page.locator().click()
                        elif (isinstance(call.func.value, ast.Call) and
                              isinstance(call.func.value.func, ast.Attribute) and
                              isinstance(call.func.value.func.value, ast.Name) and
                              call.func.value.func.value.id == "page" and
                              call.func.value.func.attr == "locator"):

                            method_name = call.func.attr
                            locator_args = [ast.unparse(arg) for arg in call.func.value.args]
                            args = [ast.unparse(arg) for arg in call.args]
                            keywords = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}

                            interaction = {
                                "type": "page_interaction",
                                "method": method_name,
                                "args": locator_args + args,  # Combine locator and method args
                                "keywords": keywords,
                                "line_no": node.lineno
                            }
                            interactions.append(interaction)

            return interactions
        except SyntaxError as e:
            raise ValueError(f"Invalid Python script syntax: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing Playwright script: {e}")
