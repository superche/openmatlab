# MATLAB core use-case gap analysis

**Captured:** 2026-10-13 (Asia/Shanghai) on `main` after #526.
**Method:** every status below was checked on the real CLI; nothing comes from memory.
- **Per-function existence:** `openmatlab -e "NAME()"`. A missing function prints `Undefined function or variable: NAME`; a present one fails on its arguments or runs.
- **Behaviour probes:** the commands quoted in the Evidence column.
- **Script, function-file and classdef probes:** small `.m` files reached through `addpath`. They are reproduced in the appendix.

Categories follow the public MATLAB documentation tree: Language Fundamentals, Mathematics, Graphics, Data Import and Analysis, Programming Scripts and Functions, App Building / Desktop.
Priority reflects impact on a typical user:
- **p0:** common scripts break without it.
- **p1:** common in engineering and science work.
- **p2:** specialised.

## Summary

> **M10 and M11 opened (2026-10-16, approved by Shaw).** [Tables and data types](https://github.com/superche/openmatlab/milestone/10) (`docs/milestones/M10-tables.md`, T01–T10, epics #691–#697) and [Debugger and Workbench](https://github.com/superche/openmatlab/milestone/11) (`docs/milestones/M11-debugger-workbench.md`, D01–D10, epics #698–#703), interleaved and led by D-E1. They reference (do not move) #565 #577 #585 #602 #611 #665 #673.
>
> **M8 and M3 closed (2026-10-16).** M8 Object system 10/10 (epics #618–#624); M3 Domain toolboxes 7/7 (epics #625–#631). p2 residuals stay on the closed milestones (M8: #593 #602 #636 #645 #653 #669 #673 #677; M3: #581 #649 #657 #661 #665 #681 #685).
>
> **M7 closed (2026-10-13), 11/11 criteria (C11 adds `evalin`/`assignin`/`doc`/`lookfor`/`what`).** The residual issues were re-homed:
> - Core backlog: #565 #569 #573 #577 #585 #589 #598 #611;
> - Object system: #593 #602;
> - Domain toolboxes (M3): #581.
>
> The Object system milestone delivered the OOP row (classdef).

> **M7 update (2026-10-13):** every M7 conformance criterion (C01–C10) is met, and each M7-tagged row below now says what was delivered and what remains, with an issue for the remainder. The original findings are kept underneath as the historical baseline. A probe sweep after M7 found no Python exceptions reaching the user (fixed in #606). The rows tagged M3 and new-milestone still reflect the original capture, except that some numerics (polyfit/polyval/roots/conv/deconv, interp1, trapz/cumtrapz/integral, fzero/fminsearch, filter, histcounts/cov/corrcoef, readmatrix/writematrix and friends) shipped early with Epic #534 and #533.

- **Strong:** array core, indexing, cells, structs, N-D arrays, complex numbers, integer classes, strings/regexp, sparse matrices and linear solve (the M2 C01–C19 criteria).
- **Missing at p0 level:** whole areas that ordinary MATLAB scripts use:
  - error handling (`try/catch`, `error`);
  - variadic functions (`nargin`, `varargin`);
  - local functions in scripts. This path **crashes with a Python traceback**.
  - command syntax (`hold on`, `format long`, `clear x`);
  - formatted and file I/O (`fprintf`, `fopen`, `save`/`load`);
  - random numbers;
  - `diff`, `repmat`, `meshgrid`, sets, `tic`/`toc`;
  - the plot-decoration calls (`figure`, `hold`, `title`, `xlabel`, `legend`, `subplot`).
- **Missing altogether:** domain numerics (polynomials, interpolation, integration, ODE, optimisation, FFT, statistics), tables/datetime and classdef.

## Gap table

| Area | Item | Status | Evidence (`openmatlab -e ...`) | Priority | Candidate epic / milestone |
|------|------|--------|-------------------------------|----------|----------------------------|
| Language fundamentals | Array constructors / shape (`zeros ones eye linspace magic reshape size numel cat`) | **present** | `openmatlab -e "zeros(2), ones(1,2), eye(2)"`, `"reshape(1:4,2,2)"`, `"magic(3)"` → correct | — | — |
| Language fundamentals | `repmat kron horzcat vertcat colon logspace meshgrid ndgrid` | **present** | delivered in M7 (Epic #535); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-ARRAYS |
| Language fundamentals | Cell conversions `cell2mat num2cell iscellstr` | **present** | delivered in M7 (Epic #535); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-ARRAYS |
| Language fundamentals | Type queries `class isa isnumeric ischar islogical isstruct iscell isfield isequal` | **present** | `"isnumeric(1), ischar('a'), islogical(true)"` → 1 1 1 | — | — |
| Language fundamentals | `mat2str int2str dec2bin bin2dec hex2dec dec2hex blanks deblank` | **present** | delivered in M7 (Epic #536); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-STRINGS |
| Language fundamentals | Command syntax (`hold on`, `format long`, `clear x`, `close all`, `which sin`) | **present** | delivered in M7 (Epic #532); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-COMMAND-SYNTAX |
| Mathematics | Elementary `abs sqrt exp log log10 sin cos tan floor ceil round mod max min sum prod cumsum` | **present** | `"abs(-1), sqrt(4), sum([1 2])"` → 1 2 3 | — | — |
| Mathematics | `fix rem sign hypot log2 diff cumprod gcd lcm primes factor isprime nchoosek factorial` | **present** | delivered in M7 (Epic #534); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-MATH |
| Mathematics | `round(x, n)` digits form | **present** | delivered in M7 (Epic #534); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-MATH |
| Mathematics | Linear solve / `inv det rank pinv norm expm` (M2 C17) | **present** | `"A=[2 1;1 3]; x=A\\[3;5]"` → 0.8 1.4 | — | — |
| Mathematics | Decompositions `eig svd lu qr chol null orth trace cross dot` | **present** | delivered in M7 (Epic #538); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-LINALG-DECOMP |
| Mathematics | Sparse (M2 C16/C19, #522/#523) | **present** | `"S=sparse(1e5,1e5); E=speye(1e5); nnz(E)"` → 100000 | — | — |
| Polynomials | `polyfit polyval roots poly conv deconv polyder polyint` | **present** | `polyfit polyval roots conv deconv` present; `poly polyder polyint` delivered in M3-E2 (#626) (verified 2026-10-13) | — | M3-POLY-INTERP |
| Interpolation | `interp1 interp2 spline pchip` | **present** | `interp1` present; `interp1` spline/pchip, `interp2`, `spline`, `pchip`, `ppval` delivered in M3-E2 (#626); residual #649 (verified 2026-10-13) | — | M3-POLY-INTERP |
| Integration | `trapz cumtrapz integral integral2 quad` | **present** | `trapz cumtrapz integral` present; `integral2`, `quad`, `integral` ArrayValued delivered in M3-E3 (#627); residual #657 (verified 2026-10-13) | — | M3-CALCULUS-ODE-OPT |
| ODE | `ode45 ode23` | **present** | `ode45 ode23 odeset odeget` delivered in M3-E3 (#627); stiff solvers/Events → #657 (verified 2026-10-13) | — | M3-CALCULUS-ODE-OPT |
| Optimization | `fzero fminsearch fminbnd` | **present** | `fzero fminsearch` present; `fminbnd`, `optimset`/`optimget` and fminsearch options delivered in M3-E3 (#627) (verified 2026-10-13) | — | M3-CALCULUS-ODE-OPT |
| FFT / filtering | `fft ifft fft2 filter filtfilt` | **partial** | `fft ifft fft2 ifft2 fftn ifftn fftshift ifftshift nextpow2` delivered in M3-E1 (#625); `filter` present; `filtfilt` → community.signal plugin (#630) (verified 2026-10-13) | p1 | M3-SIGNAL |
| Statistics | `mean max min` present; `median mode std var` | **present** | delivered in M7 (Epic #534); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-MATH |
| Statistics | `histcounts quantile prctile corrcoef cov movmean cummax cummin` | **present** | `histcounts corrcoef cov cummax cummin` present (Epic #534); `quantile prctile movmean` (and the mov* family, `histc`) delivered in M3-E4 (#628); residual #661 (verified 2026-10-13) | — | M3-STATS |
| Random numbers | `rand randn randi rng randperm` | **present** | delivered in M7 (Epic #534); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-MATH |
| Sets | `union intersect setdiff setxor ismember sortrows` | **present** | delivered in M7 (Epic #535); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-ARRAYS |
| Sets | `unique` numeric (M2 C09) | **present** | delivered in M7 (Epic #535); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-ARRAYS |
| Strings / regexp | `regexp regexpi regexprep strtrim strcmp strcmpi strncmp strrep upper lower split join contains startsWith extractAfter compose sprintf num2str str2double` | **present** | `"regexprep('abc','b','X')"` → aXc; `"sprintf('%d,%s',3,'a')"` → 3,a | — | — |
| Strings / regexp | `strsplit strjoin strfind strcat strvcat str2num` | **present** | delivered in M7 (Epic #536); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-STRINGS |
| Cells / functional | `cellfun arrayfun structfun` incl. `'UniformOutput'` | **present** | `"cellfun(@(x) x*2, {1,2}, 'UniformOutput', false)"` → {2,4} | — | — |
| Cells / functional | `containers.Map` | **present** | delivered in M7 (Epic #539); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-DATA-TYPES |
| Structs | structs / struct arrays (M2 C18) | **present** | `"s=struct('a',{1,2}); numel(s)"` → 2 | — | — |
| Tables etc. | `table timetable categorical` | **partial** | `table` core (Epic #691, T01/T02; residual #709), `categorical` (Epic #692, T04; residual #717) , `readtable`/`writetable` (Epic #694, T08; residual #721) and table utilities, sorting and sets (Epic #693, T03/T05; residual #738) and joins/grouping (Epic #696, T06/T07; residual #742) delivered 2026-10-16; missing: `timetable` | p1 | [M10 Tables and data types](https://github.com/superche/openmatlab/milestone/10) (T01–T10) |
| Date / time | `datetime duration seconds datenum datestr clock now` | **present** | delivered in M7 (Epic #539); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13); datetime arrays, `NaT`, `InputFormat`, `calendarDuration` (`caldays calmonths calyears between split`), `dateshift` added in M10 (Epic #695, residual #733) | — | E-DATA-TYPES |
| Performance tooling | `tic toc pause cputime` | **present** | delivered in M7 (Epic #534); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-CORE-MATH |
| Errors / exceptions | `try/catch` | **present** | delivered in M7 (Epic #530); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-ERRORS |
| Errors / exceptions | `error MException throw rethrow assert lasterr`; `warning lastwarn` | **present** | delivered in M7 (Epic #530); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-ERRORS |
| Errors / exceptions | `MException.stack` lines, `getReport`, `dbstack`, `mfilename`, "Error in f (line N)" | **present** | delivered in M11 D-E1 (Epic #698; D01/D02 met, 2026-10-16); residual #705 | — | [M11](https://github.com/superche/openmatlab/milestone/11) |
| Scripts & functions | Function files (fixed arity) | **present** | `"addpath(...); r = f(x)"` resolves `.m` functions (lang.mfile BDD) | — | — |
| Scripts & functions | `varargin varargout nargin nargout narginchk nargoutchk` | **present** | delivered in M7 (Epic #531); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-FUNCTIONS |
| Scripts & functions | Local functions in script files | **present** | delivered in M7 (Epic #531); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-FUNCTIONS |
| Scripts & functions | `eval evalin feval str2func func2str exist isvarname` | **present** | delivered in M7 (Epic #531; `evalin`/`doc`/`lookfor`/`what` added by Epic #610, C11); verified 2026-10-13 | — | E-FUNCTIONS |
| Scripts & functions | `global persistent` | **present** | delivered in M7 (Epic #531); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-FUNCTIONS |
| Scripts & functions | `inputParser validateattributes` | **present** | delivered in #569 (inputParser, validateattributes, multi-input cellfun, inputname); edge residuals → #640 (verified 2026-10-13) | — | E-FUNCTIONS |
| OOP | `classdef` (properties, methods, constructors) | **present** | delivered in M8 (Epics #618–#624; O01–O10 met); residuals #636 #645 #653 #669 #673 #677 (verified 2026-10-16) | — | [Object system](https://github.com/superche/openmatlab/milestone/8) (closed) |
| File I/O | `disp` / `sprintf` present; `fprintf display` | **present** | delivered in M7 (Epic #533); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-FILE-IO |
| File I/O | `fopen fclose fgetl fgets fread fwrite fscanf textscan fileread dir` | **present** | delivered in M7 (Epic #533); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-FILE-IO |
| File I/O | `save load` (.mat) | **present** | delivered in M7 (Epic #533); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-FILE-IO |
| Data import/export | `readmatrix writematrix csvread csvwrite dlmread dlmwrite readtable writetable jsonencode jsondecode` | **partial** | `readmatrix writematrix csvread csvwrite dlmread dlmwrite` present (Epic #533); `jsonencode jsondecode` and dlmwrite `-append`/offsets delivered in M3-E5 (#629); residual #665; `readtable writetable readcell writecell` delivered for delimited text in M10 (Epic #694, residual #721) | p2 | M3-DATA-IO |
| File I/O | `input keyboard` | **present** | `input` and `keyboard` delivered in M11 (Epic #700, D06; residual #729) | — | E-FILE-IO; M11 D06 (Epic #700) |
| Graphics | `plot` (2-D line, figures region in Workbench) | **present** | delivered in M7 (Epic #537); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-GRAPHICS-CORE |
| Graphics | `figure hold subplot title xlabel ylabel legend grid axis xlim ylim gca gcf set get close saveas print` | **present** | delivered in M7 (Epic #537); all listed names resolve and are covered by the M7 conformance/unit tests (verified 2026-10-13) | — | E-GRAPHICS-CORE |
| Graphics | `bar scatter histogram pie area stairs stem errorbar semilogx semilogy loglog` | **partial** | delivered in M7 (Epic #537); still missing: `pie` `area` `stairs` `stem` `errorbar` `semilogx` `semilogy` `loglog` → #593 (verified 2026-10-13) | p1 | E-GRAPHICS-CORE |
| Graphics | `surf mesh contour plot3 imagesc colorbar colormap text line patch fill` | **missing** | missing: `surf` `mesh` `contour` `plot3` `imagesc` `colorbar` `colormap` `text` `line` `patch` `fill` | p2 | M3-SCI-GRAPHICS |
| App / Workbench | Command window, editor (tabs), workspace browser, current folder, figures (M6) | **partial** | `openmatlab workbench --help`; feature_map `host.workbench.*` all `partial`; editor note "no LSP/debugger" | — | — |
| App / Workbench | `help doc lookfor what who whos clc clear format pwd cd ls rmpath path` | **present** | delivered in M7 (Epic #532; `evalin`/`doc`/`lookfor`/`what` added by Epic #610, C11); verified 2026-10-13 | — | E-COMMAND-SYNTAX |
| App / Workbench | Debugger (breakpoints, dbstop/dbstep), variable editor, help browser | **partial** (engine: dbstop/dbstep/dbcont/dbquit/dbup/dbdown/K>> delivered in Epic #699, residual #713; Workbench UI and variable editor pending) | feature_map: no `debugger`/`variable_editor` feature id; `host.workbench.editor` notes "no LSP/debugger" | p1 | [M11 Debugger and Workbench](https://github.com/superche/openmatlab/milestone/11) (D03–D10) |
| Octave extensions | `x++`, `do ... until` | **missing** | `"x = 3; x++"` → `Unexpected token EOF` | p2 | non-goal (MATLAB first) |

## Proposed grouping

**New milestone M7 — MATLAB core language and I/O completeness.** These are core MATLAB, not toolboxes; p0 first:

| Epic | Scope | Priority |
|------|-------|----------|
| E-ERRORS | `try/catch`, `error` (id + format), `MException`, `throw`/`rethrow`, `assert`, `lasterr`, `err.stack` | p0 |
| E-FUNCTIONS | `nargin`/`nargout`/`varargin`/`varargout`, `narginchk`, local functions in scripts (fixes the crash), nested `end`-terminated functions, `global`/`persistent`, `eval`/`feval`/`str2func`/`func2str`/`exist`; then `inputParser`/`validateattributes` (p1) | p0 |
| E-COMMAND-SYNTAX | command syntax `cmd arg`; `clear clc who whos format help doc pwd cd ls dir path rmpath which` | p0 |
| E-FILE-IO | `fprintf` (console and fid), `fopen`/`fclose`/`fgetl`/`fgets`/`fread`/`fwrite`/`fscanf`/`textscan`, `fileread`, `save`/`load` (.mat v5 subset), `input` (p2) | p0 |
| E-CORE-MATH | `fix rem sign hypot log2 diff cumprod gcd lcm primes factor isprime nchoosek factorial`, `round(x,n)`, `median mode std var`, `rand randn randi rng randperm`, `tic toc pause` | p0 |
| E-CORE-ARRAYS | `repmat kron horzcat vertcat logspace meshgrid ndgrid cell2mat num2cell iscellstr`, sets `union intersect setdiff setxor ismember sortrows`, `unique` on cellstr/string | p0 |
| E-CORE-STRINGS | `strsplit strjoin strfind strcat strvcat str2num`; then `mat2str int2str dec2bin bin2dec hex2dec dec2hex blanks deblank` (p1) | p0/p1 |
| E-GRAPHICS-CORE | `figure hold subplot title xlabel ylabel legend grid axis xlim ylim gca gcf set get close saveas print`; then `bar scatter histogram pie area stairs stem errorbar semilog*/loglog` (p1) | p0/p1 |
| E-LINALG-DECOMP | `eig svd lu qr chol null orth trace cross dot` | p1 |
| E-DATA-TYPES | `containers.Map`, `datetime`/`duration`/`datenum`/`datestr`; then `table`/`timetable`/`categorical` (p2, possibly its own milestone) | p1/p2 |

**M3 — Domain toolboxes** (milestone/3, **closed 2026-10-16** at 7/7): domain libraries delivered as clean-room code. They ship either as `libs/` modules or as community plugins on the M4 contract, and each is gated like M5 by reference-vector conformance scripts:

| Epic | Scope | Priority |
|------|-------|----------|
| M3-POLY-INTERP | `polyfit polyval roots poly conv deconv polyder polyint interp1 interp2 spline pchip` | p1 |
| M3-CALCULUS-ODE-OPT | `trapz cumtrapz integral integral2 quad ode45 ode23 fzero fminsearch fminbnd` | p1 |
| M3-SIGNAL | `fft ifft fft2 filter filtfilt`; grow `community.signal` beyond `hamming`/`rectwin`/`blackman` (`hann kaiser`, `freqz`) | p1 |
| M3-STATS | `histcounts quantile prctile corrcoef cov movmean cummax cummin` | p1 |
| M3-DATA-IO | `readmatrix writematrix csvread csvwrite dlmread dlmwrite jsonencode jsondecode`; `readtable`/`writetable` after tables | p1 |
| M3-SCI-GRAPHICS | `surf mesh contour plot3 imagesc colorbar colormap text line patch fill` | p2 |

**Object system ([milestone/8](https://github.com/superche/openmatlab/milestone/8), **closed 2026-10-16** at 10/10):** `classdef` (value and handle classes, properties, methods, events) delivered; p2 residuals remain on the closed milestone.

**M6 follow-up — Workbench:** debugger, variable editor, help browser (p2).

## Appendix — probe files

```matlab
% /tmp/gap/localfn.m  (script with a local function)
r = helper(3);
disp(r)
function y = helper(x)
  y = x * 2;
end
% /tmp/gap/fdir/vfun.m
function varargout = vfun(varargin)
  varargout{1} = nargin;
  varargout{2} = numel(varargin);
end
% /tmp/gap/fdir/run_v.m
[a, b] = vfun(1, 2, 3);
disp([a b])
% /tmp/gap/fdir/Pt.m
classdef Pt
  properties
    x = 0
  end
  methods
    function obj = Pt(v)
      obj.x = v;
    end
    function r = dbl(obj)
      r = obj.x * 2;
    end
  end
end
% /tmp/gap/fdir/run_c.m
p = Pt(3);
disp(dbl(p))
```

Per-function existence results (`openmatlab -e "NAME()"`, 279 names):

- present (64): addpath arrayfun bitand bitshift cat cell cellfun char class compose contains det disp double exp expm extractAfter fieldnames fliplr inv isa iscell isequal isfield issorted isstruct join lastwarn linspace log log10 lower max mean min mod norm num2str pinv plot prod rank regexp regexpi regexprep round run sort split sprintf startsWith str2double strcmp strcmpi string strncmp strrep strtrim struct structfun unique upper warning which
- missing (215): MException area assert axis bar bin2dec blanks categorical cd cell2mat chol clc clear clock close colon colorbar colormap containers contour conv corrcoef cov cputime cross csvread csvwrite cummax cummin cumprod cumtrapz datenum datestr datetime deblank dec2bin dec2hex deconv diff dir display dlmread dlmwrite doc dot duration eig error errorbar eval evalin exist factor factorial fclose feval fft fft2 fgetl fgets figure fileread fill filter filtfilt fminbnd fminsearch fopen format fprintf fread fscanf func2str fwrite fzero gca gcd gcf get global grid help hex2dec histcounts histogram hold horzcat hypot ifft imagesc input inputParser int2str integral integral2 interp1 interp2 intersect iscellstr ismember isprime isvarname jsondecode jsonencode keyboard kron lasterr lcm legend line load log2 loglog logspace lookfor ls lu mat2str median mesh meshgrid mode movmean nargin narginchk nargout nargoutchk nchoosek ndgrid now null num2cell ode23 ode45 orth patch path pause pchip persistent pie plot3 poly polyder polyfit polyint polyval prctile primes print pwd qr quad quantile rand randi randn randperm readmatrix readtable rem repmat rethrow rmpath rng roots save saveas scatter seconds semilogx semilogy set setdiff setxor sign sortrows spline stairs std stem str2func str2num strcat strfind strjoin strsplit strvcat subplot surf svd table text textscan throw tic timetable title toc trace trapz union validateattributes var varargin vertcat what who whos writematrix writetable xlabel xlim ylabel ylim
