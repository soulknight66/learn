package pebble

func Analyze(program Program) (*Analysis, error) {
	if !validSpan(program.Span) {
		return nil, languageError(StageAnalyze, CodeInvalidAST, program.Span.Start, "program span is invalid")
	}
	if len(program.Statements) == 0 && program.Span.Start != program.Span.End {
		return nil, languageError(StageAnalyze, CodeInvalidAST, program.Span.Start, "empty program must have an empty span")
	}
	if len(program.Statements) > 0 && program.Statements[0].Span.Start != program.Span.Start {
		return nil, languageError(StageAnalyze, CodeInvalidAST, program.Span.Start, "program must start at its first statement")
	}
	slots := make(map[string]int)
	seenExpressions := make(map[*Expr]bool)
	previousEnd := program.Span.Start.Offset
	for i := range program.Statements {
		statement := &program.Statements[i]
		if !spanContains(program.Span, statement.Span) || statement.Span.Start.Offset < previousEnd {
			return nil, languageError(StageAnalyze, CodeInvalidAST, statement.Span.Start, "statement span is outside program or unordered")
		}
		if err := validateStatementShape(statement); err != nil {
			return nil, err
		}
		if statement.Kind == StmtLet {
			if _, exists := slots[statement.Name]; exists {
				return nil, languageError(StageAnalyze, CodeRedeclaredName, statement.NameSpan.Start, "name is already declared")
			}
		}
		if err := analyzeExpression(statement.Expr, slots, seenExpressions); err != nil {
			return nil, err
		}
		if statement.Kind == StmtLet {
			slots[statement.Name] = len(slots)
		}
		previousEnd = statement.Span.End.Offset
	}
	return &Analysis{Slots: slots, SlotCount: len(slots)}, nil
}

func analyzeExpression(expr *Expr, slots map[string]int, seen map[*Expr]bool) error {
	if expr != nil && seen[expr] {
		return languageError(StageAnalyze, CodeInvalidAST, expr.Span.Start, "expression graph contains a cycle or shared node")
	}
	if err := validateExpressionShape(expr); err != nil {
		return err
	}
	seen[expr] = true
	switch expr.Kind {
	case ExprInteger:
		return nil
	case ExprName:
		if _, exists := slots[expr.Name]; !exists {
			return languageError(StageAnalyze, CodeUndefinedName, expr.Span.Start, "name is not defined")
		}
		return nil
	case ExprBinary:
		if err := analyzeExpression(expr.Left, slots, seen); err != nil {
			return err
		}
		return analyzeExpression(expr.Right, slots, seen)
	default:
		return languageError(StageAnalyze, CodeInvalidAST, expr.Span.Start, "unknown expression kind")
	}
}

func validateStatementShape(statement *Stmt) error {
	if statement == nil || !validSpan(statement.Span) {
		return languageError(StageAnalyze, CodeInvalidAST, Position{}, "statement is nil or has an invalid span")
	}
	if statement.Expr == nil || !spanContains(statement.Span, statement.Expr.Span) {
		return languageError(StageAnalyze, CodeInvalidAST, statement.Span.Start, "statement expression is missing or outside its span")
	}
	switch statement.Kind {
	case StmtLet:
		if !validIdentifier(statement.Name) || statement.Name == "let" || statement.Name == "print" ||
			!spanContains(statement.Span, statement.NameSpan) || statement.NameSpan.Start == statement.NameSpan.End ||
			statement.Span.Start.Offset >= statement.NameSpan.Start.Offset ||
			statement.NameSpan.End.Offset > statement.Expr.Span.Start.Offset ||
			statement.Expr.Span.End.Offset >= statement.Span.End.Offset ||
			statement.NameSpan.End.Offset-statement.NameSpan.Start.Offset != len(statement.Name) ||
			statement.NameSpan.Start.Line != statement.NameSpan.End.Line ||
			statement.NameSpan.End.Column-statement.NameSpan.Start.Column != len(statement.Name) {
			return languageError(StageAnalyze, CodeInvalidAST, statement.Span.Start, "let name or name span is invalid")
		}
	case StmtPrint:
		if statement.Name != "" || statement.NameSpan != (Span{}) {
			return languageError(StageAnalyze, CodeInvalidAST, statement.Span.Start, "non-let statement contains name data")
		}
		if statement.Span.Start.Offset >= statement.Expr.Span.Start.Offset || statement.Expr.Span.End.Offset >= statement.Span.End.Offset {
			return languageError(StageAnalyze, CodeInvalidAST, statement.Span.Start, "print expression span is invalid")
		}
	case StmtExpr:
		if statement.Name != "" || statement.NameSpan != (Span{}) || statement.Span != statement.Expr.Span {
			return languageError(StageAnalyze, CodeInvalidAST, statement.Span.Start, "expression statement shape is invalid")
		}
	default:
		return languageError(StageAnalyze, CodeInvalidAST, statement.Span.Start, "unknown statement kind")
	}
	return nil
}

func validateExpressionShape(expr *Expr) error {
	if expr == nil || !validSpan(expr.Span) || expr.Span.Start == expr.Span.End {
		return languageError(StageAnalyze, CodeInvalidAST, Position{}, "expression is nil or has an invalid span")
	}
	switch expr.Kind {
	case ExprInteger:
		if expr.Integer < 0 || expr.Name != "" || expr.Op != TokenInvalid || expr.Left != nil || expr.Right != nil {
			return languageError(StageAnalyze, CodeInvalidAST, expr.Span.Start, "integer expression contains unrelated fields")
		}
	case ExprName:
		if !validIdentifier(expr.Name) || expr.Name == "let" || expr.Name == "print" ||
			expr.Integer != 0 || expr.Op != TokenInvalid || expr.Left != nil || expr.Right != nil ||
			expr.Span.End.Offset-expr.Span.Start.Offset != len(expr.Name) ||
			expr.Span.Start.Line != expr.Span.End.Line || expr.Span.End.Column-expr.Span.Start.Column != len(expr.Name) {
			return languageError(StageAnalyze, CodeInvalidAST, expr.Span.Start, "name expression is invalid")
		}
	case ExprBinary:
		if expr.Integer != 0 || expr.Name != "" || !isBinaryOperator(expr.Op) || expr.Left == nil || expr.Right == nil ||
			!spanContains(expr.Span, expr.Left.Span) || !spanContains(expr.Span, expr.Right.Span) ||
			expr.Span.Start.Offset >= expr.Left.Span.Start.Offset ||
			expr.Left.Span.End.Offset > expr.Right.Span.Start.Offset ||
			expr.Right.Span.End.Offset >= expr.Span.End.Offset {
			return languageError(StageAnalyze, CodeInvalidAST, expr.Span.Start, "binary expression shape is invalid")
		}
	default:
		return languageError(StageAnalyze, CodeInvalidAST, expr.Span.Start, "unknown expression kind")
	}
	return nil
}
