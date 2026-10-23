Feature: Global imbinarize and bwareaopen (Epic #1021)
  @needs_numpy
  Scenario: default imbinarize thresholds a uint8 row with Otsu
    Given a uint8 row of six intensities
    When I evaluate the mask "level = graythresh(I); BW = imbinarize(I); BW2 = imbinarize(I, level); n = sum(BW(:)); same = sum(abs(double(BW(:)) - double(BW2(:))));"
    Then the mask variable "n" equals row [2]
    And the mask variable "same" equals row [0]

  Scenario: bwareaopen removes a component smaller than P
    Given a binary speck beside a block
    When I evaluate the mask "BW2 = bwareaopen(BW, 3); n = sum(BW2(:)); k = double(strcmp(class(BW2), 'logical'));"
    Then the mask variable "n" equals row [4]
    And the mask variable "k" equals row [1]
