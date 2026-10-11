Feature: Matrix-first lexer and parser
  As a language front-end
  I want matrix literals and .* vs * in the AST
  So that the evaluator (#4) can consume real syntax

  Scenario: Parse a 2x2 matrix literal
    When I parse "[1 2; 3 4]"
    Then the statement expression is a matrix with 2 rows

  Scenario: Star is matmul token distinct from dot-star
    When I parse "A * B"
    Then the binary operator is "*"
    When I parse "A .* B"
    Then the binary operator is ".*"
