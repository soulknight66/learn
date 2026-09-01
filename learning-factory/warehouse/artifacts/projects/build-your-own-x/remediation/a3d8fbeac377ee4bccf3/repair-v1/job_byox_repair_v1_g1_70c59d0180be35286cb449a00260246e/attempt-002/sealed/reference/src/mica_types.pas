unit mica_types;

{$mode objfpc}{$H+}

interface

uses
  SysUtils;

const
  MICA_MIN_VALUE = Int64(-1000000000);
  MICA_MAX_VALUE = Int64(1000000000);
  MICA_STEP_LIMIT = 100000;

type
  TTokenKind = (
    tkEOF, tkInteger, tkIdentifier,
    tkLet, tkPrint, tkIf, tkElse, tkWhile, tkHalt, tkTrue, tkFalse,
    tkLeftParen, tkRightParen, tkLeftBrace, tkRightBrace, tkSemicolon,
    tkEqual, tkPlus, tkMinus, tkStar, tkSlash, tkPercent, tkBang,
    tkEqualEqual, tkBangEqual, tkLess, tkLessEqual, tkGreater, tkGreaterEqual
  );

  TToken = record
    Kind: TTokenKind;
    Lexeme: string;
    IntValue: Int64;
    Line: Integer;
    Column: Integer;
  end;

  TTokenArray = array of TToken;

  TOpCode = (
    opConst, opLoad, opStore,
    opAdd, opSubtract, opMultiply, opDivide, opRemainder,
    opNegate, opNot,
    opEqual, opNotEqual, opLess, opLessEqual, opGreater, opGreaterEqual,
    opJump, opJumpIfFalse, opPrint, opHalt
  );

  TInstruction = record
    Op: TOpCode;
    Arg: Int64;
    Line: Integer;
    Column: Integer;
  end;

  TInstructionArray = array of TInstruction;

  TCompiledProgram = record
    Code: TInstructionArray;
    VariableCount: Integer;
  end;

  EMicaError = class(Exception)
  public
    Phase: string;
    SourceLine: Integer;
    SourceColumn: Integer;
    constructor CreateAt(const APhase: string; ALine, AColumn: Integer;
      const AMessage: string);
  end;

function TokenName(Kind: TTokenKind): string;
function OpName(Op: TOpCode): string;
function OpHasArgument(Op: TOpCode): Boolean;

implementation

constructor EMicaError.CreateAt(const APhase: string; ALine, AColumn: Integer;
  const AMessage: string);
begin
  inherited Create(AMessage);
  Phase := APhase;
  SourceLine := ALine;
  SourceColumn := AColumn;
end;

function TokenName(Kind: TTokenKind): string;
begin
  case Kind of
    tkEOF: Result := 'EOF';
    tkInteger: Result := 'INTEGER';
    tkIdentifier: Result := 'IDENTIFIER';
    tkLet: Result := 'LET';
    tkPrint: Result := 'PRINT';
    tkIf: Result := 'IF';
    tkElse: Result := 'ELSE';
    tkWhile: Result := 'WHILE';
    tkHalt: Result := 'HALT';
    tkTrue: Result := 'TRUE';
    tkFalse: Result := 'FALSE';
    tkLeftParen: Result := 'LEFT_PAREN';
    tkRightParen: Result := 'RIGHT_PAREN';
    tkLeftBrace: Result := 'LEFT_BRACE';
    tkRightBrace: Result := 'RIGHT_BRACE';
    tkSemicolon: Result := 'SEMICOLON';
    tkEqual: Result := 'EQUAL';
    tkPlus: Result := 'PLUS';
    tkMinus: Result := 'MINUS';
    tkStar: Result := 'STAR';
    tkSlash: Result := 'SLASH';
    tkPercent: Result := 'PERCENT';
    tkBang: Result := 'BANG';
    tkEqualEqual: Result := 'EQUAL_EQUAL';
    tkBangEqual: Result := 'BANG_EQUAL';
    tkLess: Result := 'LESS';
    tkLessEqual: Result := 'LESS_EQUAL';
    tkGreater: Result := 'GREATER';
    tkGreaterEqual: Result := 'GREATER_EQUAL';
  end;
end;

function OpName(Op: TOpCode): string;
begin
  case Op of
    opConst: Result := 'CONST';
    opLoad: Result := 'LOAD';
    opStore: Result := 'STORE';
    opAdd: Result := 'ADD';
    opSubtract: Result := 'SUB';
    opMultiply: Result := 'MUL';
    opDivide: Result := 'DIV';
    opRemainder: Result := 'MOD';
    opNegate: Result := 'NEG';
    opNot: Result := 'NOT';
    opEqual: Result := 'EQ';
    opNotEqual: Result := 'NE';
    opLess: Result := 'LT';
    opLessEqual: Result := 'LE';
    opGreater: Result := 'GT';
    opGreaterEqual: Result := 'GE';
    opJump: Result := 'JUMP';
    opJumpIfFalse: Result := 'JUMP_IF_FALSE';
    opPrint: Result := 'PRINT';
    opHalt: Result := 'HALT';
  end;
end;

function OpHasArgument(Op: TOpCode): Boolean;
begin
  Result := Op in [opConst, opLoad, opStore, opJump, opJumpIfFalse];
end;

end.
