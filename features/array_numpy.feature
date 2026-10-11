Feature: Array-first NumPy backend
  As a runtime consumer
  I want concrete Array values via NumPyArrayBackend
  So that matrix math can land without a float-dict evaluator

  @needs_numpy
  Scenario: Scalar is stored as 1x1
    Given a NumPy array backend
    When I create a scalar array from 2.0
    Then the array is scalar
    And the array shape is 1 by 1

  @needs_numpy
  Scenario: Matrix multiply of 2x2
    Given a NumPy array backend
    When I matmul identity with [[1, 2], [3, 4]]
    Then the result equals [[1, 2], [3, 4]]
