program mica;

{$mode objfpc}{$H+}

uses
  Classes, SysUtils, mica_types, lexer, compiler, vm;

function ReadAllText(const FileName: string): string;
var
  Stream: TFileStream;
  ByteCount: LongInt;
begin
  Stream := TFileStream.Create(FileName, fmOpenRead or fmShareDenyNone);
  try
    if Stream.Size > High(LongInt) then
      raise Exception.Create('source file is too large');
    ByteCount := LongInt(Stream.Size);
    SetLength(Result, ByteCount);
    if ByteCount > 0 then
      Stream.ReadBuffer(Result[1], ByteCount);
  finally
    Stream.Free;
  end;
end;

procedure Usage;
begin
  WriteLn(StdErr, 'usage: mica [--tokens|--bytecode] SOURCE');
end;

procedure PrintTokens(const Tokens: TTokenArray);
var
  I: Integer;
  DisplayLexeme: string;
begin
  for I := 0 to High(Tokens) do
  begin
    if Tokens[I].Kind = tkEOF then
      DisplayLexeme := '<eof>'
    else
      DisplayLexeme := Tokens[I].Lexeme;
    WriteLn(Tokens[I].Line, ':', Tokens[I].Column, ' ',
      TokenName(Tokens[I].Kind), ' ', DisplayLexeme);
  end;
end;

procedure PrintBytecode(const ProgramImage: TCompiledProgram);
var
  I: Integer;
  IndexText: string;
begin
  for I := 0 to High(ProgramImage.Code) do
  begin
    IndexText := IntToStr(I);
    while Length(IndexText) < 4 do
      IndexText := '0' + IndexText;
    Write(IndexText, ' ', OpName(ProgramImage.Code[I].Op));
    if OpHasArgument(ProgramImage.Code[I].Op) then
      Write(' ', ProgramImage.Code[I].Arg);
    WriteLn(' @', ProgramImage.Code[I].Line, ':', ProgramImage.Code[I].Column);
  end;
end;

function FailureExitCode(const Phase: string): Integer;
begin
  if Phase = 'runtime' then
    Result := 70
  else
    Result := 65;
end;

var
  Action: string;
  SourcePath: string;
  Source: string;
  Tokens: TTokenArray;
  ProgramImage: TCompiledProgram;
begin
  Action := 'run';
  if (ParamCount = 1) and (ParamStr(1) <> '--tokens') and
    (ParamStr(1) <> '--bytecode') then
    SourcePath := ParamStr(1)
  else if (ParamCount = 2) and
    ((ParamStr(1) = '--tokens') or (ParamStr(1) = '--bytecode')) then
  begin
    Action := Copy(ParamStr(1), 3, Length(ParamStr(1)) - 2);
    SourcePath := ParamStr(2);
  end
  else
  begin
    Usage;
    Halt(64);
  end;

  try
    Source := ReadAllText(SourcePath);
  except
    on E: Exception do
    begin
      WriteLn(StdErr, SourcePath, ': ', E.Message);
      Halt(66);
    end;
  end;

  try
    Tokens := Tokenize(Source);
    if Action = 'tokens' then
    begin
      PrintTokens(Tokens);
      Halt(0);
    end;
    ProgramImage := CompileTokens(Tokens);
    if Action = 'bytecode' then
    begin
      PrintBytecode(ProgramImage);
      Halt(0);
    end;
    RunProgram(ProgramImage);
  except
    on E: EMicaError do
    begin
      WriteLn(StdErr, SourcePath, ':', E.SourceLine, ':', E.SourceColumn,
        ': ', E.Phase, ': ', E.Message);
      Halt(FailureExitCode(E.Phase));
    end;
  end;
end.
