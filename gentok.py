import os, sys

cwd = os.getcwd() + "/"

settings = {}
discards = {}

def gen_token_header(tok_enum):
    token_extras = ""

    if "INCLUDE_EXTRAS" in settings:
        token_extras += "#include <string>\n"
        token_extras += "size_t get_token_column(const Token& token);\n"
        token_extras += "std::string get_token_text(const Token& token);\n"
        token_extras += "std::string get_token_type_name(TokenType type);\n"

    with open(cwd + "token.h", "w") as f:
        f.write("""
#ifndef _TOKEN_H_
#define _TOKEN_H_
    #include <vector>
    #include <cstddef>

    %s

    struct Token {
        TokenType type;
        const char* start;
        size_t length;
        const char* line_start;
        size_t line;
    };

    %s

    std::vector<Token> tokenize(const char* input);
#endif //_TOKEN_H_

        """ % (tok_enum, token_extras));

TOKEN_UNDEF_MODE = -1
TOKEN_TYPELIST_MODE = 0
TOKEN_DEFLIST_MODE = 1

def gen_token_extra_functions(token_types):
    token_extras = "size_t get_token_column(const Token& token) {\n"
    token_extras += "    return token.start - token.line_start;\n"
    token_extras += "}\n\n"
    token_extras += "std::string get_token_text(const Token& token) {\n"
    token_extras += "    return std::string(token.start, token.length);\n"
    token_extras += "}\n\n"
    token_extras += "std::string get_token_type_name(TokenType type) {\n"
    token_extras += "    switch(type) {\n"
    for token_type in token_types:
        token_extras += "        case TokenType::" + token_type + ": "
        token_extras += "            return \"" + token_type + "\";\n"
    token_extras += "        default: return \"UNDEFINED\";\n"
    token_extras += "    }\n"
    token_extras += "}\n\n"

    return token_extras

def gen_token_type_enum(token_types):
    enum = "enum class TokenType {\n"
    enum += "    " + "UNDEFINED" + ",\n"
    for token_type in token_types:
        enum += "    " + token_type + ",\n"
    enum += "    EOF\n"
    enum += "};\n"
    return enum

def emit_int(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    return "/* [ INT ] */\n    if(!(*input) || (*input < '0' || *input > '9')) { %s } %s " % (fail, postIncrement)

def emit_string(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    chunk  = "/* [ STRING ] */\n    if(!(*input) || *input != '\"') { %s } %s " % (fail, postIncrement)
    chunk += "    {\n"
    chunk += "    bool escaped = false;\n"
    chunk += "    while(*input && *input != '\"') { if(escaped) { escaped = false; ++input; } else if(*input == '\\\\') { escaped = true; } ++input; } if(!(*input) || *input != '\"') { %s } %s\n" % (fail, postIncrement);
    chunk += "    }\n"
    return chunk

def emit_whitespace(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    return "/* [ WHITESPACE ] */\n    if(!(*input) || (*input != ' ' && *input != '\\t' && *input != '\\r')) { %s } %s \n" % (fail, postIncrement)

def emit_newline(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    if invert:
        return "/* [ EOF LINE ] */\n    if((*input) && *input != '\\n') { %s } %s newline_counter++; last_newline = input; \n" % (fail, postIncrement)
    else:
        return "/* [ EOF LINE ] */\n    if(!(*input) || *input != '\\n') { %s } %s newline_counter++; last_newline = input; \n" % (fail, postIncrement)

def emit_eof(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    return "/* [ EOF ] */\n   if(*input) { %s } \n" % fail

def emit_word(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    return "/* [ WORD(A-Za-z0-9_) ] */\n    if(!(*input) || (!isalnum(*input) && *input != '_')) { %s } %s \n" % (fail, postIncrement)

def emit_any(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    return "/* [ ANY ]*/\n    if(!(*input)) { %s } %s \n" % (fail, postIncrement)

def emit_any_except(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    except_cond = token[len("@ANY_EXCEPT("):-1]

    r = "/* [ ANY_EXCEPT " + except_cond.strip().replace("*/", "* /") + " ] */\n    {"
    r += "\nconst char* idx = input; const char* ln = last_newline; size_t nl = newline_counter; \n"
    r += gen_rule(except_cond, "input++;\n" + fail, "++input;", True)
    r += "\ninput = idx; newline_counter = nl; last_newline = ln;\n break;\n"
    #r += "if(!(*input)) { input = idx;\n %s } %s \n" % (fail, postIncrement)
    r += "}"
    return r

def emit_any_of(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    token = token[len("@ANY_OF("):-1]
    
    if len(token) == 0:
        print("Invalid @ANY_OF rule, no options provided")
        sys.exit(1)

    ret = "/* [ ANY_OF " + token.strip().replace("*/", "* /") + " ] */\n    if(!(*input) || !("

    if token[0] == '"':
        token = token[1:-1]
    
    i = 0
    for c in token:
        ret += " *input == '%s' " % c
        if i < len(token) - 1:
            ret += " || "
        i += 1

    ret += ")) { %s } %s \n" % (fail, postIncrement)
    return ret

# REPEAT(RULE, UNITL)
def emit_repeat(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    otoken = token
    token = token[len("@REPEAT("):-1]
    params = token.split(",")
    
    if len(params) != 2:
        print("Invalid @REPEAT rule [%s], 2 parameters expected, found %d" % (otoken, len(params)))
        sys.exit(1)

    fail_code = gen_rule(params[1].strip(), "break;", postIncrement);

    ret = "/* [ REPEAT " + params[0].replace("*/", "* /") + " UNTIL " + params[1].replace("*/", "* /") + " ] */\n    do { if(!(*input)) { %s }\n" % fail
    
    gen_rule(params[0].strip(), fail_code)

    ret += " \n   } while(*input);\n"
    return ret

def emit_longest(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    token = token[len("@LONGEST("):-1]
    ret = "/* [ LONGEST " + token.replace("*/", "* /") + " ] */\n    do {\n"

    ret += "        if(!(*input)) { %s }\n" % fail
    ret += gen_rule(token.strip(), "continue;" if token.startswith("@ANY_EXCEPT") else "break;")

    ret += "\n    } while(*input);\n"
    return ret

def emit_discard(token, fail = "return 0;", postIncrement = "++input;", invert = False):    
    token = token[len("@DISCARD("):-1]

    comma = token.find(",")
    if comma == -1:
        print("Invalid @DISCARD rule [%s], 2 parameters expected, found %d" % (token, comma))
        sys.exit(1)

    name = token[0:comma].strip()
    token = token[comma+1:].strip()

    discards[name] = True

    return "/* [ DISCARD " + name + " ] */\n" + gen_rule(token.strip(), fail)

def emit_optional(token, fail = "return 0;", postIncrement = "++input;", invert = False):
    token = token[len("@OPTIONAL("):-1]
    return "/* [ OPTIONAL " + token.strip().replace("*/", "* /") + " ] */\n" + gen_rule(token.strip(), "\n/* Do nothing if optional does not appear */\n", "else { input++; }")


def gen_rule_fun(token_type, rule):
    r = "static size_t try_%s(const char* input, Token& token) {\n" % token_type
    r += "    const char* input_start = input;\n"
    r += gen_rule(rule)

    r += "\n    return input - input_start;\n"
    r += "}\n\n"
    return r


def fix_tokens(tokens):
    new_tokens = []
    accum = None
    mode = ""
    for token in tokens:
        token = token.strip()
        if len(token) == 0:
            if accum is not None:
                accum += " "
            continue
        if not accum:
            if token.count("(") > token.count(")"):
                accum = token + " "
                mode = ")"
                continue
            elif token[0] == '"':
                if token[len(token)-1] == '"':
                    new_tokens.append(token)
                    continue

                accum = token + " "
                mode = '"'
                continue
            else:
                new_tokens.append(token)
                continue
        else:
            if token[len(token)-1] == mode:
                accum += token

                if mode == ")" and accum.count("(") != accum.count(")"):
                    accum += " "
                    continue

                new_tokens.append(accum)
                accum = None
                continue
            else:
                accum += token + " "
                continue
    if accum:
        new_tokens.append(accum)
    return new_tokens

"""
    RULES:

    @INT
    @STRING

    @HORIZONTAL_WHITESPACE
    @NEWLINE
    @EOF
    @ANY
    @ANY_EXCEPT
    @REPEAT
    @WORD
    @LONGEST
    @DISCARD 
    EXAMPLE:
    Integer = @INT
    Float = @FLOAT

    Label = @IDENTIFIER :
    Identifier = @IDENTIFIER

    SingleLineComment = "//" @REPEAT[@ANY,@EOF]
    MultiLineComment = "/*" @REPEAT[@ANY, "*/"]
"""
def gen_rule(rule, fail = "return 0;", postIncrement = "++input;", invert = False):
    ret = ""
    tokens = rule.split(" ")

    rules = {
        "@INT": emit_int,
        "@STRING": emit_string,
        "@HORIZONTAL_WHITESPACE": emit_whitespace,
        "@NEWLINE": emit_newline,
        "@EOF": emit_eof,
        "@WORD": emit_word,
        "@ANY": emit_any,
        "@ANY_EXCEPT": emit_any_except,
        "@ANY_OF": emit_any_of,
        "@REPEAT": emit_repeat,
        "@LONGEST": emit_longest,
        "@DISCARD": emit_discard,
        "@OPTIONAL": emit_optional,
    }

    tokens = fix_tokens(tokens)

    for token in tokens:
        token = token.strip()
        if len(token) == 0:
            continue
        if token[0] == "\"" and token[len(token)-1] == "\"":
            for c in token[1:-1]:
                which = c
                if c == '\\':
                    which = "\\\\"
                elif c == "'":
                    which = "\\'"

                _input = "*input"
                _postIncrement = postIncrement
                if postIncrement == "++input;":
                    _input = "*(input++)"
                    _postIncrement = ""

                if "REDUCE_SIZE" in settings and fail.count("\n") == 0:
                    ret += "if (%s != '%s') %s %s \n" % (_input, which, fail, _postIncrement)
                else:
                    ret += "    if (%s != '%s') { %s } %s \n" % (_input, which, fail, _postIncrement)
        elif token[0] == "@":
            _rk = token.split("(")[0]
            if _rk in rules:
                ret += rules[_rk](token, fail, postIncrement, invert)
            else:
                print("Unknown rule [[ %s ]] on line %d" % (token, current_line))
                sys.exit(1)
        elif token == "''":
            ret += "    if(*input != '\"') { %s } %s \n" % (fail, postIncrement)
        else:
            print("Unknown rule [[ %s ]] on line %d" % (token, current_line))
            sys.exit(1)
    return ret

current_line = 1
current_rule = ""

def gen_case(token_type, rule):
    r = " if((len = try_%s(input, token)) > 0) {\n" % token_type

    if token_type in discards:
        r += "input += len;\n"
        r += "line += newline_counter;\nnewline_counter = 0;\n"
        r += "        continue;\n"
    else:
        if "REDUCE_SIZE" in settings:
            r += " add_token(TokenType::%s);\n continue;\n" % token_type
        else:
            r += "        token.type = TokenType::%s;\n" % token_type
            r += "        token.start = input;\n"
            r += "        token.length = len;\n"
            r += "        input += len;\n"
            r += "        token.line_start = last_newline;\n"
            r += "        token.line = line;\n"
            r += "        line += newline_counter;\nnewline_counter = 0;\n"
            r += "        tokens.push_back(token);\n"
            r += "        continue;\n"
    r += "    }\n"
    return r


def gen_token_source(token_types, token_defs):
    cpp_body = "#include \"token.h\"\n"

    if "USE_EXCEPTION" in settings:
        cpp_body += "#include <stdexcept>\n"
    if "USE_STDERR" in settings:
        cpp_body += "#include <iostream>\n"
    

    cpp_body += "\nstatic size_t newline_counter = 0;\n"
    cpp_body += "\nstatic const char* last_newline = NULL;\n"

    for token_type in token_types:
        cpp_body += gen_rule_fun(token_type, token_defs[token_type])
    
    cpp_body += "std::vector<Token> tokenize(const char* input) {\n"
    cpp_body += "    std::vector<Token> tokens;\n"
    cpp_body += "    Token token;\n"
    cpp_body += "    const char* start = input;\n"
    cpp_body += "    last_newline = input;\n"
    cpp_body += "    size_t line = 1;\n"
    cpp_body += "    size_t len = 0;\n\n"

    if "REDUCE_SIZE" in settings:
        cpp_body += "auto add_token = [&](TokenType type){\n"
        cpp_body += "    token.type = type;\n"
        cpp_body += "    token.start = start;\n"
        cpp_body += "    token.length = len;\n"
        cpp_body += "    token.line_start = last_newline;\n"
        cpp_body += "    token.line = line;\n"
        cpp_body += "    tokens.push_back(token);\n"
        cpp_body += "    input += len;"
        cpp_body += "    line += newline_counter;\nnewline_counter = 0;\n"
        cpp_body += "};\n\n"

    cpp_body += "    while (*input) {\n"

    for token_type in token_types:
        cpp_body += gen_case(token_type, token_defs[token_type])

    if "USE_STDERR" in settings:
        cpp_body += "std::cerr << \"Unknown token on line \" << line << \" column \" << (size_t)(input - last_newline) << std::endl;\n"
        cpp_body += "for(const char* ch = last_newline; (*ch) && (*ch != '\\n'); ++ch) { std::cerr << *ch; } std::cerr << std::endl;\n"
        cpp_body += "for(const char* ch = last_newline; ch < input; ++ch) { std::cerr << \"~\"; }\nstd::cerr << \"^\" << std::endl;\n"
        cpp_body += "tokens.clear();\n"
    if "USE_EXCEPTION" in settings:
        cpp_body += "        throw std::runtime_error(\"Unknown token\");\n"
    
    cpp_body += "break;\n"

    cpp_body += "    }\n"
    cpp_body += "    return tokens;\n"
    cpp_body += "}\n"
    return cpp_body



def main(filename):
    with open(filename) as f:
        lines = f.readlines()

    mode = TOKEN_UNDEF_MODE

    token_types = []
    token_defs = {}

    current_line = 0
    for line in lines:
        current_line += 1
        line = line.strip()
        if len(line) == 0:
            continue
        
        if line[0] == "!":
            continue
        if line == "[tokens]":
            mode = TOKEN_TYPELIST_MODE
            print("Warning: [tokens] is deprecated, use [rules]")
            continue
        if line == "[rules]":
            mode = TOKEN_DEFLIST_MODE
            continue
        if line[0] == "#":
            settings[line[1:]] = True
            continue
        if mode == TOKEN_TYPELIST_MODE:
            if line in token_types:
                print("Duplicate token type [%s]" % line)
                sys.exit(1)
            token_types.append(line)
            continue
        if mode == TOKEN_DEFLIST_MODE:
            eq = line.find("=")
            rule = line[0:eq].strip()
            if rule in token_defs:
                print("Warning: Redefinition of rule [%s] on line %d" % (rule, current_line))
            else:
                token_types.append(rule)
            token_defs[rule] = line[eq+1:].strip()
            continue
    
    err = 0
    for token_type in token_types:
        if token_type not in token_defs:
            print("Missing definition for token type [%s]" % token_type)
            err += 1
    if err > 0:
        print("Please add %d missing definitions" % err)
        sys.exit(1)

    gen_token_header(gen_token_type_enum(token_types))

    cpp_body = gen_token_source(token_types, token_defs)

    if "INCLUDE_EXTRAS" in settings:
        cpp_body += gen_token_extra_functions(token_types)

    with open(cwd + "token.cpp", "w") as f:
        f.write(cpp_body)

    os.system("astyle token.cpp")
    os.system("astyle token.h")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: gentok.py <filename>")
        sys.exit(1)
    
    main(sys.argv[1])
