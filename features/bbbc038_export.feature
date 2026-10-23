Feature: BBBC038 lab-figure export (Epic #1024)
  @needs_numpy
  Scenario: exportgraphics writes a png and a pdf at 300 dpi
    Given a fresh nuclei export session
    When I export the nuclei layout to "/tmp/openmatlab-m16-v07-bdd"
    Then the nuclei export variable "png_bytes" is greater than 0
    And the nuclei export variable "pdf_bytes" is greater than 0
