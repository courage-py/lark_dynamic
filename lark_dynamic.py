from typing import List, Union

Renderable = Union[str, list, tuple, "Token"]

def add_tab(text):
    return ("\n" + text).replace("\n", "\n    ") + "\n" if text else ""


def is_rule(s):
    return s.islower() and s.isidentifier()


def is_term(s):
    return s.isupper() and s.isidentifier()


class Grammar:
    def __init__(self):
        self.__rules = {}
        self.__terminals = {}
        self.__directives = []
        self.__templates = {}

    def generate(self, **context):
        return "".join(self.iter(context)).strip()

    def iter(self, context):
        for terminal in self.__terminals.values():
            yield from terminal.render(context)
            yield "\n"
        yield "\n"
        for rule in self.__rules.values():
            yield from rule.render(context)
            yield "\n"
        yield "\n"
        for directive in self.__directives:
            yield from directive.render(context)
            yield "\n"
        for template in self.__templates.values():
            yield from template.render(context)
            yield "\n"
        yield "\n"

    def make_rule(self, name, tokens, modifier="", priority=1):
        if not is_rule(name):
            raise ValueError(
                f"Invalid rule name: '{name}'. Rule names must only contain chars [a-z0-9_] and cannot start with a digit"
            )
        if name in self.__rules:
            raise NameError(f"Rule '{name}' already exists")
        if isinstance(tokens, Modifier):
            tokens, modifier = tokens.tokens, tokens.type
        if not isinstance(tokens, (tuple, list)):
            tokens = (tokens,)
        ruledef = RuleDef(name, tokens, modifier, priority)
        self.__rules[name] = ruledef
        return ruledef

    def make_terminal(self, name, tokens, modifier="", priority=1):
        if not is_term(name):
            raise ValueError(
                f"Invalid terminal name: '{name}'. Terminal names only contain chars [A-Z0-9_] and cannot start with a digit"
            )
        if name in self.__terminals:
            raise NameError(f"Terminal '{name}' already exists")

        if isinstance(tokens, Modifier):
            tokens, modifier = tokens.tokens, tokens.type

        if not isinstance(tokens, (tuple, list)):
            tokens = (tokens,)

        termdef = TerminalDef(name, tokens, modifier, priority)
        self.__terminals[name] = termdef
        return termdef

    def make_directive(self, name, content):
        directivedef = DirectiveDef(name, content)
        self.__directives.append(directivedef)
        return directivedef

    def make_template(self, name, args, tokens, modifier=""):
        if isinstance(tokens, Modifier):
            tokens, modifier = tokens.tokens, tokens.type

        if not isinstance(tokens, (tuple, list)):
            tokens = (tokens,)

        templatedef = TemplateDef(name, args, tokens, modifier)
        self.__templates[name] = templatedef
        return templatedef

    def __setattr__(self, attr: str, value):
        if not attr.startswith("__"):
            if is_rule(attr):
                return self.make_rule(attr, value)
            if is_term(attr):
                return self.make_terminal(attr, value)
        super().__setattr__(attr, value)

    def __getattr__(self, attr):
        if is_rule(attr):
            return Rule(attr, self)
        if is_term(attr):
            return Terminal(attr, self)
        return super().__getattr__(attr)

    def __repr__(self):
        return "\n\n".join(
            [
                *[repr(rule) for rule in self.__rules.values()],
                *[repr(term) for term in self.__terminals.values()],
                *[repr(directive) for directive in self.__directives],
            ]
        )


class Modifier:
    def __init__(self, type_, *tokens):
        self.type = type_
        self.tokens = tokens

    def __call__(self, *tokens):
        new = Modifier(self.type, *tokens)
        return new


# for rules
Modifier.INLINE = Modifier("_")
Modifier.INLINE_SINGLE = Modifier("?")
Modifier.KEEP_TERMINALS = Modifier("!")
# for terminals
Modifier.ANONYMOUS = Modifier("_")


class Token:
    def get_name(self):
        return self.__class__.__name__

    def repr_children(self):
        return ""

    def __repr__(self):
        return f"{self.get_name()}({add_tab(self.repr_children())})"

    def render(self, context) -> List[Renderable]:
        pass

    @staticmethod
    def render_str(token, context):
        if isinstance(token, tuple):
            yield from Group(*token).render(context)
        elif isinstance(token, list):
            yield from Optional(*token).render(context)
        elif isinstance(token, str):
            yield '"'
            yield token.replace('"', '\\"')
            yield '"'
        else:
            yield from token.render(context)

    def __or__(self, other):
        return Option(self, other)

    def __ror__(self, other):
        return Option(other, self)


class Definition(Token):
    def __init__(self, name, tokens, modifier="", priority=1):
        self.name = name
        self.tokens = tokens
        self.modifier = modifier
        self.priority = priority

    def render(self, context):
        yield self.modifier
        yield self.name
        if self.priority != 1:
            yield "."
            yield str(self.priority)
        yield ":"
        for token in self.tokens:
            yield " "
            yield from Token.render_str(token, context)

    def repr_children(self):
        return "\n".join(map(repr, self.tokens))


class RuleDef(Definition):
    pass


class TerminalDef(Definition):
    pass


class DirectiveDef(Definition):
    def __init__(self, name, content):
        self.name = name
        self.content = content

    def render(self, context):
        yield "%"
        yield self.name
        yield " "
        if isinstance(self.content, Token):
            yield from self.content.render(context)
        else:
            yield self.content

    def repr_children(self):
        return repr(self.content)


class TemplateDef(Definition):
    def __init__(self, name, args, tokens, modifier=""):
        self.name = name
        self.args = args
        self.tokens = tokens
        self.modifier = modifier

    def render(self, context):
        yield self.modifier
        yield self.name
        yield "{"
        if isinstance(self.args, Group):
            args = self.args.children[:]
        elif isinstance(self.args, (tuple, list)):
            args = self.args[:]
        else:
            args = (self.args,)
        for arg in args[:-1]:
            yield from Token.render_str(arg, context)
            yield ", "
        yield from Token.render_str(args[-1], context)
        yield "}:"
        for token in self.tokens:
            yield " "
            yield from Token.render_str(token, context)


class Combinator(Token):
    def __init__(self, *children):
        self.children = children

    def repr_children(self):
        return "\n".join(map(repr, self.children))


class Some(Combinator):
    def render(self, context):
        yield from Group(*self.children).render(context)
        yield "*"


class Many(Combinator):
    def render(self, context):
        yield from Group(*self.children).render(context)
        yield "+"


class Maybe(Combinator):
    def render(self, context):
        yield from Group(*self.children).render(context)
        yield "?"


class Optional(Combinator):
    def render(self, context):
        yield "["
        yield " "
        for child in self.children:
            yield from Token.render_str(child, context)
            yield " "
        yield "]"


class Group(Combinator):
    def render(self, context):
        yield "("
        yield " "
        for child in self.children:
            yield from Token.render_str(child, context)
            yield " "
        yield ")"


class Option(Combinator):
    def render(self, context):
        for child in self.children[:-1]:
            yield from Token.render_str(child, context)
            yield " | "
        yield from Token.render_str(self.children[-1], context)


class OptionG(Combinator):
    def render(self, context):
        yield "("
        for child in self.children[:-1]:
            yield from Token.render_str(child, context)
            yield " | "
        yield from Token.render_str(self.children[-1], context)
        yield ")"


class ManySeparated(Combinator):
    def __init__(self, sep, token):
        self.sep = sep
        self.token = token

    def render(self, context):
        yield from Token.render_str(self.token, context)
        yield from Group(self.sep, self.token).render(context)
        yield "+"

    def repr_children(self):
        return "".join([repr(self.token), " (", '","', repr(self.token), ")*"])


class SomeSeparated(Combinator):
    def __init__(self, sep, token):
        self.sep = sep
        self.token = token

    def render(self, context):
        yield "("
        yield from Token.render_str(self.token, context)
        yield " "
        yield from Group(self.sep, self.token).render(context)
        yield "*"
        yield ")"

    def repr_children(self):
        return "".join([repr(self.token), " (", '","', repr(self.token), ")*"])


class Repeat(Token):
    def __init__(self, content, number_or_range):
        self.content = content
        self.number_or_range = number_or_range

    def render(self, context):
        yield from Group(self.content).render(context)
        yield " ~ "
        if isinstance(self.number_or_range, (list, tuple)):
            yield "..".join(map(str, self.number_or_range))
        else:
            yield str(self.number_or_range)


class Literal(Token):
    def __init__(self, string: str, case_insensitive=False):
        self.string = string
        self.case_insensitive = case_insensitive

    def render(self, context):
        string = self.string.replace('"', '\\"')
        yield f'"{string}"'
        if self.case_insensitive:
            yield "i"

    @property
    def i(self):
        return Literal(self.string, True)

    def repr_children(self):
        return "".join(self.render({}))


class Range(Token):
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def render(self, context):
        yield from Token.render_str(self.start, context)
        yield ".."
        yield from Token.render_str(self.end, context)

    def repr_children(self):
        return "\n".join(map(repr, [self.start, self.end]))

class RegExp(Token):
    def __init__(self, regexp: str, flags: str = ""):
        self.regexp = regexp
        self.flags = flags

    def render(self, context):
        yield f"/{self.regexp}/{self.flags}"

    def repr_children(self):
        return "".join(self.render({}))


class Variable(Token):
    def __init__(self, callback):
        self.callback = callback

    def render(self, context):
        yield from Token.render_str(
            self.callback(context), context
        )

    def repr_children(self):
        return str(self.callback.__doc__ if self.callback.__doc__ else self.callback)


class Prerendered(Token):
    def __init__(self, string: str):
        self.string = string

    def render(self, context):
        yield self.string

    def repr_children(self):
        return self.string


class MetaAlias(type):
    def __getattr__(self, attr):
        return Alias(attr, ())


class Alias(Token, metaclass=MetaAlias):
    def __init__(self, name, tokens):
        self.name = name
        self.tokens = tokens

    def __call__(self, *tokens):
        self.tokens = tokens
        return self

    def render(self, context):
        for token in self.tokens:
            yield from Token.render_str(token, context)
            yield " "
        yield "-> "
        yield self.name

    def __repr__(self):
        return f"{self.get_name()}:{self.name}({add_tab(self.repr_children())})"

    def repr_children(self):
        return "\n".join(map(repr, self.tokens))


class Template(Token):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def render(self, context):
        yield self.name
        yield "{"
        yield from Token.render_str(self.args, context)
        yield "}"

    def repr_children(self):
        return "\n".join(map(repr, self.args))


class BoolVariable(Variable):
    def __init__(self, callback, key, default=False):
        self.callback = lambda context: callback(context.get(key, default))


def makeBoolVariable(key, true, false, default=False):
    return BoolVariable(lambda value: [false, true][value], key, default)


# aliases
class Star(Some):
    pass


class Plus(Many):
    pass


class QuestionMark(Maybe):
    pass


class Brackets(Optional):
    pass


class Parens(Group):
    pass


class Regexp(RegExp):
    pass


class Rule(Prerendered):
    def __init__(self, string, grammar):
        # print("NEW RULE", string)
        self.string = string
        self.grammar = grammar

    def __getitem__(self, item):
        # print("RULE GETITEM", self.string, item)
        return Template(self.string, item)

    def __setitem__(self, item, value):
        if isinstance(item, int):
            return self.grammar.make_rule(self.string, value, "", item)
        return self.grammar.make_template(self.string, item, value)


class Terminal(Prerendered):
    def __init__(self, string, grammar):
        self.string = string
        self.grammar = grammar

    def __setitem__(self, item, value):
        if isinstance(item, int):
            return self.grammar.make_terminal(self.string, value, "", item)
        raise TypeError(f"Priority must be an integer, not {type(item).__name__}")


Empty = Prerendered("")
