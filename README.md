Dynamic grammar generator for [Lark parsing toolkit](https://github.com/lark-parser/lark)

# Why?

While writing EBNF by hand is a preferred approach for most use cases (because of rich syntax), it's only viable for static grammars.    
If your grammar is variable (e.g. based on some kind of configuration), it should be built with code on the fly.    
As per [lark#439](https://github.com/lark-parser/lark/issues/439), no API for grammar exists, so building a string is only solution (it's pretty fast though).

**This README implies you are familiar with Lark and Lark EBNF.**    

# Basic usage

```python
from lark_dynamic import *

g = Grammar()

g.DIGIT = g.NONZERO | "0"
g.NONZERO = Range("1", "9")
g.INTEGER = makeBoolVariable(
    "zero_leading_numbers", 
    true=Many(g.DIGIT), 
    false=(g.NONZERO, Some(g.DIGIT))
)
g.FLOAT[2] = Group(g.INTEGER, ".", Some(g.DIGIT)) | (".", Many(g.DIGIT))

g.number = Alias.integer(g.INTEGER) | Alias.float(g.FLOAT)

print(g.generate(zero_leading_numbers=False))
print(g.generate(zero_leading_numbers=True))
```

Which outputs:    
*zero_leading_numbers=False*:    
```
DIGIT: NONZERO | "0"
NONZERO: "1".."9"
INTEGER: ( NONZERO ( DIGIT )* )
FLOAT.2: ( INTEGER "." ( DIGIT )* ) | ( "." ( DIGIT )+ )

number: INTEGER -> integer | FLOAT -> float
```

*zero_leading_numbers=True*    
```
DIGIT: NONZERO | "0"
NONZERO: "1".."9"
INTEGER: ( DIGIT )+
FLOAT.2: ( INTEGER "." ( DIGIT )* ) | ( "." ( DIGIT )+ )

number: INTEGER -> integer | FLOAT -> float
```

# Getting started

Install with:

`python -m pip install lark-dynamic`

To create a grammar, you need to create `Grammar` object:
```python
from lark_dynamic import * # it is recommended to create grammar in a separate file, so * import is fine

g = Grammar() # short name is convenient
```

Then write rules and terminals:

```python
# this is a terminal (uppercase)
g.NUMBER = RegExp(r'[0-9]+')
g.SIGN = Literal("+") | "-" # first (or second) string needs to be wrapped into a Literal to support |
g.test = Maybe(g.SIGN), Many(g.TEST)
```

# Reference

All code snippets use this setup:
```python
from lark_dynamic import *
g = Grammar()
```

## Grammar

Main object, stores rules, terminals, templates and directives

To create a rule, you can use a shorthand:

```python
g.any_lowercase_identifier = ... # rule contents here
```

Same for terminal:

```python
g.ANY_UPPERCASE_IDENTIFIER = ... # terminal contents here
```

To create a template (`name{arg1, arg2} = ...`) you need to use `[]`:

```python
g.template_name[g.arg1, g.arg2] = ... # template contents here
```

Directives have different syntaxes, so no special shorthand is present:

```python
g.make_directive("name", "directive contents here")
```

To build grammar, you need to call `.generate(**context)`:

```python
g.generate(some_variable=True) # variables are discussed below
```

## Variable

Since the purpose of the module is to create grammars dynamically, this class exists.    
It takes a function, which accepts one argument (context) - a dictionary of everything passed to `.generate()`.    
Function sould return anything renderable (e.g. a token or a tuple of tokens):

```python
def integer_term(context):
    if context.get("zero_leading_numbers"):
        return Many(g.DIGIT)
    return g.NONZERO, Some(g.DIGIT)

g.DIGIT = g.NONZERO | "0"
g.NONZERO = Range("1", "9")
g.INTEGER = Variable(integer_term)
g.FLOAT[2] = Group(g.INTEGER, ".", Some(g.DIGIT)) | (".", Many(g.DIGIT))

g.number = Alias.integer(g.INTEGER) | Alias.float(g.FLOAT)
```
*(this is an example from Basic usage section rewritten to use Variable)*

### BoolVariable and makeBoolVariable

Common use case for Variable is to render different content based on a boolean key (such as in Basic usage example).    
`BoolVariable` makes it more convenient:

```python
def integer_term(zln):
    if zln:
        return Many(g.DIGIT)
    return g.NONZERO, Some(g.DIGIT)

g.DIGIT = g.NONZERO | "0"
g.NONZERO = Range("1", "9")
g.INTEGER = BoolVariable(integer_term, key="zero_leading_numbers")
g.FLOAT[2] = Group(g.INTEGER, ".", Some(g.DIGIT)) | (".", Many(g.DIGIT))

g.number = Alias.integer(g.INTEGER) | Alias.float(g.FLOAT)
```

`makeBoolVariable` goes even further, providing arguments for `True` and `False` values:

```python
g.DIGIT = g.NONZERO | "0"
g.NONZERO = Range("1", "9")
g.INTEGER = makeBoolVariable(
    "zero_leading_numbers", 
    true=Many(g.DIGIT), 
    false=(g.NONZERO, Some(g.DIGIT))
)
g.FLOAT[2] = Group(g.INTEGER, ".", Some(g.DIGIT)) | (".", Many(g.DIGIT))

g.number = Alias.integer(g.INTEGER) | Alias.float(g.FLOAT)
```

## Literal

Used for literal strings:

```python
g.hello = Literal("Hello"), Literal("World")
```
yields:

```
hello: "Hello" "World"
```

In most cases you can just use a string. Explicit `Literal(...)` is needed to support `|` (see [Combinators/Option](#option-usage-rules))

### Using regexp flags on Literal

```python
g.hello = Literal("Hello").si, Literal("World").i
```
yields:
```
hello: "Hello"si "World"i
```

## Combinators

### Maybe (aka QuestionMark)

Corresponds to `?` combinator in Lark:

```python
g.hello = "Hello", Maybe(","), "World", QuestionMark("!") # QuestionMark is just an alias for Maybe
```
yields:

```
hello: "Hello" (",")? "World" ("!")?
```

### Some (aka Star)

Corresponds to `*` combinator in Lark:

```python
g.hello = "Hello", Maybe(","), "World", Some("!")
```
yields:

```
hello: "Hello" (",")? "World" ("!")*
```

### Many (aka Plus)

Corresponds to `+` combinator in Lark:

```python
g.POSITION = Literal("two number 9s") | "a number 9 large" | "a number 6 with extra dip" | "a number 7" | "two number 45s" | "one with cheese" | "a large soda"

g.order = "I'll have ", g.position, Many(", ", g.position), Maybe(", and ", g.position)
g.position = g.POSITION
```
yields:

```
POSITION: "two number 9s" | "a number 9 large" | "a number 6 with extra dip" | "a number 7" | "two number 45s" | "one with cheese" | "a large soda"

order: "I'll have " position ( ", " position )+ ( ", and " position )?
position: POSITION
```

### Optional (aka Brackets)

Corresponds to `[...]` combinator in Lark:

```python
g.hello = "Hello", Optional(","), "World", ["!"]
```
yields:

```
hello: "Hello" [","] "World" ["!"]
```

Can also be written as `[...]` (as a list, basically), but be aware of [`|` usage rules (below)](#option-usage-rules)

### Option 

Corresponds to `|` combinator in Lark:

```python
g.hello = "Hello", Maybe(","), (Option("World", "dlroW"), ), Some("!") # note Option is placed inside a tuple, (explained below)
```
yields:

```
hello: "Hello" (",")? ("World" | "dlroW") ("!")*
```

Can also be written as `|`:
```python
g.hello = "Hello", Maybe(","), (Literal("World") | "dlroW", ), Some("!") # note Literal (explained below)
```

#### Option usage rules

**`|` priority in Lark is higher than in Python:**

`Maybe(","), Option("World", "dlroW"), Maybe("!")`    
yields    
`(",")? "World" | "dlroW" ("!")?`    
which, in turn, is equal to    
`(","? "World") | ("dlroW" "!"?)`    

You should wrap option with any other combinator (e.g. `Group()` or tuple. Remember that `(x)` is not a tuple) or just use `OptionG`.    
The reason why default `Option` doesn't do this is that wrapping top-level option in parens would break alias creation.

**`|` operator would not work with python built-in types (str, list or tuple)**

You need at least one `Token` (rule, combinator, literal etc.) on either side of `|` for it to work.

### Group (aka Parens)

Corresponds to `(...)` combinator in Lark:

```python
g.hello = "Hello", Group(Maybe(","), "World"), (Some("!"), )
```
yields:

```
hello: "Hello" ((",")? "World") (("!")*)
```

Can also be written as `(...)` (as a tuple, basically), but be aware of [`|` usage rules](#option-usage-rules)    
`Some`, `Many` and `Maybe` also will render in parenthesis by default to avoid combinator collision (e.g. to avoid rendering `(("!")+)?` as `"!"+?` which is invalid).

### SomeSeparated and ManySeparated

Correspond to `content (sep, content)*` and `content (sep, content)+` patterns, respectively:

```python
g.POSITION = Literal("two number 9s") | "a number 9 large" | "a number 6 with extra dip" | "a number 7" | "two number 45s" | "one with cheese" | "a large soda"
g._COMMA = ",", Maybe(g.WS)
g.WS = " "

g.order = "I'll have ", SomeSeparated(g._COMMA, g.position), Maybe(g._COMMA, "and ", g.position)
g.position = g.POSITION
```
yields:

```
POSITION: "two number 9s" | "a number 9 large" | "a number 6 with extra dip" | "a number 7" | "two number 45s" | "one with cheese" | "a large soda"
_COMMA: "," ( WS )?
WS: " "

order: "I'll have " (position ( _COMMA position )*) ( _COMMA "and " position )?
position: POSITION
```

## RegExp

Corresponds to Lark regexp syntax (`/content/flags`):

```python
g.WORD = RegExp(r"\w+") # flags are provided as a second argument (e.g. RegExp(r"\w+", "is")) 
g.some_phrase = g.WORD, Maybe(","), g.WORD, Some("!")
```
yields:
```
WORD: /\w+/

some_phrase: WORD ( "," )? WORD ( "!" )*
```

## Repeat

Corresponds to Lark repeat syntax: `item ~ n` and `item ~ n..m`:

```python
g.three_lemons = Repeat("Lemon", 3)
g.three_to_five_apples = Repeat("Lemon", [3, 5])
```
yields:
```
three_lemons: ( "Lemon" ) ~ 3
three_to_five_apples: ( "Lemon" ) ~ 3..5
```

## Prerendered

If you want to insert a prerendered content into a rule/terminal/template, you can use `Prerendered`:

```python
g.hello = "Hello", Prerendered('((",")? "World")'), Some("!")
```
yields:

```
hello: "Hello" ((",")? "World") ("!")*
```

### Empty

Sometimes (when using Variable) you'll need to render nothing.    
It can be achieved with `Prerendered("")`, or its alias, `Empty`

## Modifiers

Rule and terminal modifiers (such as `?` and `!`) can be used with `Modifier` class (**works only on top level of rule/terminal**):

```python
g.parens = Modifier.INLINE_SINGLE("(", g.word, ")")
g.word = g.WORD
g.WORD = RegExp(r"\w+")
```
yields:
```
WORD: /\w+/

?parens: "(" word ")"
word: WORD
```

# Priority

To use terminal/rule priority, you can use `[priority]` notation (similar to templates, but with a number):

```python
g.DIGIT = g.NONZERO | "0"
g.NONZERO = Range("1", "9")
g.INTEGER = g.NONZERO, Some(g.DIGIT)
g.FLOAT[2] = Group(g.INTEGER, ".", Some(g.DIGIT)) | (".", Many(g.DIGIT))

g.number = Alias.integer(g.INTEGER) | Alias.float(g.FLOAT)
```
yields:
```
DIGIT: NONZERO | "0"
NONZERO: "1".."9"
INTEGER: NONZERO ( DIGIT )*
FLOAT.2: ( INTEGER "." ( DIGIT )* ) | ( "." ( DIGIT )+ )

number: INTEGER -> integer | FLOAT -> float
```


# Advanced usage

`Grammar` object can be edited after its creation.

First, you need to get a grammar wrapper: `wrapper = grammar.use_wrapper()`


## Get a definition


```python

g = Grammar()


g.HELLO = "Hello"

wrapper = g.use_wrapper()

print(wrapper.get_def("HELLO")) 

# prints
# TerminalDef(
#     "Hello"
# )

``` 

## Replace definition contents


```python

g = Grammar()

g.HELLO = "Hello"

wrapper = g.use_wrapper()
wrapper.replace("HELLO", "World")


print(wrapper.get_def("HELLO")) 

# prints
# TerminalDef(
#     "World"
# )

``` 

## Edit definition


```python

g = Grammar()

g.HELLO = "Hello"

wrapper = g.use_wrapper()
wrapper.edit("HELLO", priority=10)


print(wrapper.get_def("HELLO")) 

# prints
# TerminalDef(
#     'Hello'
# )

``` 

## Extend definition


```python

g = Grammar()

g.HELLO = "Hello"

wrapper = g.use_wrapper()
wrapper.extend("HELLO", "World")


print(wrapper.get_def("HELLO")) 

# prints
# TerminalDef(
#     Option(
#         "Hello"
#         "World"
#     )
# )

``` 

## Getting all definitions / directives

You can get dictionaries with rules, terminals, templates, or a list of all directives with a wrapper:

```python

g = Grammar()
wrapper = g.use_wrapper()

wrapper.rules
wrapper.terminals
wrapper.templates
wrapper.directives
```


## Why a wrapper?

Because grammar object itself is used to create definitions with arbitrary names. Creating methods with common names would easily create a problem:


```python
g = Grammar()

g.edit = "EDIT", Some("blah")
g.save = "SAVE", Some(Option("lorem", "ipsum", "dolor", "sit", "amet"))

g.command = Option(g.edit, g.save) # g.edit used here as a rule, not method

```

