function fail(code, varargin)
% FAIL  Octave test helper shim for the T2 harness: CODE must raise an error.
ok = false;
try
    evalin('caller', [code ';']);
catch
    ok = true;
end
if ~ok
    error('openmatlab:t2:fail', 'fail: expected an error');
end
end
