unit vm;

{$mode objfpc}{$H+}

interface

uses
  mica_types;

procedure RunProgram(const ProgramImage: TCompiledProgram);

implementation

procedure RunProgram(const ProgramImage: TCompiledProgram);
begin
  { TODO: Execute ProgramImage with checked arithmetic and a bounded step count. }
  raise EMicaError.CreateAt('runtime', 1, 1,
    'virtual machine not implemented');
end;

end.
