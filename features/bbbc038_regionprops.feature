Feature: bwlabel and regionprops on a binary mask (Epic #1022)
  @needs_numpy
  Scenario: an eight-connected diagonal is one object
    Given a 2 by 2 diagonal mask
    When I evaluate the labels "[L, n] = bwlabel(BW); st = regionprops(L, 'Area'); a = st.Area;"
    Then the label variable "n" equals row [1]
    And the label variable "a" equals row [2]

  Scenario: a four-connected diagonal is two objects
    Given a 2 by 2 diagonal mask
    When I evaluate the labels "[L, n] = bwlabel(BW, 4);"
    Then the label variable "n" equals row [2]
