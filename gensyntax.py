import os, sys

cwd = os.getcwd() + "/"

settings = {}

UNDEFINED_MODE = -1
INLINE_CPP_MODE = 0
AST_MODE = 1
RULE_MODE = 2

def main(filename):
    with open(filename) as f:
        lines = f.readlines()
    
    mode = UNDEFINED_MODE

    for line in lines:
        line = line.strip()
        if len(line) == 0:
            continue
        if line[0] == "!":
            continue
        if line == "[cpp]":
            mode = INLINE_CPP_MODE
            continue
        if line == "[ast]":
            mode = AST_MODE
            continue
        if line == "[rules]":
            mode = RULE_MODE
            continue
        if line[0] == "#":
            settings[line[1:]] = True
            continue

        if mode == INLINE_CPP_MODE:
            print(line)
        if mode == AST_MODE:
            print(line)
            continue
        if mode == RULE_MODE:
            print(line)
            continue

        

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: gensyntax.py <filename>")
        sys.exit(1)
    main(sys.argv[1])