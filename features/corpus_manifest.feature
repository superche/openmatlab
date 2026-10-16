Feature: Corpus manifest and licence allow-list (Epic #762, M12 C01)
  Scenario: the committed manifest passes the licence check
    When I run the corpus licence check
    Then it reports no problems
    And the manifest lists at least 300 runnable entries from 4 sources

  Scenario: a copyleft source marked for vendoring is rejected
    Given the manifest with source "octave" set to policy "vendor"
    When I check the allow-list
    Then a problem mentions "octave"
