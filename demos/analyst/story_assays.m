% Field-assay log (M17 analyst story, issue #1034, epic #1032).
% Synthetic rows written for this demo. No third-party file. The text is
% covered by the repository licence.
%
% Pipeline, in the order an analyst would run it:
%   readtable CSV with 'TreatAsMissing' -> ismissing summary
%   -> rmmissing / fillmissing -> groupsummary IncludeEmptyGroups
%   -> writetable CSV under demos/analyst/out/
%
% Placeholders 'NA', '-999', and a blank field become standard missing
% values. xlsx is not a path here: readtable still rejects spreadsheets.
% fillmissing in this story uses 'previous' (temperature) and 'constant'
% (qc). 'next' exists and is not needed on this file. Other fill methods
% are out of scope.
%
% The sheet is ordered by site, and each site's first kept row already
% has a temperature, so 'previous' does not carry a temperature across
% sites. Moisture is not imputed: rows that still lack moisture_pct are
% removed. West is a planned site with no rows. It is a category, and
% IncludeEmptyGroups keeps it, with GroupCount 0 and a mean of NaN.
%
% Exports (gitignored; the directory's README is the tracked convention):
%   demos/analyst/out/site_summary.csv
%   demos/analyst/out/cleaned.csv
% writematrix already writes a numeric matrix (Epic #533). This result is
% a table, so the story uses writetable.
%
% From the repository root:
%   openmatlab -e "run('demos/analyst/story_assays.m')"
% Workbench recording (needs a display):
%   DISPLAY=:1 ./demos/analyst/record_story_assays.sh

here = fileparts(mfilename('fullpath'));
src = fullfile(here, 'assays.csv');
T = readtable(src, 'TreatAsMissing', {'NA', '-999', ''});
nrows = height(T);
ncols = width(T);
M = ismissing(T);
miss = sum(M, 1);
nmiss = sum(M, 'all');
fprintf('ANALYST read rows=%.0f cols=%.0f file=%s\n', nrows, ncols, src);
fprintf('ANALYST missing site=%.0f shift=%.0f moisture_pct=%.0f temp_c=%.0f qc=%.0f total=%.0f\n', ...
    miss(1), miss(2), miss(3), miss(4), miss(5), nmiss);

[kept_site, drop_site] = rmmissing(T, 'DataVariables', 'site');
n_after_site = height(kept_site);
n_drop_site = sum(drop_site);
fprintf('ANALYST rmmissing site kept=%.0f dropped=%.0f\n', n_after_site, n_drop_site);

[kept_temp, filled_temp] = fillmissing(kept_site, 'previous', 'DataVariables', 'temp_c');
n_temp_filled = sum(filled_temp, 'all');
fprintf('ANALYST fillmissing temp_c previous filled=%.0f\n', n_temp_filled);

[kept_qc, filled_qc] = fillmissing(kept_temp, 'constant', 'pass', 'DataVariables', 'qc');
n_qc_filled = sum(filled_qc, 'all');
fprintf('ANALYST fillmissing qc constant filled=%.0f value=pass\n', n_qc_filled);

[clean, drop_m] = rmmissing(kept_qc, 'DataVariables', 'moisture_pct');
n_clean = height(clean);
n_drop_moisture = sum(drop_m);
fprintf('ANALYST rmmissing moisture_pct kept=%.0f dropped=%.0f\n', n_clean, n_drop_moisture);

clean.site = categorical(clean.site, {'North', 'South', 'East', 'West'});
S = groupsummary(clean, 'site', {'mean', 'sum'}, {'moisture_pct', 'temp_c'}, ...
    'IncludeEmptyGroups', true);
ngroups = height(S);
fprintf('ANALYST groups=%.0f empty_west=1\n', ngroups);
names = {'North', 'South', 'East', 'West'};
for k = 1:ngroups
    fprintf('ANALYST group=%s count=%.0f mean_moisture=%.4f mean_temp=%.4f sum_moisture=%.4f sum_temp=%.4f\n', ...
        names{k}, S.GroupCount(k), S.mean_moisture_pct(k), S.mean_temp_c(k), ...
        S.sum_moisture_pct(k), S.sum_temp_c(k));
end

out_dir = fullfile(here, 'out');
if ~isfolder(out_dir)
    mkdir(out_dir);
end
summary_path = fullfile(out_dir, 'site_summary.csv');
cleaned_path = fullfile(out_dir, 'cleaned.csv');
writetable(S, summary_path);
writetable(clean, cleaned_path);
summary_info = dir(summary_path);
cleaned_info = dir(cleaned_path);
summary_bytes = summary_info.bytes;
cleaned_bytes = cleaned_info.bytes;
fprintf('ANALYST summary=%s bytes=%.0f\n', summary_path, summary_bytes);
fprintf('ANALYST cleaned=%s bytes=%.0f\n', cleaned_path, cleaned_bytes);
