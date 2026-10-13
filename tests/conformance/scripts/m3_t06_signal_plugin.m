% M3 T06 - community.signal plugin breadth (hann/kaiser/butter/freqz/filtfilt); run with the plugin mfiles on the path
r1 = hann(5);
r2 = hann(4);
r3 = kaiser(5, 2.5);
[b, a] = butter(2, 0.5);
r4 = b;
r5 = a;
[b1, a1] = butter(1, 0.5);
r6 = [b1 a1];
[h, wv] = freqz([1 1], 1, 4);
r7 = abs(h);
r8 = wv;
r9 = filtfilt([0.5 0.5], 1, 1:10);
r10 = filtfilt([0.5 0.5], 1, 5 * ones(1, 7));
r11 = sum(kaiser(7, 0));
r12 = size(hann(6));
w1 = which('hann');
r13 = ~isempty(strfind(w1, 'community.signal'));
