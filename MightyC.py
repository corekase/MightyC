#!/bin/env python
import os, sys, subprocess, argparse, logging, re
from enum import Enum
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

Token = Enum("Token", "WHITESPACE LPAREN RPAREN LBRACE RBRACE SEMICOLON INT \
              VOID RETURN IDENTIFIER CONSTANT")

class Lexer:
    TOKENS = (
        (re.compile(r'\s+'), Token.WHITESPACE),
        (re.compile(r'\('), Token.LPAREN),
        (re.compile(r'\)'), Token.RPAREN),
        (re.compile(r'\{'), Token.LBRACE),
        (re.compile(r'\}'), Token.RBRACE),
        (re.compile(r';'), Token.SEMICOLON),
        (re.compile(r'int\b'), Token.INT),
        (re.compile(r'void\b'), Token.VOID),
        (re.compile(r'return\b'), Token.RETURN),
        (re.compile(r'(?<!\d)(?:[a-zA-Z_]\w*|0-9+)(?!\w)'), Token.IDENTIFIER),
        (re.compile(r'[0-9]+'), Token.CONSTANT)
    )
    NON_TOKEN = re.compile(r'\S+')

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
                    if token_type != Token.WHITESPACE:
                        tokens.append((token_type, match.group()))
                    break
            if not matched:
                match = Lexer.NON_TOKEN.match(data, position)
                if match:
                    unknown_token = match.group()
                else:
                    unknown_token = "unknown"
                print(f"Unexpected token {unknown_token}")
                sys.exit(1)
        return tokens

class Parser:
    def __init__(self, tokens: List[Tuple[Token, str]]):
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
        self.expect(Token.INT)
        name = self.expect(Token.IDENTIFIER)[1]
        self.expect(Token.LPAREN)
        self.expect(Token.VOID)
        self.expect(Token.RPAREN)
        self.expect(Token.LBRACE)
        statement = self.parse_statement()
        self.expect(Token.RBRACE)
        return Function(name, [statement])

    def parse_statement(self) -> "Return":
        """Parse a return statement"""
        self.expect(Token.RETURN)
        expression = self.parse_expression()
        self.expect(Token.SEMICOLON)
        return Return([expression])

    def parse_expression(self) -> "Constant":
        """Parse a constant expression"""
        literal = self.expect(Token.CONSTANT)[1]
        return Constant(literal)

    def expect(self, expected_type: Token) -> Tuple[Token, str]:
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
        self.parser = argparse.ArgumentParser(description='C Compiler Toolchain')
        self.parser.add_argument('file', type=str, help='Input C source file')
        self.parser.add_argument('-S', action='store_true', help='Generate assembly code')
        self.parser.add_argument('--lex', action='store_true', help='Only perform lexical analysis')
        self.parser.add_argument('--parse', action='store_true', help='Only perform parsing')
        self.parser.add_argument('--codegen', action='store_true', help='Only perform code generation')
        self.args = self.parser.parse_args()

        # Validate file name
        if not self._validate_file(self.args.file):
            self._invalid_filename()

    def _validate_file(self, file_path: str) -> bool:
        """Validate the input file exists and has the correct extension."""
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return False
        if not file_path.endswith('.c'):
            logging.error(f"Invalid file extension. Expected .c, got {file_path}")
            return False
        return True

    def _invalid_filename(self):
        """Log error and exit with non-zero code."""
        logging.error("Invalid filename")
        sys.exit(1)

    def _run_command(self, command: list, description: str):
        """Execute a subprocess command and log the output."""
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            logging.info(f"{description} completed successfully")
            return result.returncode
        except subprocess.CalledProcessError as e:
            logging.error(f"{description} failed: {e.stderr}")
            sys.exit(1)

    def _cleanup(self):
        """Clean up intermediate files."""
        for ext in ('.i', '.s', '.o'):
            file_path = f"{self.args.file[:-2]}{ext}"
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Removed intermediate file: {file_path}")

    def preprocess(self):
        """Preprocess the C source file."""
        output_file = f"{self.args.file[:-2]}.i"
        command = ["gcc", "-E", "-P", f"{self.args.file}", "-o", output_file]
        self._run_command(command, "Preprocessing")

    def lex(self):
        """Perform lexical analysis."""
        tokens = Lexer().analyze(self.args.file[:-2])
        logging.info(f"Lexical analysis completed. Found {len(tokens)} tokens")
        if self.args.lex:
            logging.info("Exiting after lexical analysis")
            sys.exit(0)
        return tokens

    def parse(self, tokens):
        """Parse tokens into an AST."""
        ast = Parser(tokens).parse()
        ast.print_ast()
        if self.args.parse:
            logging.info("Exiting after parsing")
            sys.exit(0)
        return ast

    def codegen(self, ast):
        """Generate assembly code from AST."""
        self._run_command(["gcc", "-S", "-O", "-fno-asynchronous-unwind-tables", "-fcf-protection=none", f"{self.args.file[:-2]}.i", "-o", f"{self.args.file[:-2]}.s"], "Code generation")
        if self.args.codegen:
            logging.info("Exiting after code generation")
            sys.exit(0)

    def assemble(self, ast):
        """Assemble the code and handle options."""
        if self.args.S:
            self._run_command(["rm", f"{self.args.file[:-2]}.i"], "Removing preprocessed file")
            sys.exit(0)

    def compile(self):
        """Compile the assembly to binary."""
        self._run_command(["gcc", f"{self.args.file[:-2]}.s", "-o", self.args.file[:-2]], "Compiling to executable")

    def run(self):
        """Main execution flow."""
        try:
            self.preprocess()
            tokens = self.lex()
            ast = self.parse(tokens)
            self.codegen(ast)
            self.assemble(ast)
            self.compile()
            self._cleanup()
            logging.info("Compilation completed successfully")
        except Exception as e:
            logging.error(f"Compilation failed: {str(e)}")
            sys.exit(1)

if __name__ == "__main__":
    Driver().run()
