function C = cmapss_sensor_corr(S)
%CMAPSS_SENSOR_CORR  Pearson sample correlation, columns are sensors.
%   C = cmapss_sensor_corr(S) is corrcoef(S). Rows are observations.
%   The covariance divides by n-1. The diagonal is 1. Constant columns
%   are not defined; the FD001 story drops them before this call.

C = corrcoef(S);
end
