unit broken_vm_fragment;

{$mode objfpc}{$H+}

interface

procedure ExecuteBinary(Op: Integer);

implementation

function Pop: Int64;
begin
  { Supplied elsewhere by the exercise harness. }
  Result := 0;
end;

procedure Push(Value: Int64);
begin
  { Supplied elsewhere by the exercise harness. }
end;

procedure ExecuteBinary(Op: Integer);
var
  LeftValue: Int64;
  RightValue: Int64;
begin
  LeftValue := Pop;
  RightValue := Pop;
  case Op of
    0: Push(LeftValue + RightValue);
    1: Push(LeftValue - RightValue);
    2: Push(LeftValue * RightValue);
    3: Push(LeftValue div RightValue);
  end;
end;

end.
