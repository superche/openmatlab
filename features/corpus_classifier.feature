Feature: Corpus preprocessing and root-cause classifier (Epic #763, M12 C03/C04)
  Scenario: a pasted command-window transcript becomes runnable code
    Given the snippet ">> a = 2+3" followed by its echoed output
    When I normalize it
    Then the code is "a = 2+3" and the echo is kept as expected output

  Scenario: an undefined Octave function is corpus noise, not a missing builtin
    When I classify an eval error "Undefined function or variable: printf"
    Then the category is "corpus-noise"

  Scenario: the labelled failure set meets the accuracy bar
    When I score the classifier on the labelled set
    Then at least 60 failures are labelled
    And the accuracy is at least 90 percent with full internal-crash recall
