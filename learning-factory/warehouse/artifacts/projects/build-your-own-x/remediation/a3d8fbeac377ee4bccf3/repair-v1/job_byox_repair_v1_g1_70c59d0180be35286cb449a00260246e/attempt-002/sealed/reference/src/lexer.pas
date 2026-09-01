unit lexer;

{$mode objfpc}{$H+}

interface

uses
  mica_types;

function Tokenize(const Source: string): TTokenArray;

implementation

uses
  SysUtils;

type
  TMicaLexer = class
  private
    FSource: string;
    FIndex: Integer;
    FLine: Integer;
    FColumn: Integer;
    FTokens: TTokenArray;
    function AtEnd: Boolean;
    function Peek: Char;
    function Advance: Char;
    function MatchChar(Expected: Char): Boolean;
    procedure SkipIgnored;
    procedure AddToken(Kind: TTokenKind; StartIndex, StartLine,
      StartColumn: Integer; Value: Int64);
    procedure ScanIdentifier(StartIndex, StartLine, StartColumn: Integer);
    procedure ScanInteger(StartIndex, StartLine, StartColumn: Integer);
    procedure ScanOne;
  public
    constructor Create(const Source: string);
    function ScanAll: TTokenArray;
  end;

function IsDigit(C: Char): Boolean;
begin
  Result := (C >= '0') and (C <= '9');
end;

function IsIdentifierStart(C: Char): Boolean;
begin
  Result := ((C >= 'a') and (C <= 'z')) or
    ((C >= 'A') and (C <= 'Z')) or (C = '_');
end;

function IsIdentifierPart(C: Char): Boolean;
begin
  Result := IsIdentifierStart(C) or IsDigit(C);
end;

function KeywordKind(const Text: string): TTokenKind;
begin
  if Text = 'let' then
    Result := tkLet
  else if Text = 'print' then
    Result := tkPrint
  else if Text = 'if' then
    Result := tkIf
  else if Text = 'else' then
    Result := tkElse
  else if Text = 'while' then
    Result := tkWhile
  else if Text = 'halt' then
    Result := tkHalt
  else if Text = 'true' then
    Result := tkTrue
  else if Text = 'false' then
    Result := tkFalse
  else
    Result := tkIdentifier;
end;

constructor TMicaLexer.Create(const Source: string);
begin
  inherited Create;
  FSource := Source;
  FIndex := 1;
  FLine := 1;
  FColumn := 1;
  SetLength(FTokens, 0);
end;

function TMicaLexer.AtEnd: Boolean;
begin
  Result := FIndex > Length(FSource);
end;

function TMicaLexer.Peek: Char;
begin
  if AtEnd then
    Result := #0
  else
    Result := FSource[FIndex];
end;

function TMicaLexer.Advance: Char;
begin
  Result := FSource[FIndex];
  Inc(FIndex);
  if Result = #10 then
  begin
    Inc(FLine);
    FColumn := 1;
  end
  else
    Inc(FColumn);
end;

function TMicaLexer.MatchChar(Expected: Char): Boolean;
begin
  if AtEnd or (Peek <> Expected) then
    Exit(False);
  Advance;
  Result := True;
end;

procedure TMicaLexer.SkipIgnored;
begin
  while not AtEnd do
  begin
    case Peek of
      ' ', #9, #13, #10:
        Advance;
      '#':
        begin
          while (not AtEnd) and (Peek <> #10) do
            Advance;
        end;
    else
      Exit;
    end;
  end;
end;

procedure TMicaLexer.AddToken(Kind: TTokenKind; StartIndex, StartLine,
  StartColumn: Integer; Value: Int64);
var
  NewIndex: Integer;
begin
  NewIndex := Length(FTokens);
  SetLength(FTokens, NewIndex + 1);
  FTokens[NewIndex].Kind := Kind;
  FTokens[NewIndex].Lexeme := Copy(FSource, StartIndex, FIndex - StartIndex);
  FTokens[NewIndex].IntValue := Value;
  FTokens[NewIndex].Line := StartLine;
  FTokens[NewIndex].Column := StartColumn;
end;

procedure TMicaLexer.ScanIdentifier(StartIndex, StartLine,
  StartColumn: Integer);
var
  Text: string;
begin
  while (not AtEnd) and IsIdentifierPart(Peek) do
    Advance;
  Text := Copy(FSource, StartIndex, FIndex - StartIndex);
  AddToken(KeywordKind(Text), StartIndex, StartLine, StartColumn, 0);
end;

procedure TMicaLexer.ScanInteger(StartIndex, StartLine, StartColumn: Integer);
var
  Value: Int64;
  Digit: Integer;
  OriginalStart: Integer;
begin
  OriginalStart := StartIndex;
  while (not AtEnd) and IsDigit(Peek) do
    Advance;

  Value := 0;
  while StartIndex < FIndex do
  begin
    Digit := Ord(FSource[StartIndex]) - Ord('0');
    if Value > (MICA_MAX_VALUE - Digit) div 10 then
      raise EMicaError.CreateAt('lex', StartLine, StartColumn,
        'integer literal exceeds 1000000000');
    Value := Value * 10 + Digit;
    Inc(StartIndex);
  end;
  AddToken(tkInteger, OriginalStart, StartLine, StartColumn, Value);
end;

procedure TMicaLexer.ScanOne;
var
  StartIndex: Integer;
  StartLine: Integer;
  StartColumn: Integer;
  C: Char;
begin
  StartIndex := FIndex;
  StartLine := FLine;
  StartColumn := FColumn;
  C := Advance;

  if IsDigit(C) then
  begin
    ScanInteger(StartIndex, StartLine, StartColumn);
    Exit;
  end;
  if IsIdentifierStart(C) then
  begin
    ScanIdentifier(StartIndex, StartLine, StartColumn);
    Exit;
  end;

  case C of
    '(' : AddToken(tkLeftParen, StartIndex, StartLine, StartColumn, 0);
    ')' : AddToken(tkRightParen, StartIndex, StartLine, StartColumn, 0);
    '{' : AddToken(tkLeftBrace, StartIndex, StartLine, StartColumn, 0);
    '}' : AddToken(tkRightBrace, StartIndex, StartLine, StartColumn, 0);
    ';' : AddToken(tkSemicolon, StartIndex, StartLine, StartColumn, 0);
    '+' : AddToken(tkPlus, StartIndex, StartLine, StartColumn, 0);
    '-' : AddToken(tkMinus, StartIndex, StartLine, StartColumn, 0);
    '*' : AddToken(tkStar, StartIndex, StartLine, StartColumn, 0);
    '/' : AddToken(tkSlash, StartIndex, StartLine, StartColumn, 0);
    '%' : AddToken(tkPercent, StartIndex, StartLine, StartColumn, 0);
    '=' :
      if MatchChar('=') then
        AddToken(tkEqualEqual, StartIndex, StartLine, StartColumn, 0)
      else
        AddToken(tkEqual, StartIndex, StartLine, StartColumn, 0);
    '!' :
      if MatchChar('=') then
        AddToken(tkBangEqual, StartIndex, StartLine, StartColumn, 0)
      else
        AddToken(tkBang, StartIndex, StartLine, StartColumn, 0);
    '<' :
      if MatchChar('=') then
        AddToken(tkLessEqual, StartIndex, StartLine, StartColumn, 0)
      else
        AddToken(tkLess, StartIndex, StartLine, StartColumn, 0);
    '>' :
      if MatchChar('=') then
        AddToken(tkGreaterEqual, StartIndex, StartLine, StartColumn, 0)
      else
        AddToken(tkGreater, StartIndex, StartLine, StartColumn, 0);
  else
    raise EMicaError.CreateAt('lex', StartLine, StartColumn,
      Format('unexpected byte $%.2x', [Ord(C)]));
  end;
end;

function TMicaLexer.ScanAll: TTokenArray;
var
  NewIndex: Integer;
begin
  while True do
  begin
    SkipIgnored;
    if AtEnd then
      Break;
    ScanOne;
  end;

  NewIndex := Length(FTokens);
  SetLength(FTokens, NewIndex + 1);
  FTokens[NewIndex].Kind := tkEOF;
  FTokens[NewIndex].Lexeme := '';
  FTokens[NewIndex].IntValue := 0;
  FTokens[NewIndex].Line := FLine;
  FTokens[NewIndex].Column := FColumn;
  Result := FTokens;
end;

function Tokenize(const Source: string): TTokenArray;
var
  Scanner: TMicaLexer;
begin
  Scanner := TMicaLexer.Create(Source);
  try
    Result := Scanner.ScanAll;
  finally
    Scanner.Free;
  end;
end;

end.
