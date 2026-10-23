Feature: Record 100 lab-figure export (Epic #1012)
  @needs_numpy
  Scenario: exportgraphics writes a png and a pdf
    Given a fresh export session
    When I export the lab layout to "/tmp/openmatlab-m15-v07-bdd"
    Then export variable "png_bytes" is greater than 0
    And export variable "pdf_bytes" is greater than 0
