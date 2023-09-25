# -*- coding: utf-8 -*-
import typing
from   typing import *

"""
#
# This is an expansion of parsec 3.3 by He Tao. Changes include:
#
#  Added Explanatory comments.
#  Provided more natural English grammar for He Tao's comments. His comments
#   are included. New comments are marked with a preceding and following group
#   of three # characters, and the original docstrings use triple single quotes
#   rather than triple double quotes.
#  To the extent practical, alphabetized the functions.
#  Inserted type hints.
#  Added a __bool__ function to the Value class.
#  Changed some string searches to exploit constants in string module rather
#   than str functions that might be affected by locale.**
#  Changed name of any() function to any_char() to avoid conflicts with 
#   Python built-in of the same name.
#  Where practical, f-strings are used for formatting.
#  Revised for modern Python; no longer compatible with Python 2. This version
#   requires Python 3.8.
#  A number of definitions of characters are provided, and they
#   are named as standard symbols: TAB, NL, CR, etc.
#  Many custom parsers are likely to include parsers for common programming
#   elements (dates, IP addresses, timestamps). These are now included. 
#  There are two versions of the `string` parser. The new version consumes
#   no input on failure. The older version can be activated by defining
#   the environment variable PARSEC3_STRING. The value is unimportant; it 
#   only needs to be defined.
#
# ** A note on the use of the import statement. The import near the top of the 
#    file imports string, and creates an entry in the system modules table 
#    named 'string'. The use of the import statement inside the parser functions
#    merely references this already imported module's index in the sys.modules
#    table.
#
"""

###
# Credits
###
__author__ = 'George Flanagin'
__credits__ = """
He Tao, sighingnow@gmail.com --- original version
Alina Enikeeva, alina.enikeeva@richmond.edu --- documentation and testing
"""
__copyright__ = 'Copyright 2023'
__version__ = 4.0
__maintainer__ = "George Flanagin"
__email__ = ['gflanagin@richmond.edu', 'me@georgeflanagin.com']
__status__ = 'in progress'
__license__ = 'MIT'

###########################################################################

"""
A universal Python parser combinator library inspired by Parsec library of Haskell.
"""

min_py = (3, 8)

###
# Standard imports, starting with os and sys
###
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

###
# Other standard distro imports
###
from   collections import namedtuple
from   collections.abc import Callable
from   collections.abc import Iterable
import datetime
from   functools import wraps
import re
import string
import warnings

##########################################################################
# SECTION 0: Constants
##########################################################################

TAB     = '\t'
CR      = '\r'
NL      = '\n'
LF      = '\n'
VTAB    = '\f'
BSPACE  = '\b'
QUOTE1  = "'"
QUOTE2  = '"'
QUOTE3  = "`"
LBRACE  = '{'
RBRACE  = '}'
LBRACK  = '['
RBRACK  = ']'
COLON   = ':'
COMMA   = ','
SEMICOLON   = ';'
BACKSLASH   = '\\'
UNDERSCORE  = '_'
OCTOTHORPE  = '#'
CIRCUMFLEX  = '^'
EMPTY_STR   = ""


SLASH   = '/'
PLUS    = '+'
MINUS   = '-'
STAR    = '*'    
EQUAL   = '='
DOLLAR  = '$'
AT_SIGN = '@'
BANG    = '!'
PERCENT = '%'


##########################################################################
# SECTION 1: Parsec.Error
##########################################################################
class ParseError(RuntimeError):
    """
    This exception is raised at the first unrecoverable syntax error.
    """

    def __init__(self, expected:str, text:str, index:tuple):
        """
        expected -- the text that should be present.
        text     -- the text that was found.
        index    -- where in the current text shred the error is located.
        """
        self.expected = expected
        self.text = text
        self.index = index


    @staticmethod
    def loc_info(text:object, index:int) -> tuple:
        '''
        Location of `index` in source code `text`.
        '''
        if index > len(text):
            raise ValueError('Invalid index.')
        if isinstance(text, str):
            line, last_ln = text.count('\n', 0, index), text.rfind('\n', 0, index)
        else:
            line, last_ln = 0, index
        col = index - (last_ln + 1)
        return (line, col)


    def loc(self) -> int:
        '''
        Locate the error position in the source code text.
        '''

        try:
            return '{}'.format(*ParseError.loc_info(self.text, self.index))
        except ValueError:
            return f'<out of bounds index {self.index}>'


    def __str__(self) -> str:
        """
        This function allows us to meaningfully print the exception.
        """
        return f'expected: {self.expected} at {self.loc}'


##########################################################################
# SECTION 2: Definition the Value model.
##########################################################################
class Value: pass
class Value(namedtuple('Value', 'status index value expected')):
    """
    Value represents the result of the Parser. namedtuple is a little bit of 
    difficult beast, adding as much syntactic complexity as it removes.

    Here the types are:
        status   -- bool
        index    -- int
        value    -- object
        expected -- str

    """

    @staticmethod
    def success(index:int, actual:object) -> Value:
        """
        Factory to create success Value.
        """
        return Value(True, index, actual, None)


    @staticmethod
    def failure(index:int, expected:object) -> Value:
        """
        Factory to create failure Value.
        """
        return Value(False, index, None, expected)


    def aggregate(self, other:Value=None) -> Value:
        '''
        Collect the furthest failure from self and other.
        '''
        if not self.status: return self
        if not other: return self
        if not other.status: return other
        return Value(True, other.index, self.value + other.value, None)


    def update_index(self, index:int=None) -> Value:
        """
        Change the index, and return a new object.
        """
        return ( self 
            if index is None else 
                Value(self.status, index, self.value, self.expected)
                )


    @staticmethod
    def combinate(values:Iterable) -> Value:
        '''
        TODO: rework this one.
        Aggregate multiple values into tuple
        '''
        prev_v = None
        for v in values:
            if prev_v:
                if not v:
                    return prev_v
            if not v.status:
                return v
        out_values = tuple(v.value for v in values)
        return Value(True, values[-1].index, out_values, None)


    def __bool__(self) -> bool:
        """
        This function allows for checking the status with an "if" before
        the Value object. Merely syntax sugar for neater code.
        """
        return bool(self.status)


    def __str__(self) -> str:
        """
        To allow for well-behaved printing.
        """
        return f'Value: {self.status=}, {self.index=}, {self.value=}, {self.expected=}'


##########################################################################
# SECTION 3: The Parser decorator.
##########################################################################

class Parser: pass
class Parser:
    '''
    A Parser is an object that wraps a function to do the parsing work.
    Arguments of the function should be a string to be parsed and the index on
    which to begin parsing. Parser is intended to be used as a decorator.

    The function should return either Value.success(next_index, value) if
    parsing successfully, or Value.failure(index, expected) on the failure.
    '''

    def __init__(self, fn:Callable):
        '''
        fn -- is the function to wrap. 
        '''
        self.fn = fn


    def __call__(self, text:str, index:int) -> Value:
        '''
        call wrapped function.
        '''
        return self.fn(text, index)


    def parse(self, text:str):
        '''
        text -- the text to be parsed.
        '''
        return self.parse_partial(text)[0]


    def parse_partial(self, text:str) -> tuple:
        '''
        Parse the longest possible prefix of a given string.

        Return a tuple of the result value and the rest of the string.

        If failed, raise a ParseError. 
        '''
        result = self(text, 0)
        if result.status:
            return result.value, text[result.index:]

        raise ParseError(result.expected, text, result.index)


    def parse_strict(self, text:str) -> Value:
        '''
        Parse the longest possible prefix of the entire given string. If the 
        parser worked successfully and NONE text was rested, return the
        result value, else raise a ParseError.

        The difference between `parse` and `parse_strict` is that the entire
        given text must be used for the event to be construed as a success.
        '''

        # Note that < is not the gt operator, but the unconsumed end
        # parser of the text shred.
        return (self < eof()).parse_partial(text)[0]


    def bind(self, fn:Callable) -> Parser:
        '''
        This is the monadic binding operation. Returns a parser which, if
        parser is successful, passes the result to fn, and continues with the
        parser returned from fn. 
        '''

        @Parser
        def bind_parser(text:str, index:int):
            result = self(text, index)
            return result if not result.status else fn(result.value)(text, result.index)

        return bind_parser


    def compose(self, other:Parser):
        '''
        (>>) Sequentially compose two actions, discarding any value produced
        by the first.
        '''

        @Parser
        def compose_parser(text:str, index:int):
            result = self(text, index)
            return result if not result.status else other(text, result.index)
        return compose_parser


    def joint(self, *parsers:Iterable):
        '''
        (+) Joint two or more parsers into one. Return the aggregate of two results
        from this two parser.
        '''
        return joint(self, *parsers)


    def choice(self, other:Parser) -> Value:
        '''
        (|) This combinator implements choice. The parser p | q first applies p.

        - If it succeeds, the value of p is returned.
        - If p fails **without consuming any input**, parser q is tried.

        NOTICE: without backtrack.
        '''
        @Parser
        def choice_parser(text:str, index:int):
            result = self(text, index)
            return result if result.status or result.index != index else other(text, index)

        return choice_parser


    def try_choice(self, other:Parser) -> Value:
        '''
        (^) Choice with backtrack. This combinator is used whenever arbitrary
        look ahead is needed. The parser p ^ q first applies p, if it success,
        the value of p is returned. If p fails, it pretends that it hasn't consumed
        any input, and then parser q is tried.
        '''
        @Parser
        def try_choice_parser(text:str, index:int):
            result = self(text, index)
            return result if result.status else other(text, index)

        return try_choice_parser


    def skip(self, other:Parser) -> Value:
        '''
        (<<) Ends with a specified parser, discarding any result from
        the parser on the RHS. Typical uses might be discarding 
        whitespace that follows a parsed token:

        a_parser << whitespace_parser
        '''
        @Parser
        def skip_parser(text:str, index:int):
            res = self(text, index)
            if not res.status:
                return res
            end = other(text, res.index)
            if end.status:
                return Value.success(end.index, res.value)
            else:
                return Value.failure(end.index, f'ends with {end.expected}')

        return skip_parser


    def ends_with(self, other:Parser) -> Value:
        '''
        (<) Ends with a specified parser, and at the end parser hasn't consumed
        any input. Typical use is with EOF, or similar.
        '''
        @Parser
        def ends_with_parser(text:str, index:int):
            res = self(text, index)
            if not res.status:
                return res
            end = other(text, res.index)
            if end.status:
                return res
            else:
                return Value.failure(end.index, f'ends with {end.expected}')

        return ends_with_parser


    def excepts(self, other:Parser) -> Parser:
        '''
        (/) In other parser libraries, this is sometimes called the notFollowedBy
        parser. In the expression p / q, p is considered to be successful only if
        p succeeds, and q fails.
        '''
        @Parser
        def excepts_parser(text, index):
            res = self(text, index)
            if not res.status:
                return res
            lookahead = other(text, res.index)
            if lookahead.status:
                return Value.failure(res.index, f'should not be "{lookahead.value}"')
            else:
                return res

        return excepts_parser


    def parsecmap(self, fn:Callable) -> Parser:
        '''
        Returns a parser that transforms the result of the current parsing
        operation by invoking fn on the result. For example, if you wanted
        to transform the result from a text shred to an int, you would
        call xxxxxx.parsecmap(int). Note the *two* lambda functions.
        '''
        return self.bind(
            lambda result: Parser(
                lambda _, index: Value.success(index, fn(result))
                )
            )


    def parsecapp(self, other:Parser) -> Parser:
        '''
        Returns a parser that applies the produced value of this parser 
        to the produced value of `other`.
        '''
        return self.bind(
            lambda res: other.parsecmap(
                lambda x: res(x)
                )
            )


    def result(self, result:Value) -> Value:
        '''
        Return a value according to the parameter res when parse successfully.
        '''
        return self >> Parser(lambda _, index: Value.success(index, result))


    def mark(self):
        '''
        Mark the line and column information of the result of this parser.
        '''
        def pos(text:str, index:int):
            return ParseError.loc_info(text, index)

        @Parser
        def mark_parser(text:str, index:int):
            res = self(text, index)
            return ( Value.success(res.index, (pos(text, index), res.value, pos(text, res.index)))
                if res.status else res )

        return mark_parser


    def desc(self, description):
        '''
        Describe a parser, when it failed, print out the description text.
        '''
        return self | Parser(lambda _, index: Value.failure(index, description))


    ###
    # SECTION 3A: This section assigns function names to the overloaded operators.
    ###
    def __or__(self, other:Parser):
        '''Implements the `(|)` operator, means `choice`.'''
        return self.choice(other)

    def __xor__(self, other:Parser):
        '''Implements the `(^)` operator, means `try_choice`.'''
        return self.try_choice(other)

    def __add__(self, other:Parser):
        '''Implements the `(+)` operator, means `joint`.'''
        return self.joint(other)

    def __rshift__(self, other:Parser):
        '''Implements the `(>>)` operator, means `compose`.'''
        return self.compose(other)

    def __gt__(self, other:Parser):
        '''Implements the `(>)` operator, means `compose`.'''
        return self.compose(other)

    def __irshift__(self, other:Parser):
        '''Implements the `(>>=)` operator, means `bind`.'''
        warnings.warn("Operator >>= is deprecated. Use >= instead.",
            category=DeprecationWarning)
        return self.bind(other)

    def __ge__(self, other:Parser):
        '''Implements the `(>=)` operator, means `bind`.'''
        return self.bind(other)

    def __lshift__(self, other:Parser):
        '''Implements the `(<<)` operator, means `skip`.'''
        return self.skip(other)

    def __lt__(self, other:Parser):
        '''Implements the `(<)` operator, means `ends_with`.'''
        return self.ends_with(other)

    def __truediv__(self, other:Parser):
        '''Implements the `(/)` operator, means `excepts`.'''
        return self.excepts(other)


###
# SECTION 4: In this section, along with parse(), we have some of 
# the class member functions exposed to the outside primarily for 
# notational flexibility.
##

def bind(p, fn:Callable) -> Parser:
    '''
    Bind two parsers, implements the operator of `(>=)`.
    '''
    return p.bind(fn)


def choice(pa:Parser, pb:Parser):
    '''
    Choice one from two parsers, implements the operator of `(|)`.
    '''
    return pa.choice(pb)


def compose(pa:Parser, pb:Parser) -> Parser:
    '''
    Compose two parsers, implements the operator of `(>>)`, or `(>)`.
    '''
    return pa.compose(pb)


def desc(p, description):
    '''
    Describe a parser, when it failed, print out the description text.
    '''
    return p.desc(description)


def ends_with(pa, pb):
    '''
    Ends with a specified parser, and at the end parser hasn't consumed any input.
    Implements the operator of `(<)`.
    '''
    return pa.ends_with(pb)


def excepts(pa, pb):
    '''
    Fail `pa` though matched when the consecutive parser `pb` success for the rest text.
    '''
    return pa.excepts(pb)


def joint(*parsers):
    '''
    Joint two or more parsers, implements the operator of `(+)`.
    '''
    @Parser
    def joint_parser(text:str, index:int):
        values = []
        prev_v = None
        for p in parsers:
            if prev_v:
                index = prev_v.index
            prev_v = v = p(text, index)
            if not v.status:
                return v
            values.append(v)
        return Value.combinate(values)
    return joint_parser


def mark(p:Parser):
    '''
    Mark the line and column information of the result of the parser `p`.
    '''
    return p.mark()


def parse(p:Parser, text:str, index:int=0) -> Value:
    '''
    Parse a string and return the result or raise a ParseError.
    '''
    return p.parse(text[index:])


def parsecapp(p:Parser, other:Parser) -> Parser:
    '''
    Returns a parser that applies the produced value of this parser to the produced
    value of `other`.

    There should be an operator `(<*>)`, but that is impossible in Python.
    '''
    return p.parsecapp(other)


def parsecmap(p:Parser, fn:Callable) -> Parser:
    '''
    Returns a parser that transforms the produced value of parser with `fn`.
    '''
    return p.parsecmap(fn)


def result(p:Parser, res:Value) -> Value:
    '''
    Return a value according to the parameter `res` when parse successfully.
    '''
    return p.result(res)


def skip(pa:Parser, pb:Parser) -> Parser:
    '''
    Ends with a specified parser, and at the end parser consumed the end flag.
    Implements the operator of `(<<)`.
    '''
    return pa.skip(pb)


def try_choice(pa:Parser, pb:Parser) -> Parser:
    '''
    Choice one from two parsers with backtrack, implements the operator of `(^)`.
    '''
    return pa.try_choice(pb)


##########################################################################
# SECTION 5: The Parser Factory.
#
# The most powerful way to construct a parser is to use the @generate decorator.
# @generate creates a parser from a generator that should yield parsers.
# These parsers are applied successively and their results are sent back to the
# generator using `.send()` protocol. The generator should return the result or
# another parser, which is equivalent to applying it and returning its result.
#
# For an explanation of the .send() protocol, see the text in section 6.2.9.1
# of the official Python documentation.
# 
#     https://docs.python.org/3/reference/expressions.html
##########################################################################

def generate(fn:Callable) -> Parser:
    '''
    Parser generator. (combinator syntax).
    '''
    if isinstance(fn, str):
        return lambda f: generate(f).desc(fn)

    @wraps(fn)
    @Parser
    def generated(text:str, index:int) -> Value:

        iterator, value = fn(), None
        try:
            while True:
                parser = iterator.send(value)
                res = parser(text, index)
                if not res.status:  # this parser failed.
                    return res
                value, index = res.value, res.index  # iterate

        except StopIteration as stop:
            ###
            # This is the successful termination of the parser.
            # Note that we catch anything *derived* from StopIteration.
            ###
            endval = stop.value
            if isinstance(endval, Parser):
                return endval(text, index)
            else:
                return Value.success(index, endval)

        except RuntimeError as error:
            ###
            # This is the real error.
            ###
            stop = error.__cause__
            endval = stop.value
            if isinstance(endval, Parser):
                return endval(text, index)
            else:
                return Value.success(index, endval)

    return generated.desc(fn.__name__)


##########################################################################
# SECTION 6: Repeaters.
##########################################################################
def times(p:Parser, min_times:int, max_times:int=0) -> list:
    '''
    Repeat a parser between min_times and max_times
    Execute it, and return a list containing whatever
    was collected. 
    '''
    
    max_times = min_times if not max_times else max_times
    @Parser
    def times_parser(text:str, index:int) -> Parser:
        
        cnt, values, res = 0, [], None
        while cnt < max_times:
            res = p(text, index)
            if res.status:
                if max_times == sys.maxsize and res.index == index:
                    break

                values.append(res.value)
                index, cnt = res.index, cnt + 1
            else:
                if cnt >= min_times:
                    break
                else:
                    return res  # failed, throw exception.
            if cnt >= max_times:  # finish.
                break
            ###
            # If we don't have any remaining text to start next loop, we need break.
            #
            # We cannot put the `index < len(text)` in where because some parser can
            # success even when we have no any text. We also need to detect if the
            # parser consume no text.
            ###
            if index >= len(text):
                if cnt >= min_times:
                    break  # we already have decent result to return
                else:
                    r = p(text, index)
                    if index != r.index:  # report error when the parser cannot success with no text
                        return Value.failure(index, "already at the end; no more input")
        return Value.success(index, values)

    return times_parser


def count(p:Parser, n:int) -> list:
    '''
    `count p n` parses n occurrences of p. If n is smaller or equal to zero,
    the parser equals to return []. Returns a list of n values returned by p.
    '''
    return times(p, n, n)


def optional(p:Parser, default_value=None):
    '''
    Make a parser as optional. If success, return the result, otherwise return
    default_value silently, without raising any exception. If default_value is not
    provided None is returned instead.
    '''

    @Parser
    def optional_parser(text:str, index:int) -> Value:
        res = p(text, index)
        if res.status:
            return Value.success(res.index, res.value)
        else:
            # Return the maybe existing default value without doing anything.
            return Value.success(index, default_value)

    return optional_parser


def many(p) -> list:
    '''
    Repeat a parser 0 to infinity times. Return a list of the values
    collected. This function is just a convenience, as it calls times.
    '''
    return times(p, 0, sys.maxsize)


def many1(p:Parser) -> list:
    '''
    Repeat a parser 1 to infinity times. Return a list of the values
    collected. This function is just a convenience, as it calls times.
    Note that it does error out if p fails to execute at least once.
    '''
    return times(p, 1, sys.maxsize)

###
# NOTE: the following parsers are useful for expressions in 
# a language that appear like this: a, b, c, d
# Most languages have these.
###
def separated(p:Parser, sep:str, min_times:int, max_times:int=0, end=None) -> list:
    '''
    Repeat a parser `p` separated by `s` between `min_times` and `max_times` times.
    If max_times is omitted, max_times becomes min_times, effectively
    executing `p` exactly min_times.

    - When `end` is None, a trailing separator is optional (default).
    - When `end` is True, a trailing separator is required.
    - When `end` is False, a trailing separator will not be parsed.

    This algorithm is greedy, and does not give back; i.e., it is like the
    splat (*) in regular expressions.

    Return list of values returned by `p`.
    '''
    max_times = min_times if not max_times else max_times

    @Parser
    def sep_parser(text, index):
        cnt, values_index, values, res = 0, index, [], None
        while cnt < max_times:
            res = p(text, index)
            if res.status:
                current_value_index = res.index
                current_value = res.value
                index, cnt = res.index, cnt + 1
            else:
                if cnt < min_times:
                    return res  # error: need more elements, but no `p` found.
                else:
                    return Value.success(values_index, values)

            # consume the sep
            res = sep(text, index)
            if res.status:  # `sep` found, consume it (advance index)
                index = res.index
                if end in [True, None]:
                    current_value_index = res.index
            else:
                if cnt < min_times or (cnt == min_times and end is True):
                    return res  # error: need more elements, but no `sep` found.
                else:
                    if end is True:
                        # step back
                        return Value.success(values_index, values)
                    else:
                        values_index = current_value_index
                        values.append(current_value)
                        return Value.success(values_index, values)

            # record the new value
            values_index = current_value_index
            values.append(current_value)
        return Value.success(values_index, values)
    return sep_parser


def sepBy(p:Parser, sep:str) -> list:
    '''
    `sepBy(p, sep)` parses zero or more occurrences of p, separated by `sep`.
    Returns a list of values returned by `p`.
    '''
    return separated(p, sep, 0, max_times=sys.maxsize, end=False)


def sepBy1(p:Parser, sep:str) -> list:
    '''
    `sepBy1(p, sep)` parses one or more occurrences of `p`, separated by
    `sep`. Returns a list of values returned by `p`.
    '''
    return separated(p, sep, 1, max_times=sys.maxsize, end=False)


def endBy(p:Parser, sep:str) -> list:
    '''
    `endBy(p, sep)` parses zero or more occurrences of `p`, separated and
    ended by `sep`. Returns a list of values returned by `p`.
    '''
    return separated(p, sep, 0, max_times=sys.maxsize, end=True)


def endBy1(p:Parser, sep:str) -> list:
    '''
    `endBy1(p, sep) parses one or more occurrences of `p`, separated and
    ended by `sep`. Returns a list of values returned by `p`.
    '''
    return separated(p, sep, 1, max_times=sys.maxsize, end=True)


def sepEndBy(p:Parser, sep:str) -> list:
    '''
    `sepEndBy(p, sep)` parses zero or more occurrences of `p`, separated and
    optionally ended by `sep`. Returns a list of
    values returned by `p`.
    '''
    return separated(p, sep, 0, max_times=sys.maxsize)


def sepEndBy1(p:Parser, sep:str) -> list:
    '''
    `sepEndBy1(p, sep)` parses one or more occurrences of `p`, separated and
    optionally ended by `sep`. Returns a list of values returned by `p`.
    '''
    return separated(p, sep, 1, max_times=sys.maxsize)


##########################################################################
# SECTION 7: Prebuilt parsers for common operations.
##########################################################################
def any_char() -> Parser:
    '''
    Note the change in name in this version. This function was named any(), but
    any is a Python built in.
    '''
    @Parser
    def any_parser(text:str, index=0) -> Parser:
        if index < len(text):
            return Value.success(index + 1, text[index])
        else:
            return Value.failure(index, 'a random char')

    return any_parser


def one_of(s:str) -> Parser:
    '''
    Parses a char from specified string.
    '''
    @Parser
    def one_of_parser(text:str, index=0) -> Parser:
        if index < len(text) and text[index] in s:
            return Value.success(index + 1, text[index])
        else:
            return Value.failure(index, f'one of {s}')

    return one_of_parser


def none_of(s) -> Parser:
    '''
    Parses a char NOT from specified string.
    '''
    @Parser
    def none_of_parser(text, index=0) -> Value:
        if index < len(text) and text[index] not in s:
            return Value.success(index + 1, text[index])
        else:
            return Value.failure(index, 'none of {}'.format(s))

    return none_of_parser


def space() -> Parser:
    '''
    Parses a whitespace character.
    '''
    @Parser
    def space_parser(text, index=0) -> Value:
        import string
        if index < len(text) and text[index] in string.whitespace:
            return Value.success(index + 1, text[index])
        else:
            return Value.failure(index, 'one space')

    return space_parser


def spaces() -> Parser:
    '''
    Parses zero or more whitespace characters.
    '''
    return many(space())


def letter() -> Parser:
    """
    Parse a character that Unicode understands to be a 
    Letter type, Lm, Lt, Lu, Ll, or Lo
    """
    @Parser
    def letter_parser(text:str, index:int=0) -> Parser:
        if index < len(text) and text[index].isalpha():
            return Value.success(index + 1, text[index])
        else:
            return Value.failure(index, 'a letter')

    return letter_parser


def ascii_letter() -> Parser:
    """
    Like letter, but restricted to 7-bit ASCII
    """

    @Parser
    def ascii_letter_parser(text:str, index:int=0) -> Parser:
        
        c = text.get(index)
        if c is not None and (c.islower() or c.isupper()):
            return Value.success(index + 1, text[index])
        else:
            return Value.failure(index, 'an ascii letter')

    return ascii_letter_parser


def digit() -> Parser:
    '''
    Parse a digit. 
    '''
    @Parser
    def digit_parser(text:str, index=0):
        import string
        if index < len(text) and text[index] in string.digits:
            return Value.success(index + 1, text[index])
        else:
            return Value.failure(index, 'a digit')

    return digit_parser


def eof() -> Parser:
    '''
    Parses EOF flag of a string.
    '''
    @Parser
    def eof_parser(text:str, index=0):
        if index >= len(text):
            return Value.success(index, None)
        else:
            return Value.failure(index, 'EOF')

    return eof_parser


def regex(exp:str, flags:int=0) -> Parser:
    '''
    Parses according to a regular expression.
    '''
    if isinstance(exp, str):
        exp = re.compile(exp, flags)

    @Parser
    def regex_parser(text:str, index:int) -> Parser:
        if not isinstance(text, str):
            return Value.failure(index, 
                "`regex` combinator only accepts string as input, " +
                f"but got type {type(text)}, value is {text}")

        match = exp.match(text, index)
        if match:
            return Value.success(match.end(), match.group(0))
        else:
            return Value.failure(index, exp.pattern)

    return regex_parser


###
# SECTION 7A: Regular expression parsers.
###
# A lot of nothing.
WHITESPACE  = regex(r'\s*', re.MULTILINE)

# And the most common parser of them all, written here in a form
# that is suitable for a decorator.
lexeme      = lambda p: p << WHITESPACE

# Either "0" or something that starts with a non-zero digit, and may
# have other digits following.
DIGIT_STR   = regex(r'(0|[1-9][\d]*)')
digit_str   = lexeme(DIGIT_STR)

# HEX numbers are allowed to start with zero.
HEX_STR     = regex(r'0[xX][0-9a-fA-F]+')
hex_str     = lexeme(HEX_STR)

# Spec for how a floating point number is written.
IEEE754     = regex(r'-?(0|[1-9][\d]*)([.][\d]+)?([eE][+-]?[\d]+)?')
ieee754     = lexeme(IEEE754)

# IP address
IPv4_ADDR   = regex(r'(?:(?:25[0-5]|2[0-4][\d]|[01]?[\d][\d]?)\.){3}(?:25[0-5]|2[0-4][\d]|[01]?[\d][\d]?)')
ipv4_addr   = lexeme(IPv4_ADDR)

# Something Python thinks is an integer.
PYINT       = regex(r'[-+]?[\d]+')
pyint       = lexeme(PYINT)

# HH:MM:SS in 24 hour format.
TIME        = regex(r'(?:[01]\d|2[0123]):(?:[012345]\d):(?:[012345]\d)')
time_parse  = lexeme(TIME)

# ISO Timestamp
TIMESTAMP   = regex(r'[\d]{1,4}\/[\d]{1,2}\/[\d]{1,2} [\d]{1,2}:[\d]{1,2}:[\d]{1,2}')
timestamp_parse   = lexeme(TIMESTAMP)

# US 10 digit phone number, w/ or w/o dashes and spaces embedded.
US_PHONE    = regex(r'[2-9][\d]{2}[ -]?[\d]{3}[ -]?[\d]{4}')
us_phone    = lexeme(US_PHONE)

###
# This is He Tao's original string parser. If the first n-characters of
# of the text matches and n < len(text), it advances the index by n *and*
# it returns a Value.failure. 
###
def string_parsec3(s):
    '''Parses a string.'''
    @Parser
    def string_parser(text, index=0):
        slen, tlen = len(s), len(text)
        expression = ''.join(text[index:index + slen]) == s
        if ''.join(text[index:index + slen]) == s:
            return Value.success(index + slen, s)
        else:
            matched = 0
            while matched < slen and index + matched < tlen and text[index + matched] == s[matched]:
                matched = matched + 1
            return Value.failure(index + matched, s)
    return string_parser


###
# This is my minor change to He Tao's code. If the first n-characters of
# the text matches and n < len(text), the index is unchanged in the
# Value.failure object that is returned.
###
def string_parsec4(s):
    '''Parses a string.'''
    @Parser
    def string_parser(text, index=0):
        slen, tlen = len(s), len(text)
        expression = ''.join(text[index:index + slen]) == s
        if ''.join(text[index:index + slen]) == s:
            return Value.success(index + slen, s)
        else:
            return Value.failure(index, s)

    return string_parser

###
# string is assigned to one or the other based on the environment
# variable, PARSEC3_STRING
###
string = string_parsec3 if os.environ.get('PARSEC3_STRING') == 1 else string_parsec4

##########################################################################
# SECTION 8: Special purpose parsers.
##########################################################################

def fail_with(message) -> Parser:
    """
    A trivial parser that always blows up.
    """
    return Parser(lambda _, index: Value.failure(index, message))


def fix(fn:Callable) -> Parser:
    '''
    Allow recursive parser using the Y combinator trick.

        Note that this version still yields the stack overflow 
        problem, and will be fixed in later version.

       See also: https://github.com/sighingnow/parsec.py/issues/39.
    '''
    return (lambda x: x(x))(lambda y: fn(lambda *args: y(y)(*args)))


def exclude(p: Parser, exclude:Parser) -> Parser:
    '''
    Fails parser p if parser `exclude` matches
    '''
    @Parser
    def exclude_parser(text:str, index:int) -> Value:
        res = exclude(text, index)
        if res.status:
            return Value.failure(index, 'something other than {}'.format(res.value))
        else:
            return p(text, index)

    return exclude_parser


def lookahead(p: Parser) -> Parser:
    '''
    Parses without consuming
    '''
    @Parser
    def lookahead_parser(text:str, index:int) -> Value:
        res = p(text, index)
        if res.status:
            return Value.success(index, res.value)
        else:
            return Value.failure(index, res.expected)
    return lookahead_parser


def unit(p: Parser) -> Parser:
    '''
    Converts a parser into a single unit. Only consumes input if 
    the parser succeeds
    '''
    @Parser
    def unit_parser(text:str, index:int):
        res = p(text, index)
        if res.status:
            return Value.success(res.index, res.value)
        else:
            return Value.failure(index, res.expected)

    return unit_parser


##########################################################################
# SECTION 9: Parsers built atop Python language elements.
##########################################################################
def integer() -> int:
    """
    Return a Python int, based on the commonsense def of a integer.
    """
    return lexeme(PYINT).parsecmap(int)


def number() -> float:
    """
    Return a Python float, based on the IEEE754 character representation.
    """
    return lexeme(IEEE754).parsecmap(float)


def time() -> datetime.time:
    """
    For 24 hour times.
    """
    return lexeme(TIME).parsecmap(datetime.time)


def timestamp() -> datetime.datetime:
    """
    Convert an ISO timestamp to a datetime.
    """
    return lexeme(TIMESTAMP).parsecmap(datetime.datetime.fromisoformat)

quote  = string(QUOTE2)

def charseq() -> str:
    """
    Returns a sequence of characters, resolving any escaped chars.
    """
    def string_part():
        return regex(r'[^"\\]+')

    def string_esc():
        global TAB, CR, LF, VTAB, BSPACE
        return string(BACKSLASH) >> (
            string(BACKSLASH)
            | string('/')
            | string('b').result(BSPACE)
            | string('f').result(VTAB)
            | string('n').result(LF)
            | string('r').result(CR)
            | string('t').result(TAB)
            | regex(r'u[0-9a-fA-F]{4}').parsecmap(lambda s: chr(int(s[1:], 16)))
            | quote
        )
    return string_part() | string_esc()


##########################################################################
# SECTION 10: Fine grain flow control.
##########################################################################


class EndOfGenerator(StopIteration):
    """
    An exception raised when parsing operations terminate. Iterators raise
    a StopIteration exception when they exhaust the input; this mod gives
    us something useful.
    """
    def __init__(self, value:Value):
        self.value = value


class EndOfParse(StopIteration):
    """
    As above, but this exception can be raised when we reach end of all parsing
    to signal the true "end" if we want/need to distinguish between them.
    """
    def __init__(self, value:Value):
        self.value = value


@lexeme
@generate
def quoted() -> str:
    yield quote
    body = yield many(charseq())
    yield quote
    raise EndOfGenerator(''.join(body))


@lexeme
@generate
def everything_else() -> str:
    body = yield many(charseq())
    raise EndOfGenerator(''.join(body))


def parser_from_strings(s:str, 
    cmap:Union[str, Callable]=None) -> Parser:
    """
    Factory for string parsers. NOTE that this function is not
        itself a Parser, but returns a Parser object joined 
        with the try-choice operator (^).

    s -- a whitespace delimited string of text.
    
    cmap -- an optional callable to be used as the argument to .parsecmap().
        If called with a str, the argument is accepted without comment or 
        checking. If it is a callable, an exception is raised if the 
        callable is nameless or has a name that cannot be determined 
        programmatically. 

        It is worth noting that the name of a callable such as str.lower
        is "lower" although the name of int is "int". In the first
        case, you would want to use "str.lower". 

    returns -- a Parser that tries all the strings non-destructively, and 
        vacuums up any trailing whitespace. The sub-parsers are tried 
        deterministically in the order in which they appear in the argument
        to the factory function. 

    NOTE: this factory will work with Parsec3 or Parsec4 strings.
    """

    if not isinstance(s, str): 
        raise ParserError(f"{s=} is not a str of whitespace delimited words.")

    if cmap is None:
        # print(" | ".join([ f"lexeme(string('{_}'))" for _ in s ]))
        return eval(" ^ ".join([ f"lexeme(string('{_}'))" for _ in s ]))

    if callable(cmap):
        try:
            cmap = cmap.__name__
        except Exception as e:
            raise Exception(f"Unable to get name of {cmap}")
    else:
        cmap = str(cmap)

    return eval(" ^ ".join([ f"lexeme(string('{_}').parsecmap({cmap}))" for _ in s ]))
        

