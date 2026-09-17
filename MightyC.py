#!/bin/env python
import sys, subprocess, re
from enum import Enum
from typing import List, Optional, Tuple

class Tokens(Enum):
    """Enum for token types"""
    WHITESPACE = "whitespace"
    INT = "int"
    IDENTIFIER = "identifier"
    CONSTANT = "constant"
    LPAREN = "("
    RPAREN = ")"
    LBRACE = "{"
    RBRACE = "}"
    SEMICOLON = ";"
    RETURN = "return"
    VOID = "void"

class Lexer:
    TOKENS = (
        (re.compile(r'\s+'), Tokens.WHITESPACE),
        (re.compile(r'\('), Tokens.LPAREN),
        (re.compile(r'\)'), Tokens.RPAREN),
        (re.compile(r'\{'), Tokens.LBRACE),
        (re.compile(r'\}'), Tokens.RBRACE),
        (re.compile(r';'), Tokens.SEMICOLON),
        (re.compile(r'int\b'), Tokens.INT),
        (re.compile(r'void\b'), Tokens.VOID),
        (re.compile(r'return\b'), Tokens.RETURN),
        (re.compile(r'(?<!\d)(?:[a-zA-Z_]\w*|0-9+)(?!\w)'), Tokens.IDENTIFIER),
        (re.compile(r'[0-9]+'), Tokens.CONSTANT)
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
                    if token_type != Tokens.WHITESPACE:
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
    def __init__(self, tokens: List[Tuple[Tokens, str]]):
        self.tokens = tokens
        self.pos = 0
        self.end = len(tokens)

    def parse(self) -> "ASTNode":
        """Main parsing entry point"""
        program = self.parse_program()
        if self.pos != self.end:
            print(f"Unexpected tokens remaining at position {self.pos}")
            sys.exit(1)
        return program

    def parse_program(self) -> "Program":
        """Parse a program (single function)"""
        function = self.parse_function()
        return Program([function])

    def parse_function(self) -> "Function":
        """Parse a function declaration"""
        self.expect(Tokens.INT)
        name = self.expect(Tokens.IDENTIFIER)[1]
        self.expect(Tokens.LPAREN)
        self.expect(Tokens.VOID)
        self.expect(Tokens.RPAREN)
        self.expect(Tokens.LBRACE)
        statement = self.parse_statement()
        self.expect(Tokens.RBRACE)
        return Function(name, [statement])

    def parse_statement(self) -> "Return":
        """Parse a return statement"""
        self.expect(Tokens.RETURN)
        expression = self.parse_expression()
        self.expect(Tokens.SEMICOLON)
        return Return([expression])

    def parse_expression(self) -> "Constant":
        """Parse a constant expression"""
        literal = self.expect(Tokens.CONSTANT)[1]
        return Constant(literal)

    def expect(self, expected_type: Tokens) -> Tuple[Tokens, str]:
        """Expect a token of the specified type"""
        if self.pos > self.end:
            print(f"Unexpected end of input at position {self.pos}, expected: {expected_type}")
            sys.exit(1)
        token_type, literal = self.tokens[self.pos]
        self.pos += 1
        if token_type != expected_type:
            print(f"Unexpected token, actual: {token_type}, expected: {expected_type}")
            sys.exit(1)
        return token_type, literal

class ASTNode:
    """Base class for all AST nodes"""
    def __init__(self, node_type: str):
        self.type = node_type
        self.children: List["ASTNode"] = []

    def add_child(self, child: "ASTNode"):
        """Add a child node"""
        self.children.append(child)

    def print_ast(self, indent: int = 0):
        """Print the AST with indentation"""
        print("  " * indent + f"{self.type}")
        self.more_info(indent)
        for child in self.children:
            child.print_ast(indent + 1)

    def more_info(self, indent: int = 0):
        """Additional information for the node (override in subclasses)"""
        pass

class Program(ASTNode):
    """Program node containing a list of functions"""
    def __init__(self, children: List["ASTNode"] = None):
        super().__init__("program")
        if children:
            self.children = children

class Function(ASTNode):
    """Function node with name and body"""
    def __init__(self, name: str, children: List["ASTNode"] = None):
        super().__init__("function")
        self.name = name
        if children:
            self.children = children

    def more_info(self, indent: int = 0):
        """Print function name information"""
        print("  " * indent + f" -> {self.name}")

class Return(ASTNode):
    """Return statement node"""
    def __init__(self, children: List["ASTNode"] = None):
        super().__init__("return")
        if children:
            self.children = children

class Constant(ASTNode):
    """Constant value node"""
    def __init__(self, value: str):
        super().__init__("constant")
        self.value = value

    def more_info(self, indent: int = 0):
        """Print constant value information"""
        print("  " * indent + f" -> {self.value}")

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
        ast = Parser(tokens).parse()
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
