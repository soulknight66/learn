unit lexer;

{$mode objfpc}{$H+}

interface

uses
  mica_types;

function Tokenize(const Source: string): TTokenArray;

implementation

function Tokenize(const Source: string): TTokenArray;
begin
  { TODO: Replace this sentinel with a complete, location-preserving lexer. }
  SetLength(Result, 0);
  raise EMicaError.CreateAt('lex', 1, 1, 'lexer not implemented');
end;

end.
