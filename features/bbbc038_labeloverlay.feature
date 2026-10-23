Feature: labeloverlay paints labels onto a gray image (Epic #1023)
  @needs_numpy
  Scenario: the default blend of a black pixel and label 1 is half of the first color
    Given a one-pixel black image labeled 1
    When I evaluate the overlay "B = labeloverlay(A, L);"
    Then the overlay variable "B" equals uint8 [114, 13, 14]

  Scenario: full transparency leaves a labeled pixel unchanged
    Given a one-pixel black image labeled 1
    When I evaluate the overlay "B = labeloverlay(A, L, 'Transparency', 1);"
    Then the overlay variable "B" equals uint8 [0, 0, 0]
