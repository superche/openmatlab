Feature: lab-meeting figure export (Epic #998)
  exportgraphics writes a PNG and a PDF of a tiled heatmap figure.
  The demo resolution is 300 dpi. The default, when a script omits it, is 150.

  @needs_numpy @needs_matplotlib
  Scenario: both files are written
    When I evaluate "f = figure('Visible','off'); tiledlayout(1, 2); nexttile; plot(1:4); nexttile; heatmap({'a','b'}, {'a','b'}, [1 0; 0 1], 'Title', 'corr'); d = tempname; mkdir(d); exportgraphics(f, fullfile(d, 'a.png'), 'Resolution', 300); exportgraphics(f, fullfile(d, 'a.pdf')); png_ok = isfile(fullfile(d, 'a.png')); pdf_ok = isfile(fullfile(d, 'a.pdf'));"
    Then variable "png_ok" equals scalar 1
    And variable "pdf_ok" equals scalar 1
