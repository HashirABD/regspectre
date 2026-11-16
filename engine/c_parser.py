"""C-subset parser for firmware snippets.

Turns a small, fixed subset of C into a list of Operation records. This is not
a C compiler. Register names and bit names come from engine/regmap.py.

Supported statements:
    UART_ISR = (1U << BIT);       direct assignment, kind WRITE
    UART_ISR |= (1U << BIT);      compound OR, kind RMW, mode SET
    UART_ISR &= ~(1U << BIT);     compound AND, kind RMW, mode CLR
    uint32_t s = UART_ISR;        read into a local, kind READ
    uint8_t d = UART_RDR;         read-to-clear read, kind READ
    void name(void) { ... }      handler scope marker; ops inside get handler=name

Operation.mask is the named bit mask M. For CLR it is the set of bits cleared.
Allowed expressions: (1U << BIT), where BIT is a bit name of the target register
or an integer 0..31; integer constants (decimal or hex); ~, | and &.
Anything else raises ParseError with the 1-based line of the offending token.
"""

import re
from dataclasses import dataclass

from engine.regmap import REGISTERS, bit_name_to_index

MASK32 = 0xFFFFFFFF

KIND_WRITE = "WRITE"
KIND_RMW = "RMW"
KIND_READ = "READ"
MODE_SET = "SET"
MODE_CLR = "CLR"

_TYPES = {"uint8_t", "uint16_t", "uint32_t"}
_LOOP_KEYWORDS = {"for", "while", "do"}
_CONDITIONAL_KEYWORDS = {"if", "else", "switch", "case", "default"}
_OTHER_KEYWORDS = {
    "return", "goto", "break", "continue", "int", "unsigned", "char", "short",
    "long", "volatile", "const", "static", "struct", "union", "enum", "typedef",
    "sizeof",
}
_POINTER_TOKENS = {"*", "->", "[", "]"}
_ALLOWED_OPS = {"=", "|=", "&=", "|", "&", "~", "(", ")", ";", "<<", "{", "}"}

_TOKEN_RE = re.compile(
    r"(?P<num>0[xX][0-9A-Fa-f]+[uUlL]*|[0-9]+[uUlL]*)"
    r"|(?P<id>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<op><<|->|\|=|&=|[^\sA-Za-z0-9_])"
    r"|\s+"
)


class ParseError(Exception):
    """An unsupported or malformed construct. Names the 1-based line."""

    def __init__(self, line, message):
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


class SymbolError(ParseError):
    """A register or bit name that is not in regmap."""


@dataclass
class Operation:
    kind: str
    reg: str
    mask: int
    mode: str = ""
    c_line: int | None = None
    handler: str = ""


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str
    line: int


def _tokenize(snippet):
    tokens = []
    for line_no, raw in enumerate(snippet.splitlines(), start=1):
        line = re.sub(r"/\*.*?\*/", " ", raw).split("//", 1)[0]
        pos = 0
        while pos < len(line):
            m = _TOKEN_RE.match(line, pos)
            if m.lastgroup is not None:
                tokens.append(_Token(m.lastgroup.upper(), m.group(), line_no))
            pos = m.end()
    return tokens


def _num_value(tok):
    m = re.fullmatch(r"(0[xX][0-9A-Fa-f]+|[0-9]+)[uUlL]*", tok.text)
    digits = m.group(1)
    if digits[:2] in ("0x", "0X"):
        value = int(digits, 16)
    elif len(digits) > 1 and digits[0] == "0":
        raise ParseError(tok.line, f"octal literal {tok.text} is not supported")
    else:
        value = int(digits, 10)
    if value > MASK32:
        raise ParseError(tok.line, f"integer constant {tok.text} does not fit in 32 bits")
    return value


def _is_unsupported(tok):
    return (
        tok.text in _POINTER_TOKENS
        or tok.text in ("?", ":")
        or (tok.kind == "OP" and tok.text not in _ALLOWED_OPS)
    )


def _unexpected(tok):
    if tok.text in _POINTER_TOKENS:
        return ParseError(
            tok.line, f"pointer arithmetic and dereference are not supported ('{tok.text}')"
        )
    if tok.text in ("?", ":"):
        return ParseError(tok.line, "conditional expressions are not supported")
    if tok.kind == "OP" and tok.text not in _ALLOWED_OPS:
        return ParseError(tok.line, f"operator '{tok.text}' is not supported")
    return ParseError(tok.line, f"unexpected '{tok.text}'")


class _Parser:
    def __init__(self, tokens):
        self._toks = tokens
        self._pos = 0

    def _peek(self, offset=0):
        i = self._pos + offset
        return self._toks[i] if i < len(self._toks) else None

    def _peek_text(self, offset=0):
        tok = self._peek(offset)
        return None if tok is None else tok.text

    def _next(self):
        tok = self._toks[self._pos]
        self._pos += 1
        return tok

    def _expect(self, text, line):
        tok = self._peek()
        if tok is None:
            raise ParseError(line, f"expected '{text}' before end of snippet")
        if tok.text == text:
            return self._next()
        if _is_unsupported(tok):
            raise _unexpected(tok)
        raise ParseError(tok.line, f"expected '{text}' but found '{tok.text}'")

    def program(self):
        ops = []
        handler = ""
        handler_line = 0
        while self._peek() is not None:
            tok = self._peek()
            if tok.text == "}":
                if not handler:
                    raise ParseError(tok.line, "'}' without an open handler")
                self._next()
                handler = ""
            elif tok.text == "void":
                if handler:
                    raise ParseError(tok.line, "nested handlers are not supported")
                handler_line = tok.line
                handler = self._handler_header()
            elif tok.kind == "ID" and tok.text in _LOOP_KEYWORDS:
                raise ParseError(tok.line, f"loops are not supported ('{tok.text}')")
            elif tok.kind == "ID" and tok.text in _CONDITIONAL_KEYWORDS:
                raise ParseError(tok.line, f"conditionals are not supported ('{tok.text}')")
            elif tok.kind == "ID" and tok.text in _OTHER_KEYWORDS:
                raise ParseError(tok.line, f"keyword '{tok.text}' is not supported")
            elif tok.text in _TYPES:
                ops.append(self._read_decl(handler))
            elif tok.kind == "ID" and tok.text in REGISTERS:
                ops.append(self._assign(handler))
            else:
                raise self._bad_statement(tok)
        if handler:
            raise ParseError(handler_line, f"handler '{handler}' is not closed")
        return ops

    def _handler_header(self):
        void_tok = self._next()
        name = self._peek()
        if name is None or name.kind != "ID":
            raise ParseError(void_tok.line, "expected a handler name after 'void'")
        self._next()
        self._expect("(", void_tok.line)
        self._expect("void", void_tok.line)
        self._expect(")", void_tok.line)
        self._expect("{", void_tok.line)
        return name.text

    def _bad_statement(self, tok):
        if _is_unsupported(tok):
            return _unexpected(tok)
        if tok.kind == "ID":
            if self._peek_text(1) == "(":
                return ParseError(tok.line, f"function calls are not supported ('{tok.text}')")
            return SymbolError(tok.line, f"unknown name '{tok.text}'")
        return ParseError(tok.line, f"unsupported statement starting with '{tok.text}'")

    def _read_decl(self, handler):
        type_tok = self._next()
        name = self._peek()
        if name is not None and name.text == "*":
            raise ParseError(type_tok.line, "pointer declarations are not supported")
        if name is None or name.kind != "ID":
            raise ParseError(type_tok.line, f"expected a variable name after '{type_tok.text}'")
        self._next()
        self._expect("=", type_tok.line)
        reg_tok = self._peek()
        if reg_tok is not None and reg_tok.kind == "ID" and reg_tok.text not in REGISTERS:
            raise SymbolError(reg_tok.line, f"unknown name '{reg_tok.text}'")
        if reg_tok is None or reg_tok.text not in REGISTERS:
            raise ParseError(type_tok.line, "a local may only be initialized from a register read")
        self._next()
        if self._peek_text() != ";":
            raise ParseError(
                type_tok.line, "a local may only be initialized from a plain register read"
            )
        self._next()
        return Operation(KIND_READ, reg_tok.text, 0, "", type_tok.line, handler)

    def _assign(self, handler):
        reg_tok = self._next()
        reg = reg_tok.text
        op_tok = self._peek()
        if op_tok is None or op_tok.text not in ("=", "|=", "&="):
            found = "end of snippet" if op_tok is None else f"'{op_tok.text}'"
            raise ParseError(
                reg_tok.line, f"expected '=', '|=' or '&=' after {reg}, found {found}"
            )
        if reg == "UART_RDR":
            raise ParseError(
                reg_tok.line, "UART_RDR is read-to-clear and cannot be written in this subset"
            )
        self._next()
        value = self._expr(reg)
        self._expect(";", reg_tok.line)
        if op_tok.text == "=":
            return Operation(KIND_WRITE, reg, value, "", reg_tok.line, handler)
        if op_tok.text == "|=":
            return Operation(KIND_RMW, reg, value, MODE_SET, reg_tok.line, handler)
        return Operation(KIND_RMW, reg, (~value) & MASK32, MODE_CLR, reg_tok.line, handler)

    def _expr(self, reg):
        value = self._and_expr(reg)
        while self._peek_text() == "|":
            self._next()
            value |= self._and_expr(reg)
        return value & MASK32

    def _and_expr(self, reg):
        value = self._unary(reg)
        while self._peek_text() == "&":
            self._next()
            value &= self._unary(reg)
        return value & MASK32

    def _unary(self, reg):
        if self._peek_text() == "~":
            self._next()
            return (~self._unary(reg)) & MASK32
        return self._primary(reg)

    def _primary(self, reg):
        tok = self._peek()
        if tok is None:
            raise ParseError(self._toks[-1].line, "expression is incomplete at end of snippet")
        if tok.text == "(":
            self._next()
            first = self._peek()
            if first is not None and first.kind == "NUM" and self._peek_text(1) == "<<":
                return self._shift(reg, tok.line)
            value = self._expr(reg)
            self._expect(")", tok.line)
            return value
        if tok.kind == "NUM":
            self._next()
            return _num_value(tok)
        if tok.kind == "ID":
            return self._name(reg)
        raise _unexpected(tok)

    def _shift(self, reg, line):
        base = _num_value(self._next())
        self._expect("<<", line)
        ref = self._peek()
        if ref is None:
            raise ParseError(line, "expected a bit name or index after '<<'")
        if ref.kind == "NUM":
            self._next()
            index = _num_value(ref)
            if index > 31:
                raise ParseError(ref.line, f"bit index {ref.text} is outside 0..31")
        elif ref.kind == "ID":
            self._next()
            try:
                index = bit_name_to_index(reg, ref.text)
            except KeyError:
                raise SymbolError(ref.line, f"unknown bit '{ref.text}' for {reg}") from None
        else:
            raise ParseError(ref.line, f"expected a bit name or index after '<<', found '{ref.text}'")
        self._expect(")", line)
        return (base << index) & MASK32

    def _name(self, reg):
        tok = self._next()
        if self._peek_text() == "(":
            raise ParseError(tok.line, f"function calls are not supported ('{tok.text}')")
        if tok.text in REGISTERS:
            raise ParseError(
                tok.line, "a register read is only allowed as a whole statement, e.g. uint32_t s = UART_ISR;"
            )
        try:
            bit_name_to_index(reg, tok.text)
        except KeyError:
            raise SymbolError(tok.line, f"unknown name '{tok.text}'") from None
        raise ParseError(tok.line, f"bit name '{tok.text}' must be used as (1U << {tok.text})")


def parse(snippet):
    """Parse a C-subset snippet into a list of Operation.

    Raises ParseError for unsupported constructs and SymbolError for unknown
    register or bit names. Both carry the 1-based line in .line.
    """
    return _Parser(_tokenize(snippet)).program()