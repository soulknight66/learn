unit vm;

{$mode objfpc}{$H+}

interface

uses
  mica_types;

procedure RunProgram(const ProgramImage: TCompiledProgram);

implementation

uses
  SysUtils;

procedure RunProgram(const ProgramImage: TCompiledProgram);
var
  Stack: array of Int64;
  StackCount: Integer;
  Variables: array of Int64;
  ProgramCounter: Integer;
  Steps: Integer;
  Instruction: TInstruction;
  LeftValue: Int64;
  RightValue: Int64;
  ResultValue: Int64;
  I: Integer;

  procedure RuntimeError(const AtInstruction: TInstruction;
    const MessageText: string);
  begin
    raise EMicaError.CreateAt('runtime', AtInstruction.Line,
      AtInstruction.Column, MessageText);
  end;

  procedure Push(Value: Int64);
  var
    NewCapacity: Integer;
  begin
    if StackCount = Length(Stack) then
    begin
      NewCapacity := Length(Stack) * 2;
      if NewCapacity = 0 then
        NewCapacity := 32;
      SetLength(Stack, NewCapacity);
    end;
    Stack[StackCount] := Value;
    Inc(StackCount);
  end;

  function Pop(const AtInstruction: TInstruction): Int64;
  begin
    if StackCount = 0 then
      RuntimeError(AtInstruction, 'invalid bytecode: stack underflow');
    Dec(StackCount);
    Result := Stack[StackCount];
  end;

  function CheckedValue(Value: Int64;
    const AtInstruction: TInstruction): Int64;
  begin
    if (Value < MICA_MIN_VALUE) or (Value > MICA_MAX_VALUE) then
      RuntimeError(AtInstruction, 'arithmetic result outside Mica integer domain');
    Result := Value;
  end;

  function SlotIndex(Argument: Int64;
    const AtInstruction: TInstruction): Integer;
  begin
    if (Argument < 0) or (Argument >= Length(Variables)) then
      RuntimeError(AtInstruction, 'invalid bytecode: variable slot out of range');
    Result := Integer(Argument);
  end;

  function JumpTarget(Argument: Int64;
    const AtInstruction: TInstruction): Integer;
  begin
    if (Argument < 0) or (Argument >= Length(ProgramImage.Code)) then
      RuntimeError(AtInstruction, 'invalid bytecode: jump target out of range');
    Result := Integer(Argument);
  end;

begin
  SetLength(Stack, 32);
  StackCount := 0;
  SetLength(Variables, ProgramImage.VariableCount);
  for I := 0 to High(Variables) do
    Variables[I] := 0;
  ProgramCounter := 0;
  Steps := 0;

  while (ProgramCounter >= 0) and
    (ProgramCounter < Length(ProgramImage.Code)) do
  begin
    Instruction := ProgramImage.Code[ProgramCounter];
    Inc(Steps);
    if Steps > MICA_STEP_LIMIT then
      RuntimeError(Instruction, 'instruction limit exceeded');
    Inc(ProgramCounter);

    case Instruction.Op of
      opConst:
        Push(CheckedValue(Instruction.Arg, Instruction));
      opLoad:
        Push(Variables[SlotIndex(Instruction.Arg, Instruction)]);
      opStore:
        Variables[SlotIndex(Instruction.Arg, Instruction)] := Pop(Instruction);
      opAdd:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          ResultValue := LeftValue + RightValue;
          Push(CheckedValue(ResultValue, Instruction));
        end;
      opSubtract:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          ResultValue := LeftValue - RightValue;
          Push(CheckedValue(ResultValue, Instruction));
        end;
      opMultiply:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          ResultValue := LeftValue * RightValue;
          Push(CheckedValue(ResultValue, Instruction));
        end;
      opDivide:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if RightValue = 0 then
            RuntimeError(Instruction, 'division by zero');
          ResultValue := LeftValue div RightValue;
          Push(CheckedValue(ResultValue, Instruction));
        end;
      opRemainder:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if RightValue = 0 then
            RuntimeError(Instruction, 'remainder by zero');
          ResultValue := LeftValue mod RightValue;
          Push(CheckedValue(ResultValue, Instruction));
        end;
      opNegate:
        begin
          ResultValue := -Pop(Instruction);
          Push(CheckedValue(ResultValue, Instruction));
        end;
      opNot:
        begin
          if Pop(Instruction) = 0 then
            Push(1)
          else
            Push(0);
        end;
      opEqual:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if LeftValue = RightValue then Push(1) else Push(0);
        end;
      opNotEqual:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if LeftValue <> RightValue then Push(1) else Push(0);
        end;
      opLess:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if LeftValue < RightValue then Push(1) else Push(0);
        end;
      opLessEqual:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if LeftValue <= RightValue then Push(1) else Push(0);
        end;
      opGreater:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if LeftValue > RightValue then Push(1) else Push(0);
        end;
      opGreaterEqual:
        begin
          RightValue := Pop(Instruction);
          LeftValue := Pop(Instruction);
          if LeftValue >= RightValue then Push(1) else Push(0);
        end;
      opJump:
        ProgramCounter := JumpTarget(Instruction.Arg, Instruction);
      opJumpIfFalse:
        begin
          ResultValue := Pop(Instruction);
          if ResultValue = 0 then
            ProgramCounter := JumpTarget(Instruction.Arg, Instruction);
        end;
      opPrint:
        WriteLn(Pop(Instruction));
      opHalt:
        Exit;
    end;
  end;
end;

end.
