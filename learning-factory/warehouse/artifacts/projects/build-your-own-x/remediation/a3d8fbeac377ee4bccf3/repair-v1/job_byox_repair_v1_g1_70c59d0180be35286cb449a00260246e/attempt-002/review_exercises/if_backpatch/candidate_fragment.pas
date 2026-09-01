unit candidate_fragment;

{$mode objfpc}{$H+}

interface

procedure CompileIf;

implementation

function EmitJump(Op: Integer): Integer;
begin
  Result := 0;
end;

procedure PatchToHere(Index: Integer);
begin
end;

procedure Expression;
begin
end;

procedure Block;
begin
end;

function MatchElse: Boolean;
begin
  Result := False;
end;

procedure CompileIf;
var
  FalseJump: Integer;
  EndJump: Integer;
begin
  Expression;
  FalseJump := EmitJump(1);
  Block;
  PatchToHere(FalseJump);
  if MatchElse then
  begin
    EndJump := EmitJump(0);
    Block;
    PatchToHere(EndJump);
  end;
end;

end.
