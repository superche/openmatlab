% M3-E1 FFT demo: locate a tone in a noise-free sampled signal
fs = 64; t = (0:fs-1)/fs;
s = sin(2*pi*5*t) + 0.5*sin(2*pi*12*t);
S = abs(fft(s))/fs*2;
f = (0:fs-1)*fs/fs;
[~, idx] = sort(S(1:fs/2), "descend"); k = idx(1:2);
peaks = sort(f(k))
centred = fftshift(round(S));
n = nextpow2(fs+1)
