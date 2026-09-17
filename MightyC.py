#!/bin/env python
import sys, subprocess, re

class Lexer:
    TOKENS = (
        (re.compile(r'\s+'), "whitespace"),
        (re.compile(r'\('), "("),
        (re.compile(r'\)'), ")"),
        (re.compile(r'\{'), "{"),
        (re.compile(r'\}'), "}"),
        (re.compile(r';'), ";"),
        (re.compile(r'int\b'), "int"),
        (re.compile(r'void\b'), "void"),
        (re.compile(r'return\b'), "return"),
        (re.compile(r'(?<!\d)(?:[a-zA-Z_]\w*|0-9+)(?!\w)'), "identifier"),
        (re.compile(r'[0-9]+'), "constant")
    )
    NONTOKEN = re.compile(r'\S+')

    def analyze(self, file_name):
        try:
            with open(f"{file_name}.i", "r") as file:
                data = file.read()
        except FileNotFoundError:
            print(f"Error: File {file_name}.i not found")
            sys.exit(1)
        tokens = []
        position = 0
        end_position = len(data)
        while position < end_position:
            matched = False
            for pattern, token_type in Lexer.TOKENS:
                match = pattern.match(data, position)
                if match:
                    matched = True
                    position = match.end()
                    if token_type != "whitespace":
                        tokens.append((token_type, match.group()))
                    break
            if not matched:
                match = Lexer.NONTOKEN.match(data, position)
                if match:
                    unknown_token = match.group()
                else:
                    unknown_token = "unknown"
                print(f"Unexpected token {unknown_token}")
                sys.exit(1)
        return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.end = len(self.tokens)

    def parse_program(self):
        program = Program([self.parse_function()])
        if self.pos != self.end:
            print("error: extra tokens found at end of input")
            sys.exit(1)
        return program

    def parse_function(self):
        self.expects("int")
        name = self.expects("identifier")[1]
        self.expects("(")
        self.expects("void")
        self.expects(")")
        self.expects("{")
        statement = self.parse_statement()
        self.expects("}")
        node = Function(name, [statement])
        return node

    def parse_statement(self):
        self.expects("return")
        constant = self.parse_exp()
        self.expects(";")
        return Return([constant])

    def parse_exp(self):
        literal = self.expects("constant")[1]
        return Constant(literal)

    def expects(self, expected):
        if self.pos >= self.end:
            print(f"unexpected end of input, expected: {expected}")
            sys.exit(1)
        token_type, literal = self.tokens[self.pos]
        if token_type != expected:
            print(f"syntax error, expected: {expected}, actual {token_type}")
            sys.exit(1)
        self.pos += 1
        return token_type, literal

class ASTNode:
    def __init__(self, node_type, children=[]):
        self.type = node_type
        self.children = children

    def add_child(self, child):
        self.children.append(child)

    def print_ast(self, indent=0):
        print("  " * indent + f"{self.type}")
        self.more_info(indent)
        for child in self.children:
            child.print_ast(indent + 1)

    def more_info(self, indent=0):
        # override in subclasses
        pass

class Program(ASTNode):
    def __init__(self, children=[]):
        super().__init__("program", children)

class Function(ASTNode):
    def __init__(self, name, children=[]):
        super().__init__("function", children)
        self.name = name

    def more_info(self, indent=0):
        print("  " * indent + " -> " + self.name)

class Return(ASTNode):
    def __init__(self, children=[]):
        super().__init__("return", children)

class Constant(ASTNode):
    def __init__(self, value):
        super().__init__("constant")
        self.value = value

    def more_info(self, indent=0):
        print("  " * indent + " -> " + self.value)

class Driver:
    def __init__(self):
        arguments = sys.argv[1:]
        if not arguments:
            self.invalid_filename()
        else:
            if arguments[0].startswith("-"):
                if len(arguments) < 2:
                    self.invalid_filename()
                else:
                    self.option = arguments[0]
                    file_name = arguments[1]
            else:
                if len(arguments) != 1:
                    self.invalid_filename()
                else:
                    file_name = arguments[0]
                    self.option = ""
            # Validate file name
            if len(file_name) < 2 or not file_name.endswith(".c"):
                self.invalid_filename()
            else:
                self.file_name = file_name[:-2]

    def invalid_filename(self):
        print("invalid filename")
        sys.exit(1)

    def invoke(self, params):
        return subprocess.run(params, capture_output=True, text=True).returncode

    def codegen(self):
        self.invoke(["gcc", "-S", "-O", "-fno-asynchronous-unwind-tables", "-fcf-protection=none", f"{self.file_name}.i", f"-o{self.file_name}.s"])

    def assemble(self):
        # lexical tokenization
        tokens = Lexer().analyze(self.file_name)
        print(tokens)
        if self.option == "--lex":
            self.cleanup()
            sys.exit(0)
        # parse lexical list into abstract syntax tree
        ast = Parser(tokens).parse_program()
        ast.print_ast()
        if self.option == "--parse":
            self.cleanup()
            sys.exit(0)
        # generate assembly code from ast
        self.codegen()
        if self.option == "-S":
            # delete preprocessed file, but not the assembly file
            self.invoke(["rm", f"{self.file_name}.i"])
            sys.exit(0)
        if self.option == "--codegen":
            self.cleanup()
            sys.exit(0)

    def cleanup(self):
        # delete preprocessed file
        self.invoke(["rm", f"{self.file_name}.i"])
        # delete assembly file
        self.invoke(["rm", f"{self.file_name}.s"])

    def run(self):
        print(f"Processing file: {self.file_name}.c")
        # preprocess input file
        self.invoke(["gcc", "-E", "-P", f"{self.file_name}.c", f"-o{self.file_name}.i"])
        # compile processed input file to assembly
        self.assemble()
        # compile assembly to binary executable
        self.invoke(["gcc", f"{self.file_name}.s", f"-o{self.file_name}"])
        # remove intermediate files
        self.cleanup()
        # return no errors
        sys.exit(0)

if __name__ == "__main__":
    Driver().run()
