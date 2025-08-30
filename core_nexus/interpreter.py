import re
import os
import sys
import inspect
from .standard import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class NexusInterpreter:
    def __init__(self): 
        self.variables = {}
        self.functions = {}
        self.env = dict(STANDARD_ENV)

    def evaluate_expression(self, expr, input_func=input, output_func=print):
        if isinstance(expr, str):
            expr = expr.strip()

            # Tratamento especial para comparações envolvendo 'empty'
            empty_comparison_match = re.match(r'(\w+)\s*==\s*empty\((.*?)\)', expr)
            if empty_comparison_match:
                var_name, arg = empty_comparison_match.groups()
                if var_name == arg:
                    empty_result = self.evaluate_expression(f"empty({arg})", input_func, output_func)
                    return empty_result == True

            if expr.startswith("f\"") or expr.startswith("f'"):
                raise ValueError(
                    "[Syntax Error] Python f-strings are not allowed in Nexus.\n"
                    "Use t\"...\" for string interpolation instead.\n"
                    "Example: t\"Value is {var}\".\n"
                    "Please update your code accordingly."
                )

            if expr.startswith('t"') or expr.startswith("t'"):
                return expr

            def clean_comment(expr):
                in_single = False
                in_double = False
                in_triple_single = False
                in_triple_double = False
                i = 0
                result = ""

                while i < len(expr):
                    char = expr[i]

                    # Verificar aspas triplas
                    if i <= len(expr) - 3 and expr[i:i+3] == '"""' and not in_single and not in_triple_single:
                        in_triple_double = not in_triple_double
                        result += char
                        i += 2
                    elif i <= len(expr) - 3 and expr[i:i+3] == "'''" and not in_double and not in_triple_double:
                        in_triple_single = not in_triple_single
                        result += char
                        i += 2
                    # Toggle aspas simples ou duplas
                    elif char == '"' and not in_single and not in_triple_single and not in_triple_double:
                        in_double = not in_double
                    elif char == "'" and not in_double and not in_triple_double and not in_triple_single:
                        in_single = not in_single
                    # Verifica se encontrou "//" fora de string
                    elif char == "/" and i + 1 < len(expr) and expr[i+1] == "/" and not in_single and not in_double and not in_triple_single and not in_triple_double:
                        break
                    result += char
                    i += 1

                return result.strip()

            # Suporte a strings de múltiplas linhas
            if (expr.startswith('"""') and expr.endswith('"""')) or (expr.startswith("'''") and expr.endswith("'''")):
                return expr[3:-3]
            elif (expr.startswith('"') and expr.endswith('"')) or (expr.startswith("'") and expr.endswith("'")):
                return expr[1:-1]

            # Suporte a fatiamento (e.g., name[::-1] ou "Pietro"[::-1])
            slice_match = re.match(r'((?:\w+|[\'"][^\'"]*[\'"]))\[(.*?)\]', expr)
            if slice_match:
                base, slice_expr = slice_match.groups()
                # Determinar se a base é uma variável ou uma string literal
                if base.startswith('"') and base.endswith('"') or base.startswith("'") and base.endswith("'"):
                    obj = base[1:-1]  # String literal, remove aspas
                elif base in self.variables:
                    obj = self.variables[base]
                    if not isinstance(obj, str):
                        raise ValueError(f"[Expression Error] Can only slice strings, not {type(obj).__name__}: '{base}'")
                else:
                    raise ValueError(f"[Expression Error] Variable '{base}' not found")

                # Processar a expressão de fatiamento
                slice_parts = slice_expr.split(':')
                if len(slice_parts) > 3:
                    raise ValueError(f"[Expression Error] Invalid slice syntax: '{slice_expr}'")

                # Avaliar start, end, step (podem ser vazios)
                start = None if slice_parts[0] == '' else self.evaluate_expression(slice_parts[0], input_func, output_func) if len(slice_parts) > 0 else None
                end = None if len(slice_parts) < 2 or slice_parts[1] == '' else self.evaluate_expression(slice_parts[1], input_func, output_func)
                step = None if len(slice_parts) < 3 or slice_parts[2] == '' else self.evaluate_expression(slice_parts[2], input_func, output_func)

                # Converter None para valores padrão do Python
                start = None if start is None else int(start)
                end = None if end is None else int(end)
                step = None if step is None else int(step)

                try:
                    if step is not None:
                        return obj[start:end:step]
                    elif end is not None:
                        return obj[start:end]
                    elif start is not None:
                        return obj[start]
                    else:
                        return obj[:]
                except (TypeError, IndexError) as e:
                    raise ValueError(f"[Expression Error] Invalid slice '{slice_expr}' for '{base}': {e}")

            if expr in self.variables:
                return self.variables[expr]

            call_match = re.match(r'(\w+)(?:\.(\w+))?\((.*)\)', expr)
            if call_match:
                obj_name, func_name, args_str = call_match.groups()
                args, kwargs = self._parse_arguments(args_str)
                evaluated_args = []
                for arg in args:
                    arg_stripped = arg.strip()
                    if (arg_stripped.startswith('"') and arg_stripped.endswith('"')) or (arg_stripped.startswith("'") and arg_stripped.endswith("'")):
                        evaluated_args.append(arg_stripped[1:-1])
                    elif (arg_stripped.startswith('"""') and arg_stripped.endswith('"""')) or (arg_stripped.startswith("'''") and arg_stripped.endswith("'''")):
                        evaluated_args.append(arg_stripped[3:-3])
                    elif arg_stripped.startswith('t"') or arg_stripped.startswith("t'"):
                        evaluated_args.append(arg_stripped)
                    else:
                        evaluated_args.append(self.evaluate_expression(arg, input_func, output_func))
                evaluated_kwargs = {}
                for k, v in kwargs.items():
                    v_stripped = v.strip()
                    if (v_stripped.startswith('"') and v_stripped.endswith('"')) or (v_stripped.startswith("'") and v_stripped.endswith("'")):
                        evaluated_kwargs[k] = v_stripped[1:-1]
                    elif (v_stripped.startswith('"""') and v_stripped.endswith('"""')) or (v_stripped.startswith("'''") and v_stripped.endswith("'''")):
                        evaluated_kwargs[k] = v_stripped[3:-3]
                    elif v_stripped.startswith('t"') or v_stripped.startswith("t'"):
                        evaluated_kwargs[k] = v_stripped
                    else:
                        evaluated_kwargs[k] = self.evaluate_expression(v, input_func, output_func)

                if func_name:
                    if obj_name in self.variables:
                        ns = self.variables[obj_name]
                        if hasattr(ns, func_name):
                            fn = getattr(ns, func_name)
                            if callable(fn):
                                return fn(*evaluated_args, **evaluated_kwargs)
                        raise ValueError(f"[Runtime Error] Function '{func_name}' not found in module '{obj_name}'")
                else:
                    func_name = obj_name
                    if func_name in self.functions:
                        self.functions[func_name].execute(self, evaluated_args, input_func, output_func)
                        return None
                    elif func_name in self.env:
                        if func_name == "nexus_input":
                            result = self.env[func_name](*evaluated_args, input_func=input_func, **evaluated_kwargs)
                            self.variables["__last_input__"] = result
                            return result
                        else:
                            func = self.env[func_name]
                            sig = inspect.signature(func)
                            call_kwargs = {}
                            if 'variables' in sig.parameters:
                                call_kwargs['variables'] = self.variables
                            if 'output_func' in sig.parameters:
                                call_kwargs['output_func'] = output_func
                            call_kwargs.update(evaluated_kwargs)
                            return func(*evaluated_args, **call_kwargs)
                    else:
                        raise ValueError(f"[Runtime Error] Unknown function '{func_name}'")
            else:
                # Verificar parênteses não fechados
                if '(' in expr and ')' not in expr:
                    raise ValueError(f"[Expression Error] Invalid expression '{expr}': '(' was never closed")

        try:
            context = {}
            context.update(self.env)
            context.update(self.variables)
            context["true"] = True
            context["false"] = False

            def custom_input(prompt=""):
                if input_func:
                    return input_func(prompt)
                else:
                    raise ValueError("[Runtime Error] Input function is not provided.")

            context["input"] = custom_input
            context["print"] = lambda *args: " ".join(str(a) for a in args)
            context["printf"] = lambda *args: printf(*args, variables=self.variables, output_func=output_func)

            result = eval(expr, {}, context)
            return result
        except Exception as e:
            raise ValueError(f"[Expression Error] Invalid expression '{expr}': {e}")

    def _parse_arguments(self, args_str):
        args = []
        kwargs = {}
        current_arg = ""
        in_quotes = False
        in_triple_quotes = False
        quote_char = None
        escape = False
        i = 0

        while i < len(args_str):
            char = args_str[i]

            if escape:
                current_arg += char
                escape = False
                i += 1
                continue

            if char == '\\':
                escape = True
                current_arg += char
                i += 1
                continue

            # Verificar aspas triplas
            if i <= len(args_str) - 3 and args_str[i:i+3] in ('"""', "'''") and not in_quotes:
                if in_triple_quotes and args_str[i:i+3] == quote_char:
                    in_triple_quotes = False
                    current_arg += args_str[i:i+3]
                    i += 3
                    continue
                elif not in_triple_quotes:
                    in_triple_quotes = True
                    quote_char = args_str[i:i+3]
                    current_arg += args_str[i:i+3]
                    i += 3
                    continue

            # Verificar aspas simples ou duplas
            if char in ('"', "'") and not in_triple_quotes:
                if in_quotes and char == quote_char:
                    in_quotes = False
                    quote_char = None
                elif not in_quotes:
                    in_quotes = True
                    quote_char = char
                current_arg += char
                i += 1
                continue

            if char == ',' and not in_quotes and not in_triple_quotes:
                if current_arg.strip():
                    if '=' in current_arg:
                        key, value = current_arg.split('=', 1)
                        kwargs[key.strip()] = value.strip()
                    else:
                        args.append(current_arg.strip())
                current_arg = ""
                i += 1
                continue

            current_arg += char
            i += 1

        if current_arg.strip():
            if '=' in current_arg:
                key, value = current_arg.split('=', 1)
                kwargs[key.strip()] = value.strip()
            else:
                args.append(current_arg.strip())

        return args, kwargs

    def run_nexus_code(self, code, input_func=None, output_func=print):
        lines = code.splitlines()
        i = 0
        skip_next_block = False

        def clean_line(line):
            in_single = False
            in_double = False
            in_triple_single = False
            in_triple_double = False
            j = 0
            result = ""

            while j < len(line):
                char = line[j]

                # Verificar aspas triplas
                if j <= len(line) - 3 and line[j:j+3] == '"""' and not in_single and not in_triple_single:
                    in_triple_double = not in_triple_double
                    result += line[j:j+3]
                    j += 3
                    continue
                elif j <= len(line) - 3 and line[j:j+3] == "'''" and not in_double and not in_triple_double:
                    in_triple_single = not in_triple_single
                    result += line[j:j+3]
                    j += 3
                    continue
                # Toggle aspas simples ou duplas
                elif char == '"' and not in_single and not in_triple_single and not in_triple_double:
                    in_double = not in_double
                elif char == "'" and not in_double and not in_triple_double and not in_triple_single:
                    in_single = not in_single
                # Verifica se encontrou "//" fora de string
                elif char == "/" and j + 1 < len(line) and line[j+1] == "/" and not in_single and not in_double and not in_triple_single and not in_triple_double:
                    break
                result += char
                j += 1

            return result.strip()

        while i < len(lines):
            line = lines[i].strip()
            current_line = i + 1

            if not line or line.startswith("//"):
                i += 1
                continue

            # Verificar strings de múltiplas linhas
            if line.startswith('"""') or line.startswith("'''"):
                quote_type = line[:3]
                if not line.endswith(quote_type) or len(line) == 3:
                    # Coletar linhas até encontrar o fechamento
                    string_lines = [line[3:]]
                    i += 1
                    while i < len(lines):
                        sub_line = lines[i].rstrip()
                        if sub_line.endswith(quote_type):
                            string_lines.append(sub_line[:-3])
                            i += 1
                            break
                        string_lines.append(sub_line)
                        i += 1
                    if i >= len(lines) and not (string_lines[-1].endswith(quote_type)):
                        raise ValueError(f"[Syntax Error] Unclosed triple quotes at line {current_line}")
                    full_string = "\n".join(string_lines)
                    # Verificar se é parte de uma chamada de função
                    call_match = re.match(r'(\w+)\s*\(\s*(.*?)\s*\)', line)
                    if call_match and call_match.group(1) in self.env:
                        func_name = call_match.group(1)
                        args_str = f'"""{full_string}"""'
                        args, kwargs = self._parse_arguments(args_str)
                        evaluated_args = [full_string]  # Já processado como string de múltiplas linhas
                        evaluated_kwargs = {}
                        self.env[func_name](*evaluated_args, variables=self.variables, input_func=input_func, output_func=output_func)
                        continue
                    else:
                        raise ValueError(f"[Syntax Error] Invalid use of triple quotes at line {current_line}")
                else:
                    line = clean_line(line)

            # Remover comentários, preservando // dentro de strings
            line = clean_line(line)

            if not line:
                i += 1
                continue

            assign_match = re.match(r'(\w+)\s*=\s*(.+)', line)
            if assign_match:
                var_name, value_expr = assign_match.groups()
                result = self.evaluate_expression(value_expr, input_func, output_func)
                self.variables[var_name] = result
                i += 1
                continue

            reg_match = re.match(r'reg\s+(\w+)\s*\((.*?)\)\s*\(', line)
            if reg_match:
                func_name = reg_match.group(1)
                params = [p.strip() for p in reg_match.group(2).split(',')] if reg_match.group(2).strip() else []
                body_lines = []
                i += 1
                parens = 1
                while i < len(lines):
                    sub_line = lines[i].rstrip()
                    if not sub_line or sub_line.startswith("//"):
                        i += 1
                        continue
                    in_quotes = False
                    in_triple_quotes = False
                    quote_char = None
                    for j, char in enumerate(sub_line):
                        if j <= len(sub_line) - 3 and sub_line[j:j+3] in ('"""', "'''") and not in_quotes:
                            if in_triple_quotes and sub_line[j:j+3] == quote_char:
                                in_triple_quotes = False
                                quote_char = None
                            elif not in_triple_quotes:
                                in_triple_quotes = True
                                quote_char = sub_line[j:j+3]
                        elif char in ('"', "'") and not in_triple_quotes:
                            if in_quotes and char == quote_char:
                                in_quotes = False
                                quote_char = None
                            elif not in_quotes:
                                in_quotes = True
                                quote_char = char
                        elif not in_quotes and not in_triple_quotes:
                            if char == '(':
                                parens += 1
                            elif char == ')':
                                parens -= 1
                    if parens == 0:
                        break
                    body_lines.append(sub_line)
                    i += 1
                if parens != 0:
                    raise ValueError(f"[Syntax Error] Unclosed function body for '{func_name}' at line {current_line}")
                self.functions[func_name] = NexusFunction(func_name, params, body_lines)
                i += 1
                continue

            invalid_multiplication_match = re.match(r'(\w+\([^)]*\))\*(\d+)', line)
            if invalid_multiplication_match:
                raise ValueError(f"[Syntax Error] Multiplication of function call is not allowed: {line}. Use multiplication inside the string (ex.: t\"text\"*4).")

            call_match = re.match(r'(\w+)(?:\.(\w+))?\((.*)\)', line)
            if call_match:
                obj_name, func_name, args_str = call_match.groups()
                args, kwargs = self._parse_arguments(args_str)
                evaluated_args = []
                for arg in args:
                    arg_stripped = arg.strip()
                    if (arg_stripped.startswith('"') and arg_stripped.endswith('"')) or (arg_stripped.startswith("'") and arg_stripped.endswith("'")):
                        evaluated_args.append(arg_stripped[1:-1])
                    elif (arg_stripped.startswith('"""') and arg_stripped.endswith('"""')) or (arg_stripped.startswith("'''") and arg_stripped.endswith("'''")):
                        evaluated_args.append(arg_stripped[3:-3])
                    elif arg_stripped.startswith('t"') or arg_stripped.startswith("t'"):
                        evaluated_args.append(arg_stripped)
                    else:
                        evaluated_args.append(self.evaluate_expression(arg, input_func, output_func))
                evaluated_kwargs = {}
                for k, v in kwargs.items():
                    v_stripped = v.strip()
                    if (v_stripped.startswith('"') and v_stripped.endswith('"')) or (v_stripped.startswith("'") and v_stripped.endswith("'")):
                        evaluated_kwargs[k] = v_stripped[1:-1]
                    elif (v_stripped.startswith('"""') and v_stripped.endswith('"""')) or (v_stripped.startswith("'''") and v_stripped.endswith("'''")):
                        evaluated_kwargs[k] = v_stripped[3:-3]
                    elif v_stripped.startswith('t"') or v_stripped.startswith("t'"):
                        evaluated_kwargs[k] = v_stripped
                    else:
                        evaluated_kwargs[k] = self.evaluate_expression(v, input_func, output_func)

                if func_name:
                    if obj_name in self.variables:
                        ns = self.variables[obj_name]
                        if hasattr(ns, func_name):
                            fn = getattr(ns, func_name)
                            if callable(fn):
                                result = fn(*evaluated_args, **evaluated_kwargs)
                                if output_func and result is not None:
                                    output_func(str(result))
                                i += 1
                                continue
                        raise ValueError(f"[Runtime Error] Function '{func_name}' not found in module '{obj_name}'")
                else:
                    func_name = obj_name
                    if func_name in self.functions:
                        self.functions[func_name].execute(self, evaluated_args, input_func, output_func)
                    elif func_name in self.env:
                        if func_name == "nexus_input":
                            result = self.env[func_name](*evaluated_args, input_func=input_func, output_func=output_func)
                            self.variables["__last_input__"] = result
                            if output_func and result is not None:
                                output_func(str(result))
                        else:
                            func = self.env[func_name]
                            sig = inspect.signature(func)
                            call_kwargs = {}
                            if 'variables' in sig.parameters:
                                call_kwargs['variables'] = self.variables
                            if 'output_func' in sig.parameters:
                                call_kwargs['output_func'] = output_func
                            call_kwargs.update(evaluated_kwargs)
                            result = func(*evaluated_args, **call_kwargs)
                            if output_func and result is not None and func_name != "printf":
                                output_func(str(result))
                    else:
                        raise ValueError(f"[Runtime Error] Unknown function '{func_name}'")
                i += 1
                continue

            if_match = re.match(r'(if|elif)\s+(.+)\s+\(', line)
            else_match = re.match(r'else\s+\(', line)

            if if_match or else_match:
                if if_match:
                    keyword, condition_expr = if_match.groups()
                    condition_result = self.evaluate_expression(condition_expr, input_func, output_func)
                    execute_block = bool(condition_result) and not skip_next_block
                else:
                    execute_block = not skip_next_block

                block_lines = []
                i += 1
                parens = 1
                while i < len(lines):
                    sub_line = lines[i].rstrip()
                    if not sub_line or sub_line.startswith("//"):
                        i += 1
                        continue
                    in_quotes = False
                    in_triple_quotes = False
                    quote_char = None
                    for j, char in enumerate(sub_line):
                        if j <= len(sub_line) - 3 and sub_line[j:j+3] in ('"""', "'''") and not in_quotes:
                            if in_triple_quotes and sub_line[j:j+3] == quote_char:
                                in_triple_quotes = False
                                quote_char = None
                            elif not in_triple_quotes:
                                in_triple_quotes = True
                                quote_char = sub_line[j:j+3]
                        elif char in ('"', "'") and not in_triple_quotes:
                            if in_quotes and char == quote_char:
                                in_quotes = False
                                quote_char = None
                            elif not in_quotes:
                                in_quotes = True
                                quote_char = char
                        elif not in_quotes and not in_triple_quotes:
                            if char == '(':
                                parens += 1
                            elif char == ')':
                                parens -= 1
                    if parens == 0:
                        break
                    block_lines.append(sub_line)
                    i += 1
                if parens != 0:
                    raise ValueError(f"[Syntax Error] Unclosed block at line {current_line}")
                if execute_block:
                    self.run_nexus_code("\n".join(block_lines), input_func, output_func)
                    skip_next_block = True
                else:
                    skip_next_block = False
                i += 1
                continue

            raise ValueError(f"[Syntax Error] Unrecognized command: '{line}' at line {current_line}")
