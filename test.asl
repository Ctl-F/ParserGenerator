#DEFINE THREE_OPERANDS({
    Operand dst;
    Operand a;
    Operand b;
})

[cpp]
enum class OpCode {
    Nop,
    Mov,
    Add,
    Sub,
    Mul,
    Div,
};

enum class ModifierMath {
    None,
    Add,
    Sub,
};

enum class OperandType {
    Register,
    Value,
};

enum class OperandModifier {
    Dereference    = 0b00000001,
    Reference      = 0b00000010,
    StaticOffset   = 0b00000100,
    RegisterOffset = 0b00001000
};

[ast]

AstNode

Value: AstNode { 
    Token val;
}

Register: AstNode {
    Token val;
}

TypeDirective: AstNode {
    Token type;
}

Operand : AstNode {
    OperandType type;
    OperandModifier modifier;
    ModifierMath math;
    Token type_specifier;
    AstNode* main_operand;
    AstNode* modifier_operand;
}

Label: AstNode {
    Token name;
}

Instruction: AstNode {
    Token operand;
    OpCode code;
}

NopInst : Instruction

MovInst : Instruction {
    Register dst;
    Register src;
}

AddInst : Instruction $THREE_OPERANDS
SubInst : Instruction $THREE_OPERANDS
MulInst : Instruction $THREE_OPERANDS
DivInst : Instruction $THREE_OPERANDS

[rules]
#START_RULE program

Value = @ANY_TOK(LiteralExtChar,LiteralChar,LiteralFloat,LiteralInteger,LiteralBinary,True,False,Identifier):valueToken
<Value*> {
    Value vnode;
    vnode.val = valueToken;
    return vnode;
}

Register = @ANY_TOK(AR,LR,SB,SH,GReg):regToken
<Register*> {
    Register *reg = new Register();
    reg->val = regToken;
    return reg;
}

Operand = @MATCH(
    @CASE(
        @OPTIONAL([TypeDirective]:type) LeftBracket [Value]:val RightBracket 
        <Operand*> {
            Operand *oper = new Operand();
            oper->type = OperandType::Value;
            oper->math = ModifierMath::None;
            oper->type_specificer.type = TokenType::UNDEFINED;
            oper->main_operand = val;
            oper->modifier_operand = offset;

            return oper;
        }
    )
    @CASE(
        LeftBracket [Value]:val @ANY_TOK(Add,Sub):oper Identifier:label
    )
)

