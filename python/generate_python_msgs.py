

import sys
import re
from typing import List

CSharp_TO_Python_TYPES = {
    "int": "int",
    "string": "str",
    "bool": "bool",
    "float": "float",
    "float[]": "List[float]",
    "int[]": "List[int]",
}

def convert_csharp_type_to_python(csharp_type):
    return CSharp_TO_Python_TYPES.get(csharp_type, csharp_type)

def extract_classes(code: str):
    # Match class name and body using braces ({}), even multiline
    pattern = r"public class (\w+)(?:\s*:\s*(\w+))?\s*\{([\s\S]*?)\n\}"
    return re.findall(pattern, code)

def extract_fields(class_body: str):
    lines = class_body.splitlines()
    fields = []
    for line in lines:
        match = re.match(r"\s*public\s+(\w+\[?\]?)\s+(\w+)\s*\{\s*get;\s*set;\s*\}", line.strip())
        if match:
            ctype, name = match.groups()
            fields.append((name, ctype))
    return fields

def generate_python_class(name, base_class, fields):
    base_class = base_class or "Message"
    if not fields:
        return f"class {name}({base_class}):\n    pass\n"

    args = ", ".join(f"{name}: {convert_csharp_type_to_python(ctype)} = None" for name, ctype in fields)
    init_lines = [f"    def __init__(self, {args}):"]
    init_lines += [f"        self.{name} = {name}" for name, _ in fields]
    return f"class {name}({base_class}):\n" + "\n".join(init_lines) + "\n"

def convert_csharp_to_python(csharp_code: str):
    output = [
        "from typing import List\n",
        "# Auto-generated from C#\n",
        "class Message:\n    pass\n"
    ]
    class_defs = extract_classes(csharp_code)
    for class_name, base_class, body in class_defs:
        fields = extract_fields(body)
        py_class = generate_python_class(class_name, base_class, fields)
        output.append(py_class)
    return "\n\n".join(output)

# === Example usage ===
if __name__ == "__main__":
    in_filename = sys.argv[1]
    with open(in_filename, "r") as f:  # Your C# message file
        csharp_code = f.read()

    python_code = convert_csharp_to_python(csharp_code)

    with open("messages.py", "w") as f:
        f.write(python_code)

    print("✅ Generated messages.py with fields.")

