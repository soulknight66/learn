unit compiler;

{$mode objfpc}{$H+}

interface

uses
  mica_types;

function CompileTokens(const Tokens: TTokenArray): TCompiledProgram;

implementation

function CompileTokens(const Tokens: TTokenArray): TCompiledProgram;
begin
  { TODO: Parse Tokens and emit deterministic stack bytecode. }
  SetLength(Result.Code, 0);
  Result.VariableCount := 0;
  raise EMicaError.CreateAt('compile', 1, 1, 'compiler not implemented');
end;

end.
