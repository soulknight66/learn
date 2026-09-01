unit compiler;

{$mode objfpc}{$H+}

interface

uses
  mica_types;

function CompileTokens(const Tokens: TTokenArray): TCompiledProgram;

implementation

uses
  SysUtils;

type
  TStringArray = array of string;

  TMicaCompiler = class
  private
    FTokens: TTokenArray;
    FCurrent: Integer;
    FCode: TInstructionArray;
    FNames: TStringArray;
    function CurrentToken: TToken;
    function PreviousToken: TToken;
    function Check(Kind: TTokenKind): Boolean;
    function Advance: TToken;
    function Match(Kind: TTokenKind): Boolean;
    function Consume(Kind: TTokenKind; const MessageText: string): TToken;
    procedure ParseErrorAt(const Token: TToken; const MessageText: string);
    procedure CompileErrorAt(const Token: TToken; const MessageText: string);
    function Emit(Op: TOpCode; Arg: Int64; const Token: TToken): Integer;
    procedure PatchJump(InstructionIndex: Integer);
    function DeclareName(const Token: TToken): Integer;
    function ResolveName(const Token: TToken): Integer;
    procedure CompileStatement;
    procedure CompileLet;
    procedure CompileAssignment;
    procedure CompilePrint;
    procedure CompileIf;
    procedure CompileWhile;
    procedure CompileHalt;
    procedure CompileBlock;
    procedure ParseExpression;
    procedure ParseEquality;
    procedure ParseComparison;
    procedure ParseTerm;
    procedure ParseFactor;
    procedure ParseUnary;
    procedure ParsePrimary;
  public
    constructor Create(const Tokens: TTokenArray);
    function Compile: TCompiledProgram;
  end;

constructor TMicaCompiler.Create(const Tokens: TTokenArray);
begin
  inherited Create;
  FTokens := Tokens;
  FCurrent := 0;
  SetLength(FCode, 0);
  SetLength(FNames, 0);
end;

function TMicaCompiler.CurrentToken: TToken;
begin
  Result := FTokens[FCurrent];
end;

function TMicaCompiler.PreviousToken: TToken;
begin
  Result := FTokens[FCurrent - 1];
end;

function TMicaCompiler.Check(Kind: TTokenKind): Boolean;
begin
  Result := FTokens[FCurrent].Kind = Kind;
end;

function TMicaCompiler.Advance: TToken;
begin
  Result := CurrentToken;
  if Result.Kind <> tkEOF then
    Inc(FCurrent);
end;

function TMicaCompiler.Match(Kind: TTokenKind): Boolean;
begin
  if not Check(Kind) then
    Exit(False);
  Advance;
  Result := True;
end;

function TMicaCompiler.Consume(Kind: TTokenKind;
  const MessageText: string): TToken;
begin
  if not Check(Kind) then
    ParseErrorAt(CurrentToken, MessageText);
  Result := Advance;
end;

procedure TMicaCompiler.ParseErrorAt(const Token: TToken;
  const MessageText: string);
begin
  raise EMicaError.CreateAt('parse', Token.Line, Token.Column, MessageText);
end;

procedure TMicaCompiler.CompileErrorAt(const Token: TToken;
  const MessageText: string);
begin
  raise EMicaError.CreateAt('compile', Token.Line, Token.Column, MessageText);
end;

function TMicaCompiler.Emit(Op: TOpCode; Arg: Int64;
  const Token: TToken): Integer;
begin
  Result := Length(FCode);
  SetLength(FCode, Result + 1);
  FCode[Result].Op := Op;
  FCode[Result].Arg := Arg;
  FCode[Result].Line := Token.Line;
  FCode[Result].Column := Token.Column;
end;

procedure TMicaCompiler.PatchJump(InstructionIndex: Integer);
begin
  if (InstructionIndex < 0) or (InstructionIndex >= Length(FCode)) then
    raise Exception.Create('internal compiler error: invalid patch index');
  FCode[InstructionIndex].Arg := Length(FCode);
end;

function TMicaCompiler.DeclareName(const Token: TToken): Integer;
var
  I: Integer;
begin
  for I := 0 to High(FNames) do
    if FNames[I] = Token.Lexeme then
      CompileErrorAt(Token, 'variable already declared: ' + Token.Lexeme);
  Result := Length(FNames);
  SetLength(FNames, Result + 1);
  FNames[Result] := Token.Lexeme;
end;

function TMicaCompiler.ResolveName(const Token: TToken): Integer;
var
  I: Integer;
begin
  for I := 0 to High(FNames) do
    if FNames[I] = Token.Lexeme then
      Exit(I);
  CompileErrorAt(Token, 'unknown variable: ' + Token.Lexeme);
  Result := -1;
end;

procedure TMicaCompiler.CompileLet;
var
  NameToken: TToken;
  Slot: Integer;
begin
  NameToken := Consume(tkIdentifier, 'expected a name after let');
  Consume(tkEqual, 'expected = after variable name');
  ParseExpression;
  Consume(tkSemicolon, 'expected ; after declaration');
  Slot := DeclareName(NameToken);
  Emit(opStore, Slot, NameToken);
end;

procedure TMicaCompiler.CompileAssignment;
var
  NameToken: TToken;
  Slot: Integer;
begin
  NameToken := Advance;
  Consume(tkEqual, 'expected = after assignment name');
  ParseExpression;
  Consume(tkSemicolon, 'expected ; after assignment');
  Slot := ResolveName(NameToken);
  Emit(opStore, Slot, NameToken);
end;

procedure TMicaCompiler.CompilePrint;
var
  PrintToken: TToken;
begin
  PrintToken := PreviousToken;
  ParseExpression;
  Consume(tkSemicolon, 'expected ; after printed expression');
  Emit(opPrint, 0, PrintToken);
end;

procedure TMicaCompiler.CompileBlock;
begin
  while (not Check(tkRightBrace)) and (not Check(tkEOF)) do
    CompileStatement;
  Consume(tkRightBrace, 'expected } after block');
end;

procedure TMicaCompiler.CompileIf;
var
  IfToken: TToken;
  ElseToken: TToken;
  FalseJump: Integer;
  EndJump: Integer;
begin
  IfToken := PreviousToken;
  ParseExpression;
  FalseJump := Emit(opJumpIfFalse, -1, IfToken);
  Consume(tkLeftBrace, 'expected { before if body');
  CompileBlock;

  if Match(tkElse) then
  begin
    ElseToken := PreviousToken;
    EndJump := Emit(opJump, -1, ElseToken);
    PatchJump(FalseJump);
    Consume(tkLeftBrace, 'expected { before else body');
    CompileBlock;
    PatchJump(EndJump);
  end
  else
    PatchJump(FalseJump);
end;

procedure TMicaCompiler.CompileWhile;
var
  WhileToken: TToken;
  LoopStart: Integer;
  ExitJump: Integer;
begin
  WhileToken := PreviousToken;
  LoopStart := Length(FCode);
  ParseExpression;
  ExitJump := Emit(opJumpIfFalse, -1, WhileToken);
  Consume(tkLeftBrace, 'expected { before while body');
  CompileBlock;
  Emit(opJump, LoopStart, WhileToken);
  PatchJump(ExitJump);
end;

procedure TMicaCompiler.CompileHalt;
var
  HaltToken: TToken;
begin
  HaltToken := PreviousToken;
  Consume(tkSemicolon, 'expected ; after halt');
  Emit(opHalt, 0, HaltToken);
end;

procedure TMicaCompiler.CompileStatement;
begin
  if Match(tkLet) then
    CompileLet
  else if Match(tkPrint) then
    CompilePrint
  else if Match(tkIf) then
    CompileIf
  else if Match(tkWhile) then
    CompileWhile
  else if Match(tkHalt) then
    CompileHalt
  else if Check(tkIdentifier) then
    CompileAssignment
  else
    ParseErrorAt(CurrentToken, 'expected a statement');
end;

procedure TMicaCompiler.ParseExpression;
begin
  ParseEquality;
end;

procedure TMicaCompiler.ParseEquality;
var
  OperatorToken: TToken;
begin
  ParseComparison;
  while FTokens[FCurrent].Kind in [tkEqualEqual, tkBangEqual] do
  begin
    OperatorToken := Advance;
    ParseComparison;
    if OperatorToken.Kind = tkEqualEqual then
      Emit(opEqual, 0, OperatorToken)
    else
      Emit(opNotEqual, 0, OperatorToken);
  end;
end;

procedure TMicaCompiler.ParseComparison;
var
  OperatorToken: TToken;
begin
  ParseTerm;
  while FTokens[FCurrent].Kind in [tkLess, tkLessEqual, tkGreater, tkGreaterEqual] do
  begin
    OperatorToken := Advance;
    ParseTerm;
    case OperatorToken.Kind of
      tkLess: Emit(opLess, 0, OperatorToken);
      tkLessEqual: Emit(opLessEqual, 0, OperatorToken);
      tkGreater: Emit(opGreater, 0, OperatorToken);
      tkGreaterEqual: Emit(opGreaterEqual, 0, OperatorToken);
    end;
  end;
end;

procedure TMicaCompiler.ParseTerm;
var
  OperatorToken: TToken;
begin
  ParseFactor;
  while FTokens[FCurrent].Kind in [tkPlus, tkMinus] do
  begin
    OperatorToken := Advance;
    ParseFactor;
    if OperatorToken.Kind = tkPlus then
      Emit(opAdd, 0, OperatorToken)
    else
      Emit(opSubtract, 0, OperatorToken);
  end;
end;

procedure TMicaCompiler.ParseFactor;
var
  OperatorToken: TToken;
begin
  ParseUnary;
  while FTokens[FCurrent].Kind in [tkStar, tkSlash, tkPercent] do
  begin
    OperatorToken := Advance;
    ParseUnary;
    case OperatorToken.Kind of
      tkStar: Emit(opMultiply, 0, OperatorToken);
      tkSlash: Emit(opDivide, 0, OperatorToken);
      tkPercent: Emit(opRemainder, 0, OperatorToken);
    end;
  end;
end;

procedure TMicaCompiler.ParseUnary;
var
  OperatorToken: TToken;
begin
  if FTokens[FCurrent].Kind in [tkBang, tkMinus] then
  begin
    OperatorToken := Advance;
    ParseUnary;
    if OperatorToken.Kind = tkBang then
      Emit(opNot, 0, OperatorToken)
    else
      Emit(opNegate, 0, OperatorToken);
  end
  else
    ParsePrimary;
end;

procedure TMicaCompiler.ParsePrimary;
var
  Token: TToken;
  Slot: Integer;
begin
  if Match(tkInteger) then
  begin
    Token := PreviousToken;
    Emit(opConst, Token.IntValue, Token);
  end
  else if Match(tkTrue) then
  begin
    Token := PreviousToken;
    Emit(opConst, 1, Token);
  end
  else if Match(tkFalse) then
  begin
    Token := PreviousToken;
    Emit(opConst, 0, Token);
  end
  else if Match(tkIdentifier) then
  begin
    Token := PreviousToken;
    Slot := ResolveName(Token);
    Emit(opLoad, Slot, Token);
  end
  else if Match(tkLeftParen) then
  begin
    ParseExpression;
    Consume(tkRightParen, 'expected ) after expression');
  end
  else
    ParseErrorAt(CurrentToken, 'expected an expression');
end;

function TMicaCompiler.Compile: TCompiledProgram;
var
  EndToken: TToken;
begin
  while not Check(tkEOF) do
    CompileStatement;
  EndToken := CurrentToken;
  Emit(opHalt, 0, EndToken);
  Result.Code := FCode;
  Result.VariableCount := Length(FNames);
end;

function CompileTokens(const Tokens: TTokenArray): TCompiledProgram;
var
  Parser: TMicaCompiler;
begin
  if Length(Tokens) = 0 then
    raise Exception.Create('internal compiler error: token stream has no EOF');
  Parser := TMicaCompiler.Create(Tokens);
  try
    Result := Parser.Compile;
  finally
    Parser.Free;
  end;
end;

end.
